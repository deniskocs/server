resource "helm_release" "argocd" {
  name       = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = var.argocd_chart_version

  namespace        = kubernetes_namespace.argocd.metadata[0].name
  create_namespace = false

  wait    = true
  timeout = 600

  values = [
    file("${path.module}/argocd/values.yaml")
  ]

  depends_on = [kubernetes_namespace.argocd]
}
