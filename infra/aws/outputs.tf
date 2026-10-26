output "url" {
  value = "${local.https ? "https" : "http"}://${aws_lb.app.dns_name}"
}

output "ecr_repository" { value = aws_ecr_repository.app.repository_url }
output "docs_bucket" { value = aws_s3_bucket.docs.bucket }
output "dynamodb_table" { value = aws_dynamodb_table.store.name }
output "cluster" { value = aws_ecs_cluster.this.name }
output "service" { value = aws_ecs_service.app.name }
