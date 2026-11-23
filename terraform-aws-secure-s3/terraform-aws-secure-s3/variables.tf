variable "bucket_name" {
  description = "Name of the S3 bucket to create (must be globally unique)."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9.-]{3,63}$", var.bucket_name))
    error_message = "bucket_name must be 3-63 characters: lowercase letters, digits, dots or hyphens."
  }
}

variable "kms_key_arn" {
  description = "ARN of a KMS key (CMK) used to encrypt objects. Recommended. If null, AWS-managed SSE-KMS is used."
  type        = string
  default     = null
}

variable "versioning_enabled" {
  description = "Enable object versioning (protects against deletion/overwrite)."
  type        = bool
  default     = true
}

variable "log_bucket_name" {
  description = "Target bucket for S3 server access logs. Required for access traceability."
  type        = string
}

variable "log_prefix" {
  description = "Key prefix for log objects in the target bucket."
  type        = string
  default     = "s3-access-logs/"
}

variable "noncurrent_version_expiration_days" {
  description = "Number of days after which noncurrent object versions are deleted."
  type        = number
  default     = 90
}

variable "abort_multipart_days" {
  description = "Abort incomplete multipart uploads after N days (avoids paying for orphaned storage)."
  type        = number
  default     = 7
}

variable "tags" {
  description = "Tags applied to the bucket."
  type        = map(string)
  default     = {}
}
