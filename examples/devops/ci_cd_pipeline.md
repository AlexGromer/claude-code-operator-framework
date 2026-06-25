# Few-Shot Example: CI/CD Pipeline for Microservices

**Domain:** DevOps / CI/CD
**Skill Level:** Advanced
**Pattern:** Complete pipeline with testing, security scanning, deployment

---

## User Query

```
Design a CI/CD pipeline for a microservices application with automated testing, security scanning, and deployment to Kubernetes.
```

---

## Exemplary Response

### Pipeline Overview

```
┌─────────────┐   ┌──────────┐   ┌─────────┐   ┌──────────┐   ┌────────┐
│ Source Code │──>│  Build   │──>│  Test   │──>│ Security │──>│ Deploy │
│  (Git Push) │   │ & Package│   │  Suite  │   │  Scan    │   │  to K8s│
└─────────────┘   └──────────┘   └─────────┘   └──────────┘   └────────┘
                        │              │             │             │
                   Docker Image    Unit Tests   Trivy/Snyk    ArgoCD/Helm
```

### GitHub Actions Pipeline

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # Job 1: Code Quality & Linting
  lint:
    name: Lint and Code Quality
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install pylint black isort mypy

      - name: Run Black (formatter check)
        run: black --check .

      - name: Run isort (import sorting)
        run: isort --check-only .

      - name: Run pylint
        run: pylint src/

      - name: Run mypy (type checking)
        run: mypy src/

  # Job 2: Unit Tests & Coverage
  test:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests with coverage
        run: |
          pytest --cov=src --cov-report=xml --cov-report=term

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true

      - name: Check coverage threshold
        run: |
          coverage report --fail-under=80

  # Job 3: Build Docker Image
  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: test
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=sha,prefix={{branch}}-

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache
          cache-to: type=registry,ref=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:buildcache,mode=max

  # Job 4: Security Scanning
  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ needs.build.outputs.image-tag }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Run Snyk security scan
        uses: snyk/actions/docker@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          image: ${{ needs.build.outputs.image-tag }}
          args: --severity-threshold=high

      - name: Run gitleaks (secrets detection)
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  # Job 5: Integration Tests
  integration-test:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: build
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run integration tests
        run: |
          docker run --network container:postgres \
            -e DATABASE_URL=postgresql://postgres:testpass@localhost/testdb \
            ${{ needs.build.outputs.image-tag }} \
            pytest tests/integration/

  # Job 6: Deploy to Staging
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: [security-scan, integration-test]
    if: github.ref == 'refs/heads/develop'
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup kubectl
        uses: azure/setup-kubectl@v3

      - name: Configure kubectl
        run: |
          echo "${{ secrets.KUBECONFIG_STAGING }}" | base64 -d > kubeconfig
          export KUBECONFIG=./kubeconfig

      - name: Update deployment image
        run: |
          kubectl set image deployment/myapp \
            myapp=${{ needs.build.outputs.image-tag }} \
            -n staging

      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/myapp -n staging --timeout=5m

      - name: Run smoke tests
        run: |
          curl -f https://staging.example.com/health || exit 1

  # Job 7: Deploy to Production
  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [security-scan, integration-test]
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://example.com
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup kubectl
        uses: azure/setup-kubectl@v3

      - name: Configure kubectl
        run: |
          echo "${{ secrets.KUBECONFIG_PROD }}" | base64 -d > kubeconfig
          export KUBECONFIG=./kubeconfig

      - name: Create backup of current deployment
        run: |
          kubectl get deployment/myapp -n production -o yaml > backup-deployment.yaml

      - name: Deploy with Helm
        run: |
          helm upgrade --install myapp ./helm/myapp \
            --namespace production \
            --set image.tag=${{ needs.build.outputs.image-tag }} \
            --set replicaCount=3 \
            --wait --timeout=10m

      - name: Run production smoke tests
        run: |
          ./scripts/smoke-tests.sh production

      - name: Notify Slack
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "✅ Deployment to production successful: ${{ github.sha }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}

  # Job 8: Rollback (manual trigger)
  rollback:
    name: Rollback Production
    runs-on: ubuntu-latest
    if: github.event_name == 'workflow_dispatch'
    environment: production
    steps:
      - name: Rollback deployment
        run: |
          kubectl rollout undo deployment/myapp -n production
          kubectl rollout status deployment/myapp -n production
```

### Dockerfile (Multi-stage)

```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Security: Non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application
COPY --chown=appuser:appuser src/ ./src/

# Security: Read-only filesystem
USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')"

EXPOSE 8080

CMD ["python", "-m", "src.main"]
```

---

## Why This Is A Good Example

✅ **Complete pipeline** — Lint → Test → Build → Scan → Deploy
✅ **Security-first** — Trivy, Snyk, gitleaks scanning
✅ **Quality gates** — Coverage thresholds, security checks
✅ **Environment separation** — Staging → Production with approvals
✅ **Rollback capability** — Manual rollback workflow
✅ **Observability** — Slack notifications, status checks

---

## Key Patterns

1. **Job dependencies** (`needs`) for sequential execution
2. **Environment protection** for production deployments
3. **Secrets management** via GitHub Secrets
4. **Multi-stage Docker** builds for smaller images
5. **Health checks** after deployment
6. **Rollback strategy** for quick recovery

---

**Tags:** #cicd #github-actions #kubernetes #docker #security-scanning
**Version:** 1.0.0
**Last Updated:** 2026-01-22
