# terraform-aws-secure-s3

A **reusable** Terraform module that provisions a "secure by default" Amazon S3 bucket,
built to pass IaC security scanners (**Checkov** and **tfsec**) with no trade-offs.
No resources are deployed to validate it: the code is analysed statically, exactly as in CI.

> **Scan results (reproducible locally and in CI)**
> `checkov`: **46 passed / 0 failed** (4 documented skips) · `tfsec`: **No problems detected!**

## Built-in security controls

| Control | How |
|---|---|
| Encryption at rest | SSE-KMS (`aws:kms`) + bucket key, CMK provided as input |
| Block public access | `public_access_block` with all four options set to `true` |
| Encryption in transit | Bucket policy that **denies** any request with `aws:SecureTransport = false` (TLS required) |
| ACLs disabled | `BucketOwnerEnforced` (no ACLs, account-level ownership) |
| Versioning | Enabled by default (protection against deletion/overwrite) |
| Traceability | Server access logging to a dedicated log bucket |
| Lifecycle hygiene | Expire noncurrent versions + abort incomplete multipart uploads |

## Usage

```hcl
module "app_bucket" {
  source = "./terraform-aws-secure-s3"

  bucket_name     = "my-app-data-eu"
  kms_key_arn     = aws_kms_key.s3.arn      # recommended CMK
  log_bucket_name = aws_s3_bucket.logs.id   # access-log target bucket
  tags = {
    Project = "DevSecOps_Project"
  }
}
```

A complete, scannable example is available in [`examples/basic`](examples/basic).

## Inputs

| Name | Type | Default | Description |
|---|---|---|---|
| `bucket_name` | string | — | Bucket name (regex-validated) |
| `kms_key_arn` | string | `null` | ARN of a KMS CMK for encryption |
| `log_bucket_name` | string | — | Access-log target bucket |
| `versioning_enabled` | bool | `true` | Enable versioning |
| `noncurrent_version_expiration_days` | number | `90` | Expiration of noncurrent versions |
| `abort_multipart_days` | number | `7` | Abort incomplete multipart uploads |

Outputs: `bucket_id`, `bucket_arn`, `bucket_domain_name`.

## Running the scans locally

```bash
pip install checkov
# tfsec: https://github.com/aquasecurity/tfsec

checkov -d . --compact --framework terraform
tfsec .
```

## Accepted skips (documented risk acceptance)

Two "enterprise" controls are intentionally **not** enabled by default in a reusable baseline,
and are tracked with inline `#checkov:skip=` comments (silent suppression is bad practice — these
are justified instead):

- **CKV_AWS_144** (cross-region replication): costly, depends on data criticality → enable per use case.
- **CKV2_AWS_62** (event notifications): no generic consumer → left to the caller.

## CI

The workflow [`.github/workflows/terraform-security.yml`](../.github/workflows/terraform-security.yml)
runs on every push/PR: `terraform fmt`, `terraform validate`, **tfsec** and **Checkov**, and publishes
**SARIF** reports in the repository's *Security* tab.

## Repository layout

```
.
├── terraform-aws-secure-s3/        # this module
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── versions.tf
│   └── examples/basic/
└── .github/workflows/
    └── terraform-security.yml      # security CI (lives at the repo root)
```
