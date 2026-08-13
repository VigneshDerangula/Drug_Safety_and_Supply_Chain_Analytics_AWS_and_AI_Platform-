"""
adverse_event_nlp_classifier.py

Pharmacovigilance use case: classify the severity of an adverse-event
narrative (mild / moderate / severe / life-threatening) from free text.

Two modes are implemented:

  1. Baseline supervised model (default, no external API needed):
     TF-IDF + Logistic Regression, trained on the synthetic labeled
     narratives in data/adverse_events.csv. This is what you'd start with
     once you have a few thousand labeled historical cases.

  2. Zero-shot LLM classification (--use-llm): calls an LLM (e.g. Claude via
     Anthropic's API, or Amazon Bedrock in a production AWS deployment) to
     classify narratives with no labeled training data at all — useful for
     a brand-new product line or a severity taxonomy that just changed.
     Requires ANTHROPIC_API_KEY to be set; this repo does not call the API
     unless --use-llm is passed explicitly.

Usage:
    python adverse_event_nlp_classifier.py --mode train
    python adverse_event_nlp_classifier.py --mode score
    python adverse_event_nlp_classifier.py --mode score --use-llm
"""
import argparse
import os

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "adverse_events.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "severity_classifier.joblib")

SEVERITY_ORDER = ["mild", "moderate", "severe", "life-threatening"]


def build_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, stop_words="english")),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )


def train():
    df = pd.read_csv(DATA_PATH)
    df = df.dropna(subset=["narrative", "severity_label"])

    X_train, X_test, y_train, y_test = train_test_split(
        df["narrative"], df["severity_label"], test_size=0.2, random_state=42, stratify=df["severity_label"]
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)
    print("=== Holdout classification report ===")
    print(classification_report(y_test, preds, labels=SEVERITY_ORDER, zero_division=0))

    joblib.dump(pipeline, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")
    return pipeline


def score(use_llm: bool = False):
    df = pd.read_csv(DATA_PATH)

    if use_llm:
        _score_with_llm(df)
        return

    if not os.path.exists(MODEL_PATH):
        print("No trained model found — training one first.")
        pipeline = train()
    else:
        pipeline = joblib.load(MODEL_PATH)

    df["predicted_severity"] = pipeline.predict(df["narrative"])
    agreement = (df["predicted_severity"] == df["severity_label"]).mean()
    print(f"Predicted-vs-labeled agreement on full dataset: {agreement:.1%}")

    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "adverse_events_scored.csv")
    df.to_csv(out_path, index=False)
    print(f"Scored output written to {out_path}")


def _score_with_llm(df: pd.DataFrame):
    """
    Zero-shot classification via an LLM. This is the pattern you'd swap in for
    a brand-new drug/therapeutic area with no labeled history yet.
    In an AWS-native deployment this call would go through Amazon Bedrock
    instead of the Anthropic API directly, using the same prompt.
    """
    try:
        import anthropic
    except ImportError:
        raise SystemExit("Install the anthropic package to use --use-llm: pip install anthropic")

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    sample = df.sample(min(10, len(df)), random_state=1)  # small demo batch, not the full dataset

    results = []
    for _, row in sample.iterrows():
        prompt = (
            "Classify the severity of this pharmacovigilance adverse event narrative "
            "into exactly one of: mild, moderate, severe, life-threatening. "
            "Respond with only the label.\n\n"
            f"Narrative: {row['narrative']}"
        )
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        label = resp.content[0].text.strip().lower()
        results.append({"case_id": row["case_id"], "llm_predicted_severity": label, "ground_truth": row["severity_label"]})

    result_df = pd.DataFrame(results)
    print(result_df)
    agreement = (result_df["llm_predicted_severity"] == result_df["ground_truth"]).mean()
    print(f"LLM agreement on demo sample: {agreement:.1%}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["train", "score"], default="train")
    parser.add_argument("--use-llm", action="store_true", help="Use zero-shot LLM classification instead of the trained model")
    args = parser.parse_args()

    if args.mode == "train":
        train()
    else:
        score(use_llm=args.use_llm)
