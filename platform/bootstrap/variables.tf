variable "region" {
  description = "Región de la demo."
  type        = string
  default     = "us-east-2"
}

variable "project" {
  description = "Valor del tag `Project` en todos los recursos de la demo."
  type        = string
  default     = "shift-left-finops"
}

variable "owner" {
  description = "Valor del tag `Owner`."
  type        = string
  default     = "dabo-demo-lab"
}

variable "github_org" {
  description = "Organización de GitHub dueña del repo."
  type        = string
  default     = "dabo-demo-lab"
}

variable "github_repo" {
  description = "Repo de la demo (sin la organización)."
  type        = string
  default     = "shift-left-finops"
}

variable "github_org_id" {
  description = "ID numérico de la organización. El repo usa el claim `sub` inmutable, que incluye los IDs."
  type        = number
  default     = 117472623
}

variable "github_repo_id" {
  description = "ID numérico del repo (gh api repos/<org>/<repo> --jq .id)."
  type        = number
  default     = 1384829651
}

variable "state_bucket_name" {
  description = "Bucket de estado existente (creado fuera de Terraform)."
  type        = string
  default     = "dabo-finops-demo-bucket"
}

variable "gha_role_name" {
  description = "Rol existente que asume GitHub Actions vía OIDC."
  type        = string
  default     = "finops_demo_role"
}

variable "budget_limit_usd" {
  description = "Límite mensual del presupuesto de la cuenta. Es una alerta, no un tope: AWS no detiene recursos al alcanzarlo."
  type        = number
  default     = 25
}

variable "budget_notification_emails" {
  description = "Correos que reciben las alertas del presupuesto. Se define en terraform.tfvars (no versionado)."
  type        = list(string)

  validation {
    condition     = length(var.budget_notification_emails) > 0
    error_message = "Definir al menos un correo para las alertas del presupuesto."
  }
}
