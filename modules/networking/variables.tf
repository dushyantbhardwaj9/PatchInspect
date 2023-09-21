variable "project" {
  type = string
  description = "Project name"
}

variable "vpc_cidr" {
    type = string
  
  default = "10.0.0.0/24"
  description = "CIDR block for the VPC (defaults to 10.0.0.0/24)"
}

variable "subnet_cidr" {
    type = string
  
  default = "10.0.1.0/24"
  description = "CIDR block for the subnet (defaults to 10.0.1.0/24)"
}

variable "az" {
    default = "ap-southeast-1a"
    description = "Availability zone for the subnet"
    type = string
}