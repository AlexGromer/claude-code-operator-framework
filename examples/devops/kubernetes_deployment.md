# Few-Shot Example: Kubernetes Deployment with Best Practices

**Domain:** DevOps / Kubernetes
**Skill Level:** Intermediate
**Pattern:** Production-ready K8s manifests with security + observability

---

## User Query

```
Create a Kubernetes deployment for a web application with 3 replicas, resource limits, and health checks.
```

---

## Exemplary Response

### Complete Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp
  namespace: production
  labels:
    app: webapp
    version: v1.2.3
    environment: production
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # Zero-downtime deployments
  selector:
    matchLabels:
      app: webapp
  template:
    metadata:
      labels:
        app: webapp
        version: v1.2.3
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      # Security Context (Pod-level)
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault

      # Service Account
      serviceAccountName: webapp-sa
      automountServiceAccountToken: true

      containers:
      - name: webapp
        image: myregistry/webapp:v1.2.3
        imagePullPolicy: IfNotPresent

        # Resource Limits & Requests
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"

        # Container Ports
        ports:
        - name: http
          containerPort: 8080
          protocol: TCP

        # Environment Variables
        env:
        - name: ENV
          value: "production"
        - name: LOG_LEVEL
          value: "info"
        - name: DATABASE_HOST
          valueFrom:
            configMapKeyRef:
              name: webapp-config
              key: db_host
        - name: DATABASE_PASSWORD
          valueFrom:
            secretKeyRef:
              name: webapp-secrets
              key: db_password

        # Health Checks
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3

        startupProbe:
          httpGet:
            path: /health/startup
            port: 8080
          initialDelaySeconds: 0
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 30  # Allow 300s for startup

        # Security Context (Container-level)
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL

        # Volume Mounts
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: cache
          mountPath: /app/cache

      # Volumes
      volumes:
      - name: tmp
        emptyDir: {}
      - name: cache
        emptyDir: {}

      # Image Pull Secrets
      imagePullSecrets:
      - name: registry-credentials

      # Affinity Rules (spread across nodes)
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - webapp
              topologyKey: kubernetes.io/hostname

---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: webapp
  namespace: production
  labels:
    app: webapp
spec:
  type: ClusterIP
  selector:
    app: webapp
  ports:
  - name: http
    port: 80
    targetPort: 8080
    protocol: TCP
  sessionAffinity: None

---
# hpa.yaml - Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: webapp-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: webapp
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # 5min cooldown
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60

---
# pdb.yaml - Pod Disruption Budget
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: webapp-pdb
  namespace: production
spec:
  minAvailable: 2  # Always keep 2 pods running
  selector:
    matchLabels:
      app: webapp
```

### Supporting Resources

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: webapp-config
  namespace: production
data:
  db_host: "postgres.database.svc.cluster.local"
  redis_host: "redis.cache.svc.cluster.local"
  log_format: "json"

---
# secret.yaml (create via kubectl, never commit to git)
apiVersion: v1
kind: Secret
metadata:
  name: webapp-secrets
  namespace: production
type: Opaque
data:
  db_password: <base64-encoded-password>

---
# serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: webapp-sa
  namespace: production
automountServiceAccountToken: true

---
# rbac.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: webapp-role
  namespace: production
rules:
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: webapp-rolebinding
  namespace: production
subjects:
- kind: ServiceAccount
  name: webapp-sa
  namespace: production
roleRef:
  kind: Role
  name: webapp-role
  apiGroup: rbac.authorization.k8s.io
```

### Deployment Commands

```bash
# Create namespace (if not exists)
kubectl create namespace production

# Create secrets (NEVER commit to git!)
kubectl create secret generic webapp-secrets \
  --from-literal=db_password="<secure-password>" \
  -n production

# Apply all manifests
kubectl apply -f configmap.yaml
kubectl apply -f serviceaccount.yaml
kubectl apply -f rbac.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f hpa.yaml
kubectl apply -f pdb.yaml

# Verify deployment
kubectl rollout status deployment/webapp -n production
kubectl get pods -n production -l app=webapp
kubectl get hpa -n production
```

### Monitoring & Validation

```bash
# Check pod status
kubectl get pods -n production -l app=webapp -o wide

# View logs
kubectl logs -n production -l app=webapp --tail=100 -f

# Check resource usage
kubectl top pods -n production -l app=webapp

# Test health endpoints
kubectl port-forward -n production svc/webapp 8080:80
curl http://localhost:8080/health/ready

# Verify autoscaling
kubectl get hpa -n production -w
```

---

## Why This Is A Good Example

✅ **Security best practices** — Non-root user, read-only filesystem, dropped capabilities
✅ **Resource management** — Requests + limits for predictable scheduling
✅ **Health checks** — Liveness, readiness, startup probes
✅ **High availability** — PodDisruptionBudget, anti-affinity, zero-downtime rollouts
✅ **Autoscaling** — HPA with CPU + memory metrics
✅ **Observability** — Prometheus annotations, proper labels
✅ **RBAC** — Least-privilege service account
✅ **Complete deployment** — All supporting resources included

---

## Key Patterns

1. **Security-first:** Always use non-root, drop capabilities, read-only filesystem
2. **Resource limits:** Always set both requests and limits
3. **Three health checks:** Liveness (restart), Readiness (traffic), Startup (slow start)
4. **High availability:** PDB + anti-affinity + replicas ≥ 3
5. **Secrets management:** Never hardcode, use Kubernetes Secrets or external vaults
6. **Labels & selectors:** Consistent labeling for observability

---

**Tags:** #kubernetes #deployment #security #ha #best-practices
**Version:** 1.0.0
**Last Updated:** 2026-01-22
