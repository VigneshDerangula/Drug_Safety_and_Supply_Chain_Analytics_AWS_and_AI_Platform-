"""
AWS Lambda: adverse_event_alert

Triggered by S3 ObjectCreated events on raw/adverse_events/*.json (a single
new individual case safety report landing ahead of the nightly batch).
Applies a lightweight rules-based severity triage and publishes an SNS
alert immediately for severe/life-threatening cases, instead of waiting for
the next Glue/Airflow batch run.

This is the "real-time" complement to the batch NLP classifier in
ai_ml/adverse_event_nlp_classifier.py — cheap keyword rules here catch the
must-not-miss cases fast; the batch ML model does the fuller severity
classification overnight and reconciles.
"""
import json
import os

import boto3

s3 = boto3.client("s3")
sns = boto3.client("sns")

SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")

HIGH_RISK_TERMS = [
    "anaphylaxis",
    "cardiac arrest",
    "respiratory failure",
    "life-threatening",
    "resuscitat",
    "fatal",
    "intubat",
]


def _extract_severity_signal(record: dict) -> str:
    narrative = (record.get("narrative") or "").lower()
    outcome = (record.get("outcome") or "").lower()

    if "fatal" in outcome or any(term in narrative for term in HIGH_RISK_TERMS):
        return "life-threatening"
    if record.get("serious_flag") is True:
        return "severe"
    return "routine"


def lambda_handler(event, context):
    alerts_sent = 0

    for s3_record in event.get("Records", []):
        bucket = s3_record["s3"]["bucket"]["name"]
        key = s3_record["s3"]["object"]["key"]

        obj = s3.get_object(Bucket=bucket, Key=key)
        body = json.loads(obj["Body"].read())

        # body may be a single case report or a batch (list) of reports
        records = body if isinstance(body, list) else [body]

        for record in records:
            severity = _extract_severity_signal(record)
            if severity in ("severe", "life-threatening"):
                message = {
                    "case_id": record.get("case_id"),
                    "drug_code": record.get("drug_code"),
                    "drug_name": record.get("drug_name"),
                    "severity_signal": severity,
                    "country": record.get("country"),
                    "narrative": record.get("narrative"),
                    "source_key": key,
                }
                sns.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Subject=f"[PV ALERT] {severity.upper()} adverse event — {record.get('drug_name')}",
                    Message=json.dumps(message, indent=2),
                )
                alerts_sent += 1

    return {"statusCode": 200, "body": f"processed event, alerts_sent={alerts_sent}"}
