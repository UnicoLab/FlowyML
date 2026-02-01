output "app_url" {
  value = google_cloud_run_v2_service.app.uri
}

output "db_instance_connection_name" {
  value = google_sql_database_instance.instance.connection_name
}

output "artifact_registry_repo" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.name}"
}
