variable "region" {
  type        = string
  description = "region to deploy the patch inspect"
  default     = "ap-south-1"
}

variable "project" {
  type        = string
  description = "Name of the project. This will be used as a tag on all resources"
  default     = "PatchInspect"
}

variable "tags" {
  description = "Common tags for all resources"
}

variable "iam_role" {
  description = "IAM role to be assumed by the solution for assuming client"
}
