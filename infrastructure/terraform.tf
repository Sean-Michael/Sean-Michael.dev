terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.26.0"
    }
  }

  backend "s3" {
    bucket = "203056033234-terraform-state"
    key    = "smr-website-tfstate"
    region = "us-west-2"
  }
}
