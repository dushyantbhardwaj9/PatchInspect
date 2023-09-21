variable "rule_name" {
  type = string
  description = "use case rule name"
}

variable "role_arn" {
  type = string
  description = "role arn used by the function"
}

variable "rule" {
  type = bool
  description = "Weather the event rule is running on cron or not"
  default = false
}

variable "cron" {
  type = string
  description = "cron expression to trigger the event"
  default = "false"
}

variable "layers" {
  type = list
  description = "list of layer ARNs for security automation"
  default = []
}

variable "env_vars" {
  type = map
  description = "list of environment variables used in lambda function"
}

variable "memory_size" {
  type = number
  description = "RAM size in MB for lambda function"
  default = 256
}

variable "timeout" {
  default = 900
  description = "Timeout for the lambda function"

}

variable "rule_enabled" {
  type = bool
  description = "Defines if the rule is enabled"
  default = true
}

variable "project"{
  type = string
  description = "Name of the project. This will be used as a tag on all resources"
  default = "PatchInspect"
}