output "prometheus_url" {
  value = "http://localhost:9090"
}

output "grafana_url" {
  value = "http://localhost:3000"
}

output "jenkins_deployer_service_account" {
  value = "${var.app_namespace}/${kubernetes_service_account_v1.jenkins_deployer.metadata[0].name}"
}
