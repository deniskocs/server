variable "kubeconfig_path" {
  description = "Путь к kubeconfig (на master node обычно ~/.kube/config)"
  type        = string
  default     = "~/.kube/config"
}

variable "argocd_chart_version" {
  description = "Версия Helm chart argo-cd (репозиторий argo-helm)"
  type        = string
  default     = "7.8.0"
}

variable "argocd_namespace" {
  description = "Namespace для Argo CD"
  type        = string
  default     = "argocd"
}
