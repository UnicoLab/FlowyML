output "app_url" {
  value = "https://${azurerm_container_app.app.latest_revision_fqdn}"
}

output "db_fqdn" {
  value = azurerm_postgresql_flexible_server.db.fqdn
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}
