variable "region" {
  description = "AWS Region"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Application name (prefix for resources)"
  type        = string
  default     = "flowyml"
}

variable "container_image" {
  description = "ECR image URI for the unified flowyml app"
  type        = string
}

variable "db_user" {
  description = "Database username"
  type        = string
  default     = "flowyml"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "flowyml"
}

variable "auth_secret" {
  description = "Authentication secret for JWT signing"
  type        = string
  sensitive   = true
}

variable "api_token" {
  description = "Static API token for client authentication"
  type        = string
  sensitive   = true
  default     = ""
}

variable "admin_user" {
  description = "Admin username for UI login"
  type        = string
  default     = "admin"
}

variable "admin_password" {
  description = "Admin password for UI login"
  type        = string
  sensitive   = true
}
