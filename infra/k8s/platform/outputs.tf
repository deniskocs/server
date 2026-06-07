output "argocd_namespace" {
  description = "Namespace, в котором установлен Argo CD"
  value       = kubernetes_namespace.argocd.metadata[0].name
}

output "argocd_release" {
  description = "Имя Helm release Argo CD"
  value       = helm_release.argocd.name
}
