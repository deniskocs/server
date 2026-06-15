# App-of-apps: корневой Application через чарт argocd-apps.
# Создаёт CR Application, поэтому зависит от установленных Argo CD CRDs (helm_release.argocd).
resource "helm_release" "argocd_apps" {
  name       = "argocd-apps"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argocd-apps"
  version    = var.argocd_apps_chart_version

  namespace        = kubernetes_namespace.argocd.metadata[0].name
  create_namespace = false

  values = [
    file("${path.module}/values/argocd-apps.yaml")
  ]

  depends_on = [helm_release.argocd]
}
