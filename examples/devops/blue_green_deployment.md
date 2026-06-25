# Example: Blue-Green Deployment Strategy

## User Request

```
Реализуй blue-green deployment для безопасного обновления production без даунтайма.
```

## Reasoning

**Domain:** DevOps (deployment strategies)
**Complexity:** Medium
**Model:** Sonnet

## Response

### Kubernetes Blue-Green with Service Selector Switch

```yaml
# deployment-blue.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-blue
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
      version: blue
  template:
    metadata:
      labels:
        app: myapp
        version: blue
    spec:
      containers:
      - name: app
        image: myapp:v1.0.0
        ports:
        - containerPort: 8080

---
# deployment-green.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-green
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
      version: green
  template:
    metadata:
      labels:
        app: myapp
        version: green
    spec:
      containers:
      - name: app
        image: myapp:v1.1.0
        ports:
        - containerPort: 8080

---
# service.yaml (initially points to blue)
apiVersion: v1
kind: Service
metadata:
  name: myapp
  namespace: production
spec:
  selector:
    app: myapp
    version: blue  # Switch this to 'green' for cutover
  ports:
  - port: 80
    targetPort: 8080
```

### Deployment Script

```bash
#!/bin/bash
# blue-green-deploy.sh

set -euo pipefail

NAMESPACE="production"
APP="myapp"
NEW_VERSION="$1"
CURRENT_COLOR=$(kubectl get svc $APP -n $NAMESPACE -o jsonpath='{.spec.selector.version}')

if [ "$CURRENT_COLOR" = "blue" ]; then
    NEXT_COLOR="green"
else
    NEXT_COLOR="blue"
fi

echo "🔵 Current: $CURRENT_COLOR"
echo "🟢 Deploying: $NEXT_COLOR (version: $NEW_VERSION)"

# Step 1: Deploy new version to inactive environment
echo "📦 Deploying $NEXT_COLOR environment..."
kubectl set image deployment/$APP-$NEXT_COLOR \
    app=myapp:$NEW_VERSION \
    -n $NAMESPACE

# Step 2: Wait for rollout
echo "⏳ Waiting for $NEXT_COLOR rollout..."
kubectl rollout status deployment/$APP-$NEXT_COLOR -n $NAMESPACE --timeout=300s

# Step 3: Health check on new environment
echo "🏥 Running health checks on $NEXT_COLOR..."
GREEN_POD=$(kubectl get pod -n $NAMESPACE -l app=$APP,version=$NEXT_COLOR -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n $NAMESPACE $GREEN_POD -- curl -sf http://localhost:8080/health || {
    echo "❌ Health check failed on $NEXT_COLOR, aborting"
    exit 1
}

# Step 4: Smoke tests
echo "🧪 Running smoke tests on $NEXT_COLOR..."
kubectl port-forward -n $NAMESPACE deployment/$APP-$NEXT_COLOR 18080:8080 &
PF_PID=$!
sleep 3

curl -sf http://localhost:18080/api/test || {
    echo "❌ Smoke tests failed"
    kill $PF_PID
    exit 1
}

kill $PF_PID
echo "✅ Smoke tests passed"

# Step 5: Switch traffic
echo "🔄 Switching traffic from $CURRENT_COLOR to $NEXT_COLOR..."
read -p "Ready to switch production traffic? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment aborted by user"
    exit 1
fi

kubectl patch svc $APP -n $NAMESPACE -p "{\"spec\":{\"selector\":{\"version\":\"$NEXT_COLOR\"}}}"

echo "✅ Traffic switched to $NEXT_COLOR"

# Step 6: Monitor new environment
echo "📊 Monitoring $NEXT_COLOR for 60 seconds..."
sleep 60

ERROR_RATE=$(kubectl logs deployment/$APP-$NEXT_COLOR -n $NAMESPACE --since=60s | grep -c ERROR || true)
if [ "$ERROR_RATE" -gt 10 ]; then
    echo "⚠️  High error rate detected: $ERROR_RATE errors"
    read -p "Rollback to $CURRENT_COLOR? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl patch svc $APP -n $NAMESPACE -p "{\"spec\":{\"selector\":{\"version\":\"$CURRENT_COLOR\"}}}"
        echo "↩️  Rolled back to $CURRENT_COLOR"
        exit 1
    fi
fi

echo "✅ Deployment complete!"
echo "💡 Old $CURRENT_COLOR environment is still running (for rollback if needed)"
echo "🗑️  To cleanup old environment: kubectl delete deployment $APP-$CURRENT_COLOR -n $NAMESPACE"
```

### Automated Blue-Green with Argo Rollouts

```yaml
# rollout.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: app
        image: myapp:v1.0.0
        ports:
        - containerPort: 8080
  strategy:
    blueGreen:
      activeService: myapp-active
      previewService: myapp-preview
      autoPromotionEnabled: false  # Manual approval required
      scaleDownDelaySeconds: 300   # Keep old version for 5 min
      prePromotionAnalysis:
        templates:
        - templateName: success-rate-check
        args:
        - name: service-name
          value: myapp-preview

---
# analysis-template.yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate-check
  namespace: production
spec:
  metrics:
  - name: success-rate
    interval: 30s
    successCondition: result >= 0.95
    provider:
      prometheus:
        address: http://prometheus:9090
        query: |
          sum(rate(http_requests_total{job="myapp",code=~"2.."}[5m]))
          /
          sum(rate(http_requests_total{job="myapp"}[5m]))
```

### Promote/Rollback Commands

```bash
# Promote green to production (Argo Rollouts)
kubectl argo rollouts promote myapp -n production

# Rollback to previous version
kubectl argo rollouts undo myapp -n production

# Abort ongoing rollout
kubectl argo rollouts abort myapp -n production
```

---

## Key Takeaways

1. **Zero-downtime** — both versions run simultaneously during switch
2. **Instant rollback** — just switch service selector back
3. **Automated analysis** — Argo Rollouts with Prometheus metrics
4. **Manual gate** — require approval before traffic switch
5. **Gradual cleanup** — keep old version for 5 min for quick rollback

**Trade-offs:** Requires 2x resources during deployment
**Alternative:** Canary deployment for gradual rollout
**Tools:** kubectl, Argo Rollouts, Prometheus
