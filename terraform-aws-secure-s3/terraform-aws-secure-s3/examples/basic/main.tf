# Example usage of the secure-s3 module.
# Creates a KMS key + a log bucket, then a secured application bucket.

provider "aws" {
  region = "eu-west-1"
}

data "aws_caller_identity" "current" {}

resource "aws_kms_key" "s3" {
  description             = "CMK used to encrypt the application bucket"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "EnableRootAccountAdmin"
      Effect    = "Allow"
      Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
      Action    = "kms:*"
      Resource  = "*"
    }]
  })
}

# ---------------------------------------------------------------------------
# Dedicated access-log bucket. It is the logging target, so it does not need
# recursive access logging, replication or event notifications itself.
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "logs" {
  #checkov:skip=CKV_AWS_144:Log bucket: cross-region replication not required.
  #checkov:skip=CKV2_AWS_62:Log bucket: event notifications not required.
  bucket = "ilyas-demo-access-logs-eu"
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket                  = aws_s3_bucket.logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    id     = "expire-old-logs"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    expiration {
      days = 365
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
  depends_on = [aws_s3_bucket_versioning.logs]
}

# ---------------------------------------------------------------------------
# Module call: the secured application bucket.
# ---------------------------------------------------------------------------
module "app_bucket" {
  source = "../../"

  bucket_name     = "ilyas-demo-app-data-eu"
  kms_key_arn     = aws_kms_key.s3.arn
  log_bucket_name = aws_s3_bucket.logs.id
  tags = {
    Project = "DevSecOps_Project"
    Owner   = "ilyas"
  }
}
