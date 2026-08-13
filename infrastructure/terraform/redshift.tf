resource "aws_redshift_subnet_group" "pharma" {
  name       = "${var.project_name}-${var.environment}-subnet-group"
  subnet_ids = [] # supply your VPC private subnet IDs at apply time
}

resource "aws_redshift_cluster" "pharma_dwh" {
  cluster_identifier   = "${var.project_name}-${var.environment}-dwh"
  database_name        = "pharma_analytics"
  master_username      = var.redshift_master_username
  master_password      = var.redshift_master_password
  node_type            = var.redshift_node_type
  cluster_type         = "single-node"
  iam_roles            = [aws_iam_role.redshift_role.arn]
  skip_final_snapshot  = true
  encrypted            = true
  publicly_accessible  = false
}
