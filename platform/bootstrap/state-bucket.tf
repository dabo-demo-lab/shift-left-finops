# El bucket ya tiene versionado, SSE-S3 y Block Public Access (configurados en
# consola). Esta raíz no lo importa para no arriesgar su ciclo de vida; solo
# añade lo que faltaba: exigir TLS, propiedad de objetos y limpieza de
# versiones antiguas.

data "aws_s3_bucket" "state" {
  bucket = var.state_bucket_name
}

resource "aws_s3_bucket_policy" "state" {
  bucket = data.aws_s3_bucket.state.id
  policy = data.aws_iam_policy_document.state_bucket.json
}

data "aws_iam_policy_document" "state_bucket" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [data.aws_s3_bucket.state.arn, "${data.aws_s3_bucket.state.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_ownership_controls" "state" {
  bucket = data.aws_s3_bucket.state.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = data.aws_s3_bucket.state.id

  rule {
    id     = "expire-noncurrent-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
