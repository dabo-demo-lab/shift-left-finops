# Proveedor OIDC y rol de GitHub Actions, creados antes en consola e
# importados aquí para fijar su configuración en código.
#
# El rol solo sirve para `terraform plan`: lectura de la cuenta, lectura del
# estado y escritura del archivo de lock. Los `apply` se ejecutan en local.

locals {
  repo_sub_prefix = "repo:${var.github_org}/${var.github_repo}"

  # Claims `sub` por defecto de GitHub. Si un job usa `environment:`, el claim
  # pasa a ser `<repo>:environment:<nombre>` y este rol lo rechazará.
  gha_allowed_subs = [
    "${local.repo_sub_prefix}:pull_request",
    "${local.repo_sub_prefix}:ref:refs/heads/main",
  ]
}

import {
  to = aws_iam_openid_connect_provider.github_actions
  id = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github_actions" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

import {
  to = aws_iam_role.gha
  id = var.gha_role_name
}

resource "aws_iam_role" "gha" {
  name                 = var.gha_role_name
  description          = "GitHub Actions (PR y main) de ${var.github_org}/${var.github_repo}: terraform plan de solo lectura."
  max_session_duration = 3600
  assume_role_policy   = data.aws_iam_policy_document.gha_trust.json
}

data "aws_iam_policy_document" "gha_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github_actions.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = local.gha_allowed_subs
    }
  }
}

import {
  to = aws_iam_role_policy_attachment.gha_readonly
  id = "${var.gha_role_name}/arn:aws:iam::aws:policy/ReadOnlyAccess"
}

# ReadOnlyAccess permite que `plan` resuelva data sources y detecte drift sin
# mantener a mano cientos de acciones Describe/List. El deny de abajo cierra
# la lectura de secretos.
resource "aws_iam_role_policy_attachment" "gha_readonly" {
  role       = aws_iam_role.gha.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

resource "aws_iam_role_policy" "gha_state" {
  name   = "terraform-state-lock"
  role   = aws_iam_role.gha.id
  policy = data.aws_iam_policy_document.gha_state.json
}

data "aws_iam_policy_document" "gha_state" {
  statement {
    sid       = "ListStateBucket"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [data.aws_s3_bucket.state.arn]
  }

  statement {
    sid       = "ReadEnvState"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${data.aws_s3_bucket.state.arn}/envs/*/terraform.tfstate"]
  }

  # `use_lockfile` crea y borra `<key>.tflock` incluso durante `plan`.
  statement {
    sid       = "EnvStateLockFile"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${data.aws_s3_bucket.state.arn}/envs/*/terraform.tfstate.tflock"]
  }

  statement {
    sid    = "DenySecretsRead"
    effect = "Deny"
    actions = [
      "secretsmanager:GetSecretValue",
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath",
      "kms:Decrypt",
    ]
    resources = ["*"]
  }

  # El estado de bootstrap y cualquier otra ruta del bucket quedan fuera.
  statement {
    sid           = "DenyStateWriteOutsideLocks"
    effect        = "Deny"
    actions       = ["s3:PutObject", "s3:DeleteObject"]
    not_resources = ["${data.aws_s3_bucket.state.arn}/envs/*/terraform.tfstate.tflock"]
  }
}
