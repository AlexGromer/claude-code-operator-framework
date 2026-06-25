# Example: Helm Chart Creation & Deployment

## User Request

```
Создай Helm chart для микросервиса с:
- ConfigMap для конфигурации
- Secret для credentials
- HPA (Horizontal Pod Autoscaler)
- Ingress с TLS
- Health checks
```

## Reasoning

**Domain:** DevOps (Kubernetes + Helm)
**Complexity:** Medium (multi-resource orchestration)
**Model:** Sonnet

## Response

### Helm Chart Structure

```
myservice/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── hpa.yaml
│   ├── ingress.yaml
│   ├── serviceaccount.yaml
│   └── _helpers.tpl
└── .helmignore
```

### Chart.yaml

```yaml
apiVersion: v2
name: myservice
description: Production-ready microservice Helm chart
type: application
version: 1.0.0
appVersion: "1.0.0"
keywords:
  - microservice
  - api
maintainers:
  - name: DevOps Team
    email: devops@example.com
```

### values.yaml

```yaml
replicaCount: 3

image:
  repository: myregistry.io/myservice
  pullPolicy: IfNotPresent
  tag: "1.0.0"

serviceAccount:
  create: true
  annotations: {}
  name: ""

service:
  type: ClusterIP
  port: 8080
  targetPort: 8080

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
  hosts:
    - host: api.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: api-tls
      hosts:
        - api.example.com

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

resources:
  limits:
    cpu: 1000m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi

probes:
  liveness:
    httpGet:
      path: /health/live
      port: 8080
    initialDelaySeconds: 30
    periodSeconds: 10
    timeoutSeconds: 5
    failureThreshold: 3
  readiness:
    httpGet:
      path: /health/ready
      port: 8080
    initialDelaySeconds: 10
    periodSeconds: 5
    timeoutSeconds: 3
    failureThreshold: 3

config:
  LOG_LEVEL: "info"
  DB_POOL_SIZE: "20"
  CACHE_TTL: "3600"

secrets:
  DATABASE_URL: ""  # Set via --set or values override
  API_KEY: ""
```

### templates/deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "myservice.fullname" . }}
  labels:
    {{- include "myservice.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "myservice.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        checksum/secret: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}
      labels:
        {{- include "myservice.selectorLabels" . | nindent 8 }}
    spec:
      serviceAccountName: {{ include "myservice.serviceAccountName" . }}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        ports:
        - name: http
          containerPort: {{ .Values.service.targetPort }}
          protocol: TCP
        envFrom:
        - configMapRef:
            name: {{ include "myservice.fullname" . }}
        - secretRef:
            name: {{ include "myservice.fullname" . }}
        livenessProbe:
          {{- toYaml .Values.probes.liveness | nindent 10 }}
        readinessProbe:
          {{- toYaml .Values.probes.readiness | nindent 10 }}
        resources:
          {{- toYaml .Values.resources | nindent 10 }}
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir: {}
```

### templates/hpa.yaml

```yaml
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "myservice.fullname" . }}
  labels:
    {{- include "myservice.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "myservice.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: {{ .Values.autoscaling.targetMemoryUtilizationPercentage }}
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
{{- end }}
```

### Deployment Commands

```bash
# Validate chart
helm lint myservice/

# Dry-run to check rendered manifests
helm install myservice ./myservice --dry-run --debug

# Install with custom values
helm install myservice ./myservice \
  --namespace production \
  --create-namespace \
  --set image.tag=1.0.1 \
  --set secrets.DATABASE_URL="postgres://..." \
  --set secrets.API_KEY="sk-..." \
  --wait --timeout 5m

# Upgrade with rollback on failure
helm upgrade myservice ./myservice \
  --namespace production \
  --reuse-values \
  --set image.tag=1.0.2 \
  --wait --timeout 5m \
  --atomic

# Rollback if needed
helm rollback myservice --namespace production

# Monitor deployment
kubectl rollout status deployment/myservice -n production
```

---

## Key Takeaways

1. **Template helpers** — reduce duplication with `_helpers.tpl`
2. **Checksum annotations** — trigger rolling update on config changes
3. **HPA with behavior** — gradual scale-down, fast scale-up
4. **Security contexts** — non-root, read-only filesystem
5. **Atomic upgrades** — auto-rollback on failure with `--atomic`

**Best Practices:** Values validation, resource limits, health checks, TLS
**Tools:** Helm 3, kubectl, cert-manager
