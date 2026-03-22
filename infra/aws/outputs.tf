output "app_url" {
  value = "https://${aws_apprunner_service.app.service_url}"
}

output "db_endpoint" {
  value = aws_db_instance.default.endpoint
}

output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}
