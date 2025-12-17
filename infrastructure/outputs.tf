output "public_ip" {
  description = "Elastic IP address of the server"
  value       = aws_eip.app_eip.public_ip
}

output "ssh_command" {
  description = "SSH command to connect to the server"
  value       = "ssh ubuntu@${aws_eip.app_eip.public_ip}"
}

output "http_url" {
  description = "HTTP URL of the application"
  value       = "http://${aws_eip.app_eip.public_ip}"
}

output "github_secrets" {
  description = "Secrets to add to GitHub repository"
  sensitive   = true
  value = {
    AWS_ACCESS_KEY_ID     = aws_iam_access_key.github_actions_key.id
    AWS_SECRET_ACCESS_KEY = aws_iam_access_key.github_actions_key.secret
    AWS_REGION            = data.aws_region.current.name
    EC2_INSTANCE_ID       = aws_instance.app_server.id
    S3_CONTENT_BUCKET     = aws_s3_bucket.content.bucket
  }
}

output "s3_content_bucket" {
  description = "S3 bucket name for blog content"
  value       = aws_s3_bucket.content.bucket
}

output "appregistry_application_arn" {
  description = "ARN of the AppRegistry application (visible in AWS myApplications)"
  value       = aws_servicecatalogappregistry_application.app.arn
}
