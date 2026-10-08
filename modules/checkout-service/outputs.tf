output "url" {
  description = "URL HTTP del ALB."
  value       = "http://${aws_lb.this.dns_name}"
}

output "asg_name" {
  description = "ASG; fuente de las métricas de horas-instancia."
  value       = aws_autoscaling_group.app.name
}

output "capacity" {
  value = {
    min_size = aws_autoscaling_group.app.min_size
    max_size = aws_autoscaling_group.app.max_size
  }
}

output "db_endpoint" {
  value = aws_db_instance.this.address
}

output "nat_gateway_count" {
  value = var.nat_gateway_count
}
