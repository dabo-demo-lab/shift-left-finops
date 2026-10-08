locals {
  env = "staging"

  # Perfil de capacidad compartido por los tres entornos. Un cambio en
  # `shared` alcanza a prod, staging y dev; `overrides.staging` solo a este.
  profile  = jsondecode(file("${path.module}/../../profiles/checkout-capacity.json"))
  capacity = merge(local.profile.shared, lookup(local.profile.overrides, local.env, {}))

  # Claves y valores que exige la política de tags de Infracost:
  # Environment solo admite Prod, Stage o Dev.
  tags = {
    Project     = "shift-left-finops"
    Service     = "checkout"
    Environment = "Stage"
    Owner       = "dabo-demo-lab"
    Scenario    = var.scenario
    ManagedBy   = "terraform"
  }
}

module "checkout" {
  source = "../../modules/checkout-service"

  env               = local.env
  vpc_cidr          = "10.20.0.0/16"
  nat_gateway_count = 1
  db_multi_az       = false

  db_backup_retention_days = 1

  min_size = local.capacity.min_size
  max_size = local.capacity.max_size

  # Sin `scenario`: cambiarlo crearía otra versión del launch template y un
  # instance refresh en medio de la medición.
  tags = {
    Project = local.tags.Project
    Owner   = local.tags.Owner
  }
}
