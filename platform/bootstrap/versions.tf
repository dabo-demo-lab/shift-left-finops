# Raíz de arranque de la cuenta de la demo. Se aplica a mano, con credenciales
# de administrador locales; GitHub Actions nunca la ejecuta.
#
# El bucket de estado ya existía antes de esta raíz (creado en consola), así
# que esta raíz guarda su propio estado en él, bajo platform/bootstrap/.

terraform {
  required_version = ">= 1.10, < 2.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  backend "s3" {
    bucket       = "dabo-finops-demo-bucket"
    key          = "platform/bootstrap/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true
  }
}
