# Example: Container Security Scanning

## User Request

```
Проверь Docker-образ на уязвимости:
- CVE в зависимостях
- Небезопасная конфигурация
- Секреты в образе
- Rootless setup
```

## Reasoning

**Domain:** Security + DevOps
**Complexity:** Simple (tool integration)
**Model:** Haiku

## Response

### Multi-Tool Scanning Pipeline

```bash
# 1. Trivy - comprehensive vulnerability scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image --severity HIGH,CRITICAL myapp:latest

# 2. Grype - Anchore's vulnerability scanner
grype myapp:latest --scope all-layers

# 3. Snyk - dependency vulnerabilities
snyk container test myapp:latest --severity-threshold=high

# 4. Hadolint - Dockerfile best practices
docker run --rm -i hadolint/hadolint < Dockerfile

# 5. Dockle - container image linter
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  goodwithtech/dockle myapp:latest
```

### Secure Dockerfile Template

```dockerfile
# Use minimal base image
FROM python:3.11-slim-bookworm AS base

# Metadata
LABEL maintainer="security@example.com"
LABEL org.opencontainers.image.source="https://github.com/org/repo"

# Security: Run as non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install dependencies as root
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=appuser:appuser . /app

# Security: Switch to non-root
USER appuser

# Security: Read-only filesystem (except /tmp)
VOLUME ["/tmp"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
EXPOSE 8000
CMD ["python", "app.py"]
```

### CI/CD Integration

```yaml
# .github/workflows/container-scan.yml
name: Container Security Scan

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Run Snyk
        uses: snyk/actions/docker@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          image: myapp:${{ github.sha }}
          args: --severity-threshold=high

      - name: Fail on HIGH/CRITICAL
        run: |
          trivy image --exit-code 1 --severity HIGH,CRITICAL myapp:${{ github.sha }}
```

### Scanning Script

```bash
#!/bin/bash
# scan-container.sh

IMAGE=$1
if [ -z "$IMAGE" ]; then
    echo "Usage: ./scan-container.sh <image:tag>"
    exit 1
fi

echo "🔍 Scanning $IMAGE..."

# Vulnerability scan
echo "📦 Running Trivy..."
trivy image --severity HIGH,CRITICAL --format json --output trivy.json $IMAGE

# Configuration scan
echo "🔧 Running Dockle..."
dockle --exit-code 1 --exit-level warn $IMAGE

# Secrets scan
echo "🔐 Scanning for secrets..."
docker save $IMAGE -o /tmp/image.tar
trufflehog filesystem /tmp/image.tar --json > secrets.json
rm /tmp/image.tar

# Generate report
echo "📊 Generating report..."
VULNS=$(jq '[.Results[].Vulnerabilities[] | select(.Severity=="HIGH" or .Severity=="CRITICAL")] | length' trivy.json)
SECRETS=$(jq 'length' secrets.json)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Scan Results for $IMAGE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐛 Vulnerabilities (HIGH/CRITICAL): $VULNS"
echo "🔐 Secrets found: $SECRETS"

if [ "$VULNS" -gt 0 ] || [ "$SECRETS" -gt 0 ]; then
    echo "❌ SECURITY ISSUES DETECTED"
    exit 1
else
    echo "✅ No critical issues found"
    exit 0
fi
```

---

## Key Takeaways

1. **Multi-tool approach** — Trivy + Snyk + Dockle comprehensive coverage
2. **Non-root user** — always run containers as non-root
3. **Minimal base images** — alpine/slim variants reduce attack surface
4. **CI/CD integration** — block builds with HIGH/CRITICAL CVEs
5. **Regular scans** — schedule weekly scans of production images

**Tools:** Trivy, Grype, Snyk, Hadolint, Dockle
**Standards:** CIS Docker Benchmark
