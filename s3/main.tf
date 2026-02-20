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

module "s3_bucket" {
    source = "terraform-aws-modules/s3-bucket/aws"

    bucket = var.bucket_name

    # Allow deletion of non-empty bucket
    force_destroy = true

    tags = {
        "Purpose" = "VideoConduit Frontend",
        "Project" = "videoconduit"
    }

    # ability to attach public policies define by user
    attach_public_policy = true

    versioning = {
        enabled = true
    }

    # website hosting enabled
    website = {
        index_document = "index.html"
        error_document = "error.html"
    }
}

# public access control list
# https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html
resource "aws_s3_bucket_public_access_block" "public-access-settings" {
    bucket = module.s3_bucket.s3_bucket_id

    block_public_acls = false
    block_public_policy = false
    ignore_public_acls = false
    restrict_public_buckets = false
}

# public read policy generation JSON
data "aws_iam_policy_document" "s3_public_read_policy" {
    statement {
      sid = "s3PublicRead"
      principals {
        type = "*"
        identifiers = [ "*" ]
      }
      #actions = [ "s3:GetObject", "s3:PutObject" ]
      actions = [ "s3:GetObject" ]
      resources = [ "${module.s3_bucket.s3_bucket_arn}/*" ]
    }
}

# S3 bucket policy attachment of JSON document
resource "aws_s3_bucket_policy" "s3_static_website_public_read" {
    bucket = module.s3_bucket.s3_bucket_id
    policy = data.aws_iam_policy_document.s3_public_read_policy.json

    depends_on = [aws_s3_bucket_public_access_block.public-access-settings]
}
