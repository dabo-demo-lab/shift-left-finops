locals {
  env = "prod"

  # Perfil de capacidad compartido por los tres entornos. Un cambio en
  # `shared` alcanza a prod, staging y dev; `overrides.prod` solo a este.
  profile  = jsondecode(file("${path.module}/../../profiles/checkout-capacity.json"))
  capacity = merge(local.profile.shared, lookup(local.profile.overrides, local.env, {}))

  # Claves y valores que exige la política de tags de Infracost:
  # Environment solo admite Prod, Stage o Dev.
  tags = {
    Project     = "shift-left-finops"
    Service     = "checkout"
    Environment = "Prod"
    Owner       = "dabo-demo-lab"
    Scenario    = var.scenario
    ManagedBy   = "terraform"
  }
}

module "checkout" {
  source = "../../modules/checkout-service"

  env = local.env
  # RDS Multi-AZ db.t4g.micro con gp3 no tenía capacidad en us-east-2b
  # (2026-10-08); AWS pidió us-east-2c como segunda AZ.
  availability_zones = ["us-east-2a", "us-east-2c"]
  vpc_cidr           = "10.10.0.0/16"
  nat_gateway_count  = 2
  db_multi_az        = true

  db_backup_retention_days = 7

  min_size = local.capacity.min_size
  max_size = local.capacity.max_size

  # Sin `scenario`: cambiarlo crearía otra versión del launch template y un
  # instance refresh en medio de la medición.
  tags = {
    Project = local.tags.Project
    Owner   = local.tags.Owner
  }
}
