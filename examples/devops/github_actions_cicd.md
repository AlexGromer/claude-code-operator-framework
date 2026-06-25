# Example: GitHub Actions CI/CD Pipeline

## User Request

```
Настрой CI/CD для Python проекта:
- Lint + тесты + coverage
- Build Docker образа
- Deploy в Kubernetes (dev/staging/prod)
- Rollback при падении health checks
```

## Reasoning

**Domain:** DevOps (CI/CD + Kubernetes)
**Complexity:** Medium
**Model:** Sonnet

## Response

### Complete CI/CD Workflow

```yaml
# .github/workflows/cicd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  release:
    types: [created]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # Stage 1: Code Quality
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install flake8 black isort mypy pylint

      - name: Run formatters check
        run: |
          black --check .
          isort --check-only .

      - name: Run linters
        run: |
          flake8 . --max-line-length=100
          pylint src/

      - name: Run type checker
        run: mypy src/

  # Stage 2: Tests & Coverage
  test:
    runs-on: ubuntu-latest
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
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt

      - name: Run tests
        run: |
          pytest --cov=src --cov-report=xml --cov-report=term-missing
        env:
          DATABASE_URL: postgresql://postgres:testpass@localhost:5432/test

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true

      - name: Check coverage threshold
        run: |
          COVERAGE=$(python -c "import xml.etree.ElementTree as ET; print(ET.parse('coverage.xml').getroot().get('line-rate'))")
          if (( $(echo "$COVERAGE < 0.80" | bc -l) )); then
            echo "❌ Coverage $COVERAGE < 80%"
            exit 1
          fi

  # Stage 3: Security Scan
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Trivy scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  # Stage 4: Build & Push Docker Image
  build:
    needs: [lint, test, security]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    outputs:
      image_tag: ${{ steps.meta.outputs.tags }}
      image_digest: ${{ steps.build.outputs.digest }}

    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Log in to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix={{branch}}-

      - name: Build and push
        id: build
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # Stage 5: Deploy to Dev
  deploy-dev:
    needs: build
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment:
      name: development
      url: https://dev.example.com

    steps:
      - uses: actions/checkout@v3

      - name: Setup kubectl
        uses: azure/setup-kubectl@v3

      - name: Configure kubeconfig
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBECONFIG_DEV }}" | base64 -d > ~/.kube/config

      - name: Deploy with Helm
        run: |
          helm upgrade --install myapp ./helm/myapp \
            --namespace dev \
            --create-namespace \
            --set image.tag=${{ needs.build.outputs.image_tag }} \
            --wait --timeout 5m

      - name: Verify deployment
        run: |
          kubectl rollout status deployment/myapp -n dev
          kubectl wait --for=condition=ready pod -l app=myapp -n dev --timeout=300s

  # Stage 6: Deploy to Production
  deploy-prod:
    needs: build
    if: github.event_name == 'release'
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://api.example.com

    steps:
      - uses: actions/checkout@v3

      - name: Setup kubectl
        uses: azure/setup-kubectl@v3

      - name: Configure kubeconfig
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBECONFIG_PROD }}" | base64 -d > ~/.kube/config

      - name: Deploy with Helm (atomic = auto-rollback)
        run: |
          helm upgrade --install myapp ./helm/myapp \
            --namespace production \
            --create-namespace \
            --set image.tag=${{ github.event.release.tag_name }} \
            --wait --timeout 10m \
            --atomic  # Auto-rollback on failure

      - name: Health check
        run: |
          sleep 30
          HEALTH=$(curl -s https://api.example.com/health | jq -r '.status')
          if [ "$HEALTH" != "healthy" ]; then
            echo "❌ Health check failed, rolling back..."
            helm rollback myapp --namespace production
            exit 1
          fi

      - name: Run smoke tests
        run: |
          curl -f https://api.example.com/health || exit 1
          curl -f https://api.example.com/metrics || exit 1

      - name: Notify Slack
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "✅ Deployed ${{ github.event.release.tag_name }} to production",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "🚀 *Deployment Successful*\n*Version:* ${{ github.event.release.tag_name }}\n*Environment:* Production\n*URL:* https://api.example.com"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Key Takeaways

1. **Multi-stage pipeline** — lint → test → build → deploy
2. **Atomic deployments** — auto-rollback with Helm `--atomic`
3. **Health checks** — verify deployment health before completing
4. **Environment gates** — manual approval for production via GitHub Environments
5. **Cache optimization** — Docker layer caching with `cache-from`/`cache-to`

**Best Practices:** Coverage threshold, security scanning, smoke tests, notifications
**Tools:** GitHub Actions, Helm, kubectl, Docker Buildx
