# Aliased provider for creating the AppRegistry application
provider "aws" {
  alias  = "appregistry"
  region = var.aws_region
}

# Service Catalog AppRegistry Application (visible in AWS myApplications)
resource "aws_servicecatalogappregistry_application" "app" {
  provider    = aws.appregistry
  name        = "Sean-Michael-Dev"
  description = "Sean-Michael.dev personal website infrastructure"
}

# Main provider with default tags for automatic resource association
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(
      aws_servicecatalogappregistry_application.app.application_tag,
      {
        Project    = var.project_name
        Automation = "Terraform"
      }
    )
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_iam_user" "github_actions_deployer" {
  name = "${var.project_name}-github-deployer"

  tags = {
    Name = "${var.project_name}-github-deployer"
  }
}

resource "aws_iam_access_key" "github_actions_key" {
  user = aws_iam_user.github_actions_deployer.name
}

# S3 Bucket for blog content
resource "aws_s3_bucket" "content" {
  bucket = "${var.project_name}-content"

  tags = {
    Name = "${var.project_name}-content"
  }
}

resource "aws_s3_bucket_versioning" "content" {
  bucket = aws_s3_bucket.content.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "content" {
  bucket = aws_s3_bucket.content.id

  block_public_acls       = true
  block_public_policy     = false
  ignore_public_acls      = true
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "content_images_public" {
  bucket     = aws_s3_bucket.content.id
  depends_on = [aws_s3_bucket_public_access_block.content]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadImages"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.content.arn}/images/*"
      }
    ]
  })
}

# IAM policy for GitHub Actions to sync the S3 content bucket. GetObject is for the
# Pages build, which downloads digests/ before building the site.
resource "aws_iam_user_policy" "github_actions_s3_sync" {
  name = "${var.project_name}-s3-content-sync"
  user = aws_iam_user.github_actions_deployer.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3ContentSync"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.content.arn,
          "${aws_s3_bucket.content.arn}/*"
        ]
      }
    ]
  })
}
