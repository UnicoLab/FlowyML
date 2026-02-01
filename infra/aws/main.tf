terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

data "aws_availability_zones" "available" {}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = "${var.app_name}-vpc"
  cidr = "10.0.0.0/16"

  azs             = slice(data.aws_availability_zones.available.names, 0, 2)
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true
}

# Database Security Group
resource "aws_security_group" "db_sg" {
  name        = "${var.app_name}-db-sg"
  description = "Allow inbound access from App Runner"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }
}

# RDS Instance
resource "aws_db_instance" "default" {
  identifier           = "${var.app_name}-db"
  allocated_storage    = 20
  storage_type         = "gp2"
  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = "db.t3.micro"
  db_name              = var.db_name
  username             = var.db_user
  password             = var.db_password
  parameter_group_name = "default.postgres15"
  skip_final_snapshot  = true

  vpc_security_group_ids = [aws_security_group.db_sg.id]
  db_subnet_group_name   = module.vpc.database_subnet_group_name
}

# App Runner VPC Connector
resource "aws_apprunner_vpc_connector" "connector" {
  vpc_connector_name = "${var.app_name}-vpc-connector"
  subnets            = module.vpc.private_subnets
  security_groups    = [aws_security_group.db_sg.id]
}

# App Runner IAM Role (for ECR access)
resource "aws_iam_role" "apprunner_role" {
  name = "${var.app_name}-apprunner-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_policy" {
  role       = aws_iam_role.apprunner_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# --- Secrets ---

resource "aws_secretsmanager_secret" "flowyml_secrets" {
  name = "${var.app_name}-secrets-${random_id.secret_suffix.hex}"
}

resource "random_id" "secret_suffix" {
  byte_length = 4
}

resource "aws_secretsmanager_secret_version" "flowyml_secrets" {
  secret_id = aws_secretsmanager_secret.flowyml_secrets.id
  secret_string = jsonencode({
    DB_PASSWORD         = var.db_password
    FLOWYML_AUTH_SECRET = var.auth_secret
    FLOWYML_API_TOKEN   = var.api_token
  })
}

# App Runner Needs Access to Secrets
resource "aws_iam_policy" "secrets_policy" {
  name        = "${var.app_name}-secrets-policy"
  description = "Allow App Runner to read secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [aws_secretsmanager_secret.flowyml_secrets.arn]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_secrets" {
  role       = aws_iam_role.apprunner_instance_role.name
  policy_arn = aws_iam_policy.secrets_policy.arn
}

# App Runner Instance Role (Run-time permissions)
resource "aws_iam_role" "apprunner_instance_role" {
  name = "${var.app_name}-apprunner-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "instance_sagemaker" {
  role       = aws_iam_role.apprunner_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

resource "aws_iam_role_policy_attachment" "instance_s3" {
  role       = aws_iam_role.apprunner_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_role_policy_attachment" "instance_logs" {
  role       = aws_iam_role.apprunner_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

# Backend Service
resource "aws_apprunner_service" "backend" {
  service_name = "${var.app_name}-backend"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_role.arn
    }
    image_repository {
      image_configuration {
        port = "8080"
        runtime_environment_variables = {
          FLOWYML_DATABASE_URL = "postgresql://${var.db_user}:${var.db_password}@${aws_db_instance.default.endpoint}/${var.db_name}"
          FLOWYML_ENV          = "production"
        }
        runtime_environment_secrets = {
          DB_PASSWORD         = "${aws_secretsmanager_secret.flowyml_secrets.arn}:DB_PASSWORD::"
          FLOWYML_AUTH_SECRET = "${aws_secretsmanager_secret.flowyml_secrets.arn}:FLOWYML_AUTH_SECRET::"
          FLOWYML_API_TOKEN   = "${aws_secretsmanager_secret.flowyml_secrets.arn}:FLOWYML_API_TOKEN::"
        }
      }
      image_identifier      = var.backend_image
      image_repository_type = "ECR"
    }
  }

  instance_configuration {
    instance_role_arn = aws_iam_role.apprunner_instance_role.arn
  }

  network_configuration {
    egress_configuration {
      egress_type       = "VPC"
      vpc_connector_arn = aws_apprunner_vpc_connector.connector.arn
    }
  }
}

# Frontend Service
resource "aws_apprunner_service" "frontend" {
  service_name = "${var.app_name}-frontend"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_role.arn
    }
    image_repository {
      image_configuration {
        port = "80"
        runtime_environment_variables = {
          VITE_API_URL = "https://${aws_apprunner_service.backend.service_url}"
        }
      }
      image_identifier      = var.frontend_image
      image_repository_type = "ECR"
    }
  }

  instance_configuration {
    instance_role_arn = aws_iam_role.apprunner_instance_role.arn
  }
}
