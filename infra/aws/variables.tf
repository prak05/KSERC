variable "name" {
  description = "Prefix for every resource"
  type        = string
  default     = "kserc-truing-up"
}

variable "region" {
  description = "Region for the app, storage and Textract"
  type        = string
  default     = "ap-south-1"
}

variable "bedrock_region" {
  description = "Region where Claude model access is enabled (defaults to var.region)"
  type        = string
  default     = ""
}

variable "llm_model" {
  type    = string
  default = "anthropic.claude-opus-5-5"
}

variable "llm_fallback_model" {
  description = "Model the SDK retries on if the primary declines a request"
  type        = string
  default     = "anthropic.claude-opus-4-8"
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "cpu" {
  type    = number
  default = 2048
}

variable "memory" {
  type    = number
  default = 4096
}

variable "desired_count" {
  description = "Keep at 1: running analyses live in the task's memory"
  type        = number
  default     = 1
}

variable "certificate_arn" {
  description = "ACM certificate ARN to enable HTTPS on the load balancer (optional)"
  type        = string
  default     = ""
}

variable "allowed_cidrs" {
  description = "Who may reach the load balancer — narrow this to the Commission's network"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "force_destroy" {
  description = "Allow `terraform destroy` to delete a non-empty bucket and ECR repo"
  type        = bool
  default     = false
}
