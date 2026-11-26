variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Name prefix for resources"
  type        = string
  default     = "smr-webdev"
}
