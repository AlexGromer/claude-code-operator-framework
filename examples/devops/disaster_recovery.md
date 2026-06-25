# Example: Kubernetes Disaster Recovery Plan

## User Request

```
Создай план disaster recovery для K8s кластера: backup etcd, восстановление, тесты DR.
```

## Reasoning

**Domain:** DevOps (disaster recovery)
**Complexity:** Medium
**Model:** Sonnet

## Response

### Automated Backup with Velero

```bash
# Install Velero
velero install \
    --provider aws \
    --bucket k8s-backups \
    --secret-file ./credentials-velero \
    --backup-location-config region=us-east-1 \
    --snapshot-location-config region=us-east-1

# Create backup schedule
velero schedule create daily-backup \
    --schedule="0 2 * * *" \
    --include-namespaces="production,staging" \
    --ttl 720h  # 30 days retention

# Manual backup
velero backup create production-$(date +%Y%m%d) \
    --include-namespaces production \
    --wait

# Verify backup
velero backup describe production-20260127
```

### etcd Backup Script

```bash
#!/bin/bash
# etcd-backup.sh

set -euo pipefail

BACKUP_DIR="/var/backups/etcd"
RETENTION_DAYS=30
ETCD_ENDPOINTS="https://127.0.0.1:2379"
ETCD_CACERT="/etc/kubernetes/pki/etcd/ca.crt"
ETCD_CERT="/etc/kubernetes/pki/etcd/server.crt"
ETCD_KEY="/etc/kubernetes/pki/etcd/server.key"

mkdir -p "$BACKUP_DIR"

# Create snapshot
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SNAPSHOT_PATH="$BACKUP_DIR/etcd-snapshot-$TIMESTAMP.db"

ETCDCTL_API=3 etcdctl snapshot save "$SNAPSHOT_PATH" \
    --endpoints="$ETCD_ENDPOINTS" \
    --cacert="$ETCD_CACERT" \
    --cert="$ETCD_CERT" \
    --key="$ETCD_KEY"

# Verify snapshot
ETCDCTL_API=3 etcdctl snapshot status "$SNAPSHOT_PATH" --write-out=table

# Compress
gzip "$SNAPSHOT_PATH"

# Upload to S3
aws s3 cp "${SNAPSHOT_PATH}.gz" "s3://k8s-etcd-backups/$(hostname)/"

# Cleanup old backups
find "$BACKUP_DIR" -name "etcd-snapshot-*.db.gz" -mtime +$RETENTION_DAYS -delete

echo "✅ etcd backup complete: ${SNAPSHOT_PATH}.gz"
```

### Restore Procedure

```bash
#!/bin/bash
# etcd-restore.sh

SNAPSHOT_FILE="$1"

if [ -z "$SNAPSHOT_FILE" ]; then
    echo "Usage: ./etcd-restore.sh <snapshot-file>"
    exit 1
fi

# Stop kube-apiserver
systemctl stop kube-apiserver

# Restore etcd from snapshot
ETCDCTL_API=3 etcdctl snapshot restore "$SNAPSHOT_FILE" \
    --data-dir="/var/lib/etcd-restore" \
    --name="$(hostname)" \
    --initial-cluster="master=https://10.0.1.10:2380" \
    --initial-advertise-peer-urls="https://$(hostname -i):2380"

# Backup current etcd data
mv /var/lib/etcd /var/lib/etcd.backup-$(date +%Y%m%d_%H%M%S)

# Replace with restored data
mv /var/lib/etcd-restore /var/lib/etcd

# Restart services
systemctl start etcd
systemctl start kube-apiserver
systemctl start kube-controller-manager
systemctl start kube-scheduler

echo "✅ etcd restored from $SNAPSHOT_FILE"
```

### Velero Restore

```bash
# List available backups
velero backup get

# Restore from backup
velero restore create --from-backup production-20260127 --wait

# Restore specific namespace
velero restore create prod-restore \
    --from-backup production-20260127 \
    --include-namespaces production \
    --wait

# Monitor restore
velero restore describe prod-restore
kubectl get pods -n production --watch
```

### DR Test Automation

```bash
#!/bin/bash
# dr-test.sh - Monthly DR drill

set -euo pipefail

echo "🔥 Starting DR test..."

# 1. Create test namespace
kubectl create namespace dr-test

# 2. Deploy test application
kubectl apply -f test-app.yaml -n dr-test

# 3. Create backup
velero backup create dr-test-backup --include-namespaces dr-test --wait

# 4. Delete namespace (simulate disaster)
kubectl delete namespace dr-test

# 5. Wait for deletion
sleep 30

# 6. Restore from backup
velero restore create dr-test-restore --from-backup dr-test-backup --wait

# 7. Verify restoration
PODS_READY=$(kubectl get pods -n dr-test -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' | grep -c True)
EXPECTED_PODS=3

if [ "$PODS_READY" -eq "$EXPECTED_PODS" ]; then
    echo "✅ DR test PASSED - $PODS_READY/$EXPECTED_PODS pods restored"
else
    echo "❌ DR test FAILED - only $PODS_READY/$EXPECTED_PODS pods restored"
    exit 1
fi

# Cleanup
kubectl delete namespace dr-test
velero backup delete dr-test-backup --confirm
velero restore delete dr-test-restore --confirm

echo "✅ DR test complete"
```

### RTO/RPO Monitoring

```yaml
# prometheus-dr-metrics.yml
groups:
  - name: disaster_recovery
    rules:
      - record: backup:age_seconds
        expr: time() - velero_backup_last_successful_timestamp

      - alert: BackupTooOld
        expr: backup:age_seconds > 86400  # 24 hours
        labels:
          severity: critical
        annotations:
          summary: "Backup is too old (> 24h)"
          description: "Last successful backup was {{ $value | humanizeDuration }} ago"

      - alert: BackupFailed
        expr: velero_backup_failure_total > 0
        labels:
          severity: critical
        annotations:
          summary: "Backup failure detected"
```

---

## Key Takeaways

1. **Automated backups** — daily schedule with 30-day retention
2. **Multiple layers** — Velero (app-level) + etcd (cluster-level)
3. **Regular testing** — monthly DR drills to verify restore
4. **RTO < 1 hour** — automated restore procedures
5. **RPO < 24 hours** — daily backups minimum

**RTO:** Recovery Time Objective (how long to restore)
**RPO:** Recovery Point Objective (how much data loss acceptable)
**Tools:** Velero, etcdctl, S3
