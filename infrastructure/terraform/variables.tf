variable "project_name" {
  description = "Prefix applied to all resources"
  type        = string
  default     = "pharmapulse"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "redshift_master_username" {
  description = "Master username for the Redshift cluster"
  type        = string
  default     = "pharma_admin"
}

variable "redshift_master_password" {
  description = "Master password for the Redshift cluster (pass via TF_VAR or secrets manager, never commit)"
  type        = string
  sensitive   = true
}

variable "redshift_node_type" {
  description = "Redshift node type"
  type        = string
  default     = "ra3.xlplus"
}

variable "alert_email" {
  description = "Email subscribed to the SNS topic for severe/life-threatening adverse event alerts"
  type        = string
  default     = "pv-alerts@example.com"
}
