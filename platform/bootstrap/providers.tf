provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = var.project
      Service     = "platform"
      Environment = "Shared"
      Owner       = var.owner
      ManagedBy   = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
