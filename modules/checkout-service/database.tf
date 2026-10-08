resource "aws_db_subnet_group" "this" {
  name       = local.name
  subnet_ids = aws_subnet.private[*].id
}

# Multi-AZ crea un standby síncrono en otra AZ; no sirve lecturas.
# La contraseña la genera y guarda Secrets Manager: nunca entra al estado.
resource "aws_db_instance" "this" {
  identifier     = local.name
  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class
  multi_az       = var.db_multi_az

  allocated_storage = var.db_allocated_storage_gb
  storage_type      = "gp3"
  storage_encrypted = true

  db_name                     = var.service
  username                    = "checkout_admin"
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false

  backup_retention_period    = var.db_backup_retention_days
  auto_minor_version_upgrade = true
  apply_immediately          = true

  # Demo efímera: se destruye al final de cada sesión.
  deletion_protection = false
  skip_final_snapshot = true
}
