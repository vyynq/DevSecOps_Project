terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.40"
    }
  }

  # Étape "aller plus loin" : state distant dans S3.
  # backend "s3" {
  #   bucket       = "mon-bucket-tfstate"
  #   key          = "secure-baseline/terraform.tfstate"
  #   region       = "eu-west-3"
  #   encrypt      = true
  #   use_lockfile = true
  # }
}

provider "aws" {
  region = var.region

  # Tags appliqués à toutes les ressources : indispensable pour le suivi des coûts et l'inventaire.
  default_tags {
    tags = {
      Project   = var.project
      Owner     = var.owner
      ManagedBy = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  account_id = data.aws_caller_identity.current.account_id
  azs        = slice(data.aws_availability_zones.available.names, 0, 2)
  name       = var.project

  # Construit à la main pour éviter une dépendance circulaire bucket policy <-> trail.
  trail_name = "${var.project}-trail"
  trail_arn  = "arn:aws:cloudtrail:${var.region}:${local.account_id}:trail/${local.trail_name}"
}
