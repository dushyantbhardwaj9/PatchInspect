output "subnet_id" {
  value = aws_subnet.subnet.id
  description = "Subnet ID to be used for Compliant Server"
}

output "sg_id" {
  value = aws_security_group.allow_ssm.id
  description = "Security ID to be used for Compliant Server"
}