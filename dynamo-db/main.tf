terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6"
    }
  }
}

provider "aws" {
  region = var.region
}

resource "aws_dynamodb_table" "users_data" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"

  # Use variables here
  hash_key  = var.partition_key_name
  range_key = var.sort_key_name

  # Attributes must match keys
  attribute {
    name = var.partition_key_name
    type = "S"
  }

  attribute {
    name = var.sort_key_name
    type = "S"
  }

  tags = {
    Purpose = "Users database to keep track of the process"
    Project = "videoconduit"
  }
}