# Infraestructura como código (Terraform) para el clúster Kubernetes de Docker Desktop.
# Gestiona lo que NO es la aplicación: el stack de monitoreo (Prometheus + Grafana)
# y una cuenta de despliegue con permisos mínimos para Jenkins.
# La aplicación (k8s/) la sigue desplegando el pipeline con kubectl.

terraform {
  required_version = ">= 1.5"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.35"
    }
  }
}

provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kube_context
}

# ─────────────────────────── Namespace de monitoreo ───────────────────────────
resource "kubernetes_namespace_v1" "monitoring" {
  metadata {
    name   = "monitoring"
    labels = { project = "devops-taskapi", managed-by = "terraform" }
  }
}

# ─────────────────────────── Prometheus ───────────────────────────
# Permiso de solo lectura para descubrir los pods de la API (service discovery)
resource "kubernetes_service_account_v1" "prometheus" {
  metadata {
    name      = "prometheus"
    namespace = kubernetes_namespace_v1.monitoring.metadata[0].name
  }
}

resource "kubernetes_cluster_role_v1" "prometheus" {
  metadata { name = "prometheus-read-pods" }
  rule {
    api_groups = [""]
    resources  = ["pods", "endpoints", "services"]
    verbs      = ["get", "list", "watch"]
  }
}

resource "kubernetes_cluster_role_binding_v1" "prometheus" {
  metadata { name = "prometheus-read-pods" }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role_v1.prometheus.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account_v1.prometheus.metadata[0].name
    namespace = kubernetes_namespace_v1.monitoring.metadata[0].name
  }
}

resource "kubernetes_config_map_v1" "prometheus" {
  metadata {
    name      = "prometheus-config"
    namespace = kubernetes_namespace_v1.monitoring.metadata[0].name
  }
  data = {
    "prometheus.yml" = <<-EOT
      global:
        scrape_interval: 15s
      scrape_configs:
        # Raspa /metrics de cada pod de la API (no del Service), para ver cada réplica por separado
        - job_name: taskapi
          metrics_path: /metrics
          kubernetes_sd_configs:
            - role: pod
              namespaces:
                names: [${var.app_namespace}]
          relabel_configs:
            - source_labels: [__meta_kubernetes_pod_label_app]
              regex: taskapi
              action: keep
            - source_labels: [__meta_kubernetes_pod_name]
              target_label: pod
    EOT
  }
}

