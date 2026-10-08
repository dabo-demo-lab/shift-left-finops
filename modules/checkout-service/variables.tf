variable "env" {
  description = "Entorno: prod, staging o dev."
  type        = string

  validation {
    condition     = contains(["prod", "staging", "dev"], var.env)
    error_message = "env debe ser prod, staging o dev."
  }
}

variable "service" {
  description = "Nombre del servicio; prefijo de recursos y valor del tag `Service`."
  type        = string
  default     = "checkout"
}

variable "vpc_cidr" {
  description = "CIDR /16 de la VPC del entorno. Debe ser distinto en cada entorno."
  type        = string
}

variable "az_count" {
  description = "Zonas de disponibilidad usadas por subredes, ALB y ASG."
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 2
    error_message = "El ALB y RDS requieren al menos 2 AZ."
  }
}

variable "nat_gateway_count" {
  description = "NAT gateways: uno por AZ en prod; uno compartido en no-prod."
  type        = number

  validation {
    condition     = var.nat_gateway_count >= 1 && var.nat_gateway_count <= var.az_count
    error_message = "nat_gateway_count debe estar entre 1 y az_count."
  }
}

variable "instance_type" {
  description = "Tipo de instancia (arm64, por la AMI)."
  type        = string
  default     = "t4g.micro"
}

variable "min_size" {
  description = "Mínimo del ASG. Es la reserva de capacidad que se paga aunque no haya demanda."
  type        = number

  validation {
    condition     = var.min_size >= 1
    error_message = "min_size debe ser al menos 1."
  }
}

variable "max_size" {
  description = "Máximo del ASG."
  type        = number
}

variable "cpu_target_percent" {
  description = "Objetivo de CPU media para el target tracking del ASG."
  type        = number
  default     = 50
}

variable "db_instance_class" {
  description = "Clase de la instancia RDS."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_multi_az" {
  description = "RDS Multi-AZ con standby síncrono."
  type        = bool
}

variable "db_engine_version" {
  description = "Versión mayor de PostgreSQL; RDS elige la menor por defecto."
  type        = string
  default     = "18"
}

variable "db_allocated_storage_gb" {
  description = "Almacenamiento gp3 de RDS."
  type        = number
  default     = 20
}

variable "db_backup_retention_days" {
  description = "Retención de backups automáticos de RDS."
  type        = number
  default     = 1
}

variable "alb_ingress_cidrs" {
  description = "CIDRs con acceso HTTP al ALB."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "tags" {
  description = "Tags adicionales para instancias y volúmenes lanzados por el ASG (default_tags no llega a ellos)."
  type        = map(string)
  default     = {}
}
