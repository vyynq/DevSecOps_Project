variable "region" {
  description = "Région AWS (eu-west-3 = Paris)."
  type        = string
  default     = "eu-west-3"
}

variable "project" {
  description = "Préfixe des noms de ressources."
  type        = string
  default     = "secure-baseline"
}

variable "owner" {
  description = "Ton nom, mis en tag sur chaque ressource."
  type        = string
}

variable "alert_email" {
  description = "Email qui reçoit les alertes GuardDuty et budget."
  type        = string
}

variable "vpc_cidr" {
  description = "Plage IP du VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "monthly_budget_usd" {
  description = "Budget mensuel déclenchant une alerte à 80 %."
  type        = number
  default     = 5
}

variable "enable_guardduty" {
  description = "GuardDuty : 30 jours gratuits, puis payant au volume."
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Durée de conservation des logs dans S3."
  type        = number
  default     = 90
}