resource "kubernetes_deployment_v1" "prometheus" {
  metadata {
    name      = "prometheus"
    namespace = kubernetes_namespace_v1.monitoring.metadata[0].name
    labels    = { app = "prometheus" }
  }
  spec {
    replicas = 1
    selector { match_labels = { app = "prometheus" } }
    template {
      metadata {
        labels = { app = "prometheus" }
        # Reinicia el pod si cambia la configuración
        annotations = { config-hash = sha1(kubernetes_config_map_v1.prometheus.data["prometheus.yml"]) }
      }
      spec {
        service_account_name = kubernetes_service_account_v1.prometheus.metadata[0].name
        container {
          name  = "prometheus"
          image = "prom/prometheus:${var.prometheus_version}"
          args  = ["--config.file=/etc/prometheus/prometheus.yml", "--storage.tsdb.retention.time=2d"]
          port { container_port = 9090 }
          resources {
            requests = { cpu = "100m", memory = "256Mi" }
            limits   = { cpu = "500m", memory = "512Mi" }
          }
          readiness_probe {
            http_get {
              path = "/-/ready"
              port = 9090
            }
            initial_delay_seconds = 5
          }
          volume_mount {
            name       = "config"
            mount_path = "/etc/prometheus"
          }
        }
        volume {
          name = "config"
          config_map { name = kubernetes_config_map_v1.prometheus.metadata[0].name }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "prometheus" {
  metadata {
    name      = "prometheus"
    namespace = kubernetes_namespace_v1.monitoring.metadata[0].name
  }
  spec {
    selector = { app = "prometheus" }
    port {
      port        = 9090
      target_port = 9090
    }
    type = "LoadBalancer" # http://localhost:9090
  }
}

# ─────────────────────────── Grafana ───────────────────────────
resource "kubernetes_config_map_v1" "grafana_provisioning" {
  metadata {
    name      = "grafana-provisioning"
    namespace = kubernetes_namespace_v1.monitoring.metadata[0].name
  }
  data = {
    "datasource.yaml" = <<-EOT
      apiVersion: 1
      datasources:
        - name: Prometheus
          type: prometheus
          uid: prometheus
          url: http://prometheus.monitoring.svc:9090
          isDefault: true
    EOT
    "dashboards.yaml" = <<-EOT
      apiVersion: 1
      providers:
        - name: taskapi
          folder: DevOps
          type: file
          options:
            path: /var/lib/grafana/dashboards
    EOT
    "taskapi.json" = file("${path.module}/dashboard-taskapi.json")
  }
}

resource "kubernetes_deployment_v1" "grafana" {
  metadata {
    name      = "grafana"
    namespace = kubernetes_namespace_v1.monitoring.metadata[0].name
    labels    = { app = "grafana" }
  }
  spec {
    replicas = 1
    selector { match_labels = { app = "grafana" } }
    template {
      metadata {
        labels      = { app = "grafana" }
        annotations = { config-hash = sha1(jsonencode(kubernetes_config_map_v1.grafana_provisioning.data)) }
      }
      spec {
        container {
          name  = "grafana"
          image = "grafana/grafana:${var.grafana_version}"
          port { container_port = 3000 }
          # Solo para el entorno local: acceso anónimo de lectura, sin contraseñas en el código
          env {
            name  = "GF_AUTH_ANONYMOUS_ENABLED"
            value = "true"
          }
          env {
            name  = "GF_AUTH_ANONYMOUS_ORG_ROLE"
            value = "Viewer"
          }
          env {
            name  = "GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH"
            value = "/var/lib/grafana/dashboards/taskapi.json"
          }
          resources {
            requests = { cpu = "50m", memory = "128Mi" }
            limits   = { cpu = "300m", memory = "256Mi" }
          }
          volume_mount {
            name       = "provisioning"
            mount_path = "/etc/grafana/provisioning/datasources/datasource.yaml"
            sub_path   = "datasource.yaml"
          }
          volume_mount {
            name       = "provisioning"
            mount_path = "/etc/grafana/provisioning/dashboards/dashboards.yaml"
            sub_path   = "dashboards.yaml"
          }
          volume_mount {
            name       = "provisioning"
            mount_path = "/var/lib/grafana/dashboards/taskapi.json"
            sub_path   = "taskapi.json"
          }
        }
        volume {
          name = "provisioning"
          config_map { name = kubernetes_config_map_v1.grafana_provisioning.metadata[0].name }
        }
      }
    }
  }
}

resource "kubernetes_service_v1" "grafana" {
  metadata {
    name      = "grafana"
    namespace = kubernetes_namespace_v1.monitoring.metadata[0].name
  }
  spec {
    selector = { app = "grafana" }
    port {
      port        = 3000
      target_port = 3000
    }
    type = "LoadBalancer" # http://localhost:3000
  }
}

# ─────────────────────────── Cuenta de despliegue para Jenkins (mínimo privilegio) ───────────────────────────
# Solo puede tocar los recursos de la app dentro de su namespace (no todo el clúster)
resource "kubernetes_service_account_v1" "jenkins_deployer" {
  metadata {
    name      = "jenkins-deployer"
    namespace = var.app_namespace
  }
}

resource "kubernetes_role_v1" "jenkins_deployer" {
  metadata {
    name      = "jenkins-deployer"
    namespace = var.app_namespace
  }
  rule {
    api_groups = ["", "apps", "autoscaling"]
    resources  = ["deployments", "replicasets", "pods", "services", "configmaps", "horizontalpodautoscalers"]
    verbs      = ["get", "list", "watch", "create", "update", "patch"]
  }
}

resource "kubernetes_role_binding_v1" "jenkins_deployer" {
  metadata {
    name      = "jenkins-deployer"
    namespace = var.app_namespace
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role_v1.jenkins_deployer.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account_v1.jenkins_deployer.metadata[0].name
    namespace = var.app_namespace
  }
}
