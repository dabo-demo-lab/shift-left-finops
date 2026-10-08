locals {
  env = "prod"

  # Perfil de capacidad compartido por los tres entornos. Un cambio en
  # `shared` alcanza a prod, staging y dev; `overrides.prod` solo a este.
  profile  = jsondecode(file("${path.module}/../../profiles/checkout-capacity.json"))
  capacity = merge(local.profile.shared, lookup(local.profile.overrides, local.env, {}))

  tags = {
    project    = "shift-left-finops"
    service    = "checkout"
    env        = local.env
    owner      = "dabo-demo-lab"
    scenario   = var.scenario
    managed-by = "terraform"
  }
}

module "checkout" {
  source = "../../modules/checkout-service"

  env               = local.env
  vpc_cidr          = "10.10.0.0/16"
  nat_gateway_count = 2
  db_multi_az       = true

  db_backup_retention_days = 7

  min_size = local.capacity.min_size
  max_size = local.capacity.max_size

  # Sin `scenario`: cambiarlo crearía otra versión del launch template y un
  # instance refresh en medio de la medición.
  tags = {
    project = local.tags.project
    owner   = local.tags.owner
  }
}
