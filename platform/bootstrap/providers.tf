provider "aws" {
  region = var.region

  default_tags {
    tags = {
      project    = var.project
      service    = "platform"
      env        = "shared"
      owner      = var.owner
      managed-by = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
