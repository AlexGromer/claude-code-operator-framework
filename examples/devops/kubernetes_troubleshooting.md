# Few-Shot Example: Kubernetes Troubleshooting

**Domain:** devops
**Skill Level:** Intermediate
**Pattern:** Observe → Diagnose → Fix → Verify

---

## User Query

My pods are stuck in CrashLoopBackOff state. Here's the output:

```
$ kubectl get pods
NAME                        READY   STATUS             RESTARTS   AGE
myapp-deploy-7b9f8c6d4-abc  0/1     CrashLoopBackOff   5          10m
myapp-deploy-7b9f8c6d4-def  0/1     CrashLoopBackOff   5          10m
myapp-deploy-7b9f8c6d4-ghi  0/1     CrashLoopBackOff   5          10m
```

How do I debug and fix this?

---

## Exemplary Response

### 1. Systematic Troubleshooting Approach

```
CrashLoopBackOff Debugging Flow:
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  1. DESCRIBE POD    ──►  Check Events section for errors                    │
│         │                                                                    │
│         ▼                                                                    │
│  2. CHECK LOGS     ──►  Application startup errors                          │
│         │                                                                    │
│         ▼                                                                    │
│  3. REVIEW RESOURCES ──►  CPU/Memory limits, OOMKilled?                     │
│         │                                                                    │
│         ▼                                                                    │
│  4. CHECK CONFIG    ──►  ConfigMaps, Secrets, Environment                   │
│         │                                                                    │
│         ▼                                                                    │
│  5. VERIFY IMAGE    ──►  Image pull, entrypoint, command                    │
│         │                                                                    │
│         ▼                                                                    │
│  6. TEST LOCALLY    ──►  Run container locally with same config             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Step 1: Describe Pod

```bash
kubectl describe pod myapp-deploy-7b9f8c6d4-abc
```

**Key sections to examine:**

```yaml
# Look for these sections:
Events:
  Type     Reason     Age                From               Message
  ----     ------     ----               ----               -------
  Normal   Scheduled  10m                default-scheduler  Successfully assigned...
  Normal   Pulling    10m                kubelet            Pulling image "myapp:v1.2.3"
  Normal   Pulled     10m                kubelet            Successfully pulled image
  Normal   Created    9m (x5 over 10m)   kubelet            Created container myapp
  Normal   Started    9m (x5 over 10m)   kubelet            Started container myapp
  Warning  BackOff    30s (x20 over 9m)  kubelet            Back-off restarting failed container

# Check Last State:
State:          Waiting
  Reason:       CrashLoopBackOff
Last State:     Terminated
  Reason:       Error         # <-- Or OOMKilled
  Exit Code:    1             # <-- Key indicator
  Started:      ...
  Finished:     ...
```

**Common Exit Codes:**
| Code | Meaning | Likely Cause |
|------|---------|--------------|
| 0 | Success | Shouldn't crash loop |
| 1 | General error | Application error |
| 126 | Permission denied | Entrypoint not executable |
| 127 | Command not found | Wrong entrypoint/command |
| 137 | SIGKILL (OOMKilled) | Memory limit exceeded |
| 143 | SIGTERM | Graceful termination failed |

### 3. Step 2: Check Logs

```bash
# Current container logs
kubectl logs myapp-deploy-7b9f8c6d4-abc

# Previous crashed container logs (IMPORTANT!)
kubectl logs myapp-deploy-7b9f8c6d4-abc --previous

# If multi-container pod
kubectl logs myapp-deploy-7b9f8c6d4-abc -c container-name --previous

# Stream logs
kubectl logs -f myapp-deploy-7b9f8c6d4-abc
```

**Common Log Patterns:**

```
# Database connection error
ERROR: Connection refused to postgres:5432
SOLUTION: Check Service/Endpoint, Network Policy, DB credentials

# Missing config
ERROR: Config file /app/config.yaml not found
SOLUTION: Check ConfigMap mount, volume configuration

# Permission error
ERROR: Permission denied: /data/cache
SOLUTION: Check securityContext.runAsUser, fsGroup

# OOM before logs appear
(No logs, or partial logs)
SOLUTION: Check describe for OOMKilled, increase memory limit
```

### 4. Step 3: Resource Analysis

```bash
# Check if OOMKilled
kubectl describe pod myapp-deploy-7b9f8c6d4-abc | grep -A5 "Last State"

# Check resource usage
kubectl top pod myapp-deploy-7b9f8c6d4-abc

# Check resource requests/limits
kubectl get pod myapp-deploy-7b9f8c6d4-abc -o yaml | grep -A10 resources
```

**If OOMKilled:**
```yaml
# Current (problematic):
resources:
  limits:
    memory: "128Mi"  # Too low!

