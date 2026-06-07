variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "url-shortener"
}

variable "api_task_count" {
  type    = number
  default = 2
}

variable "worker_task_count" {
  type    = number
  default = 1
}

variable "latency_p95_threshold_ms" {
  type    = number
  default = 500
}
