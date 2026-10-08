output "gha_role_arn" {
  description = "ARN para `role-to-assume` en aws-actions/configure-aws-credentials."
  value       = aws_iam_role.gha.arn
}

output "gha_allowed_subs" {
  description = "Claims `sub` aceptados por el rol."
  value       = local.gha_allowed_subs
}

output "state_bucket" {
  value = data.aws_s3_bucket.state.id
}
