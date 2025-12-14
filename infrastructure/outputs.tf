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
