output "backend_url" {
  value = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  value = google_cloud_run_v2_service.frontend.uri
}

output "db_instance_connection_name" {
  value = google_sql_database_instance.instance.connection_name
}