# Fixed:
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### 5. Step 4: Configuration Check

```bash
# Check environment variables
kubectl exec -it myapp-deploy-7b9f8c6d4-abc -- env

# If pod won't start, use debug container
kubectl debug -it myapp-deploy-7b9f8c6d4-abc --image=busybox --target=myapp

# Check ConfigMap
kubectl get configmap myapp-config -o yaml

# Check Secret (base64 encoded)
kubectl get secret myapp-secret -o jsonpath='{.data.DB_PASSWORD}' | base64 -d

# Verify volume mounts
kubectl get pod myapp-deploy-7b9f8c6d4-abc -o yaml | grep -A20 volumeMounts
```

### 6. Step 5: Image Verification

```bash
# Check image details
kubectl get pod myapp-deploy-7b9f8c6d4-abc -o jsonpath='{.spec.containers[0].image}'

# Test image locally
docker run --rm -it myapp:v1.2.3 /bin/sh

# Check entrypoint
docker inspect myapp:v1.2.3 | jq '.[0].Config.Entrypoint'
docker inspect myapp:v1.2.3 | jq '.[0].Config.Cmd'
```

### 7. Common Issues and Fixes

#### Issue A: Missing Environment Variable

**Symptom:**
```
ERROR: DATABASE_URL environment variable not set
```

**Fix:**
```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: myapp
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: myapp-secret
              key: database-url
```

#### Issue B: Liveness Probe Failing

**Symptom:** Pod starts, runs briefly, then restarts.

**Diagnose:**
```bash
kubectl describe pod myapp-deploy-7b9f8c6d4-abc | grep -A10 "Liveness"
```

**Fix:**
```yaml
# Increase initial delay for slow-starting apps
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 60  # Was: 10
  periodSeconds: 10
  failureThreshold: 3
```

#### Issue C: Resource Limits Too Low

**Symptom:** Exit code 137 (OOMKilled)

**Fix:**
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "1Gi"   # Increased from 256Mi
    cpu: "1000m"
```

#### Issue D: Init Container Failing

**Symptom:** Pod stuck in Init:CrashLoopBackOff

**Diagnose:**
```bash
kubectl logs myapp-deploy-7b9f8c6d4-abc -c init-container-name
```

**Fix:** Ensure init container completes successfully (e.g., database migration, wait for dependency).

#### Issue E: Image Pull Error

**Symptom:** ImagePullBackOff before CrashLoopBackOff

**Fix:**
```yaml
spec:
  imagePullSecrets:
  - name: regcred  # Create: kubectl create secret docker-registry regcred --docker-server=...
  containers:
  - name: myapp
    image: registry.example.com/myapp:v1.2.3
    imagePullPolicy: Always
```

### 8. Quick Diagnostic Commands

```bash
# All-in-one diagnostic
kubectl get pods -o wide && \
kubectl describe pod $POD_NAME && \
kubectl logs $POD_NAME --previous

# Check events cluster-wide
kubectl get events --sort-by=.lastTimestamp | grep -i error

# Resource usage
kubectl top pods
kubectl top nodes

# Network connectivity
kubectl exec -it $POD_NAME -- curl -v http://service-name:port/

# DNS resolution
kubectl exec -it $POD_NAME -- nslookup service-name
```

### 9. Prevention Checklist

```yaml
# deployment-best-practices.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
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
      - name: myapp
        image: myapp:v1.2.3
        imagePullPolicy: IfNotPresent

        # Always set resource limits
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"

        # Health checks with appropriate delays
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
          failureThreshold: 3

        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5

        # Security context
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false

        # Graceful shutdown
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 5"]

      # Pod disruption budget for availability
      terminationGracePeriodSeconds: 30
```

### 10. Verification

After applying fix:
```bash
# Watch pods recover
kubectl get pods -w

# Check new pod is healthy
kubectl describe pod $NEW_POD_NAME | tail -20

# Verify logs are clean
kubectl logs $NEW_POD_NAME | tail -50

# Confirm service is responding
kubectl exec -it $NEW_POD_NAME -- curl localhost:8080/health
```

---

## Why This Is A Good Example

- Systematic debugging flow
- Multiple diagnostic commands
- Common issues with specific fixes
- Prevention checklist for future
- Verification steps

---

## Key Patterns

1. **Describe First** - Events section reveals immediate cause
2. **Previous Logs** - Crashed container logs are critical
3. **Exit Codes** - Numeric hints to problem category
4. **Resource Limits** - OOMKilled is common but hidden

---

**Tags:** #devops #kubernetes #troubleshooting #crashloopbackoff #debugging
**Version:** 1.0.0
**Last Updated:** 2026-01-23
