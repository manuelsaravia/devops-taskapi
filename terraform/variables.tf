variable "kubeconfig_path" {
  description = "Ruta del kubeconfig de Docker Desktop"
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "Contexto de Kubernetes a usar"
  type        = string
  default     = "docker-desktop"
}

variable "app_namespace" {
  description = "Namespace donde corre la API (lo crea el pipeline con k8s/namespace.yaml)"
  type        = string
  default     = "devops-project"
}

variable "prometheus_version" {
  description = "Versión fija de la imagen de Prometheus"
  type        = string
  default     = "v2.55.1"
}

variable "grafana_version" {
  description = "Versión fija de la imagen de Grafana"
  type        = string
  default     = "11.3.1"
}
