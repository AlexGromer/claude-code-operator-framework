# Few-Shot Example: Stack Migration Planning

## Task
Пользователь: "Нужно мигрировать с Jenkins на GitLab CI. Составь план миграции."

## Solution

### Executive Summary

**Миграция:** Jenkins → GitLab CI
**Оценка длительности:** 4-6 недель
**Риски:** MEDIUM (параллельный запуск обеих систем снижает риск downtime)
**Rollback strategy:** Возможность вернуться к Jenkins в любой момент до cutover

---

## Phase 1: Assessment & Discovery (1 неделя)

### 1.1 Инвентаризация текущих Jenkins pipelines

**Actions:**
```bash
# Экспорт всех Jenkins jobs
java -jar jenkins-cli.jar -s http://jenkins.local/ list-jobs --username admin --password TOKEN > jenkins-jobs.txt

# Экспорт конфигураций
for job in $(cat jenkins-jobs.txt); do
  java -jar jenkins-cli.jar -s http://jenkins.local/ get-job "$job" > "jenkins-configs/${job}.xml"
done

# Анализ используемых плагинов
curl -u admin:TOKEN http://jenkins.local/pluginManager/api/json?depth=1 | jq '.plugins[] | {shortName, version}' > plugins.json
```

**Deliverables:**
- ✅ Список всех Jenkins jobs (Jenkinsfile locations)
- ✅ Список используемых плагинов
- ✅ Зависимости между jobs
- ✅ Список секретов и credentials
- ✅ Список shared libraries

### 1.2 Mapping Jenkins → GitLab CI Features

| Jenkins Feature | GitLab CI Equivalent | Migration Complexity |
|----------------|---------------------|---------------------|
| **Jenkinsfile** | `.gitlab-ci.yml` | 🟡 MEDIUM (syntax conversion) |
| **Pipeline** | Pipeline | 🟢 LOW (concept 1:1) |
| **Stage** | `stage:` | 🟢 LOW (direct mapping) |
| **Step** | `script:` | 🟢 LOW |
| **Agent** | `tags:` (GitLab Runner) | 🟡 MEDIUM (runner setup) |
| **Post actions** | `after_script:` | 🟢 LOW |
| **When conditions** | `rules:` or `only:` / `except:` | 🟡 MEDIUM (syntax different) |
| **Parallel stages** | `parallel:` | 🟢 LOW |
| **Parameters** | CI/CD Variables | 🟢 LOW |
| **Credentials** | CI/CD Variables (masked/protected) | 🟡 MEDIUM (migration process) |
| **Shared Library** | CI/CD Components / includes | 🟠 HIGH (requires refactoring) |
| **Build artifacts** | `artifacts:` | 🟢 LOW |
| **Build triggers** | Webhooks / Pipeline triggers | 🟢 LOW |
| **Blue Ocean UI** | GitLab Pipeline UI | 🟢 LOW (better UX) |
| **Multibranch pipeline** | GitLab Auto DevOps | 🟢 LOW |

### 1.3 Определение blockers

**Критические зависимости (могут заблокировать миграцию):**
1. ✅ **Специфичные Jenkins плагины без аналогов** → Исследовать alternatives
2. ✅ **Custom Groovy scripts в Shared Library** → Портировать в Bash/Python
3. ✅ **Интеграции с legacy системами** → Проверить API compatibility
4. ✅ **Сложные матричные builds** → Использовать GitLab `parallel:matrix:`
5. ✅ **Blue Ocean dashboards** → Migrate to GitLab Merge Request pipelines

**Mitigation strategies:**
- Для специфичных плагинов: containerize logic (Docker image)
- Для Groovy scripts: rewrite в Bash/Python, use GitLab CI/CD Components
- Для legacy integrations: API wrappers в отдельных services

---

## Phase 2: PoC (Proof of Concept) (1 неделя)

### 2.1 Конвертация 1-2 простых pipelines

**Выбор кандидатов для PoC:**
- ✅ Простой pipeline (build → test → deploy)
- ✅ Без сложных зависимостей
- ✅ Не критичный для production

**Example: Jenkins → GitLab CI conversion**

**Jenkinsfile (before):**
```groovy
pipeline {
    agent {
        docker {
            image 'node:18'
        }
    }
    stages {
        stage('Build') {
            steps {
                sh 'npm ci'
                sh 'npm run build'
            }
        }
        stage('Test') {
            steps {
                sh 'npm test'
            }
        }
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                sh './deploy.sh'
            }
        }
    }
    post {
        always {
            junit 'test-results/*.xml'
        }
    }
}
```

**.gitlab-ci.yml (after):**
```yaml
stages:
  - build
  - test
  - deploy

variables:
  NODE_VERSION: "18"

default:
  image: node:${NODE_VERSION}
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - node_modules/

build:
  stage: build
  script:
    - npm ci
    - npm run build
  artifacts:
    paths:
      - dist/
    expire_in: 1 week

test:
  stage: test
  script:
    - npm test
  artifacts:
    reports:
      junit: test-results/*.xml

deploy:
  stage: deploy
  script:
    - ./deploy.sh
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
  environment:
    name: production
```

### 2.2 Настройка GitLab Runner

**Options:**
1. **Shared runners** (GitLab.com) — простейший вариант
2. **Specific runners** (self-hosted) — для sensitive data
3. **Group runners** — shared across multiple projects

**Setup specific runner (self-hosted):**
```bash
# Install GitLab Runner
curl -L https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh | sudo bash
sudo apt-get install gitlab-runner

# Register runner
sudo gitlab-runner register \
  --url https://gitlab.com/ \
  --registration-token PROJECT_TOKEN \
  --executor docker \
  --docker-image alpine:latest \
  --description "docker-runner" \
  --tag-list "docker,linux" \
  --run-untagged="true" \
  --locked="false"

# Verify
sudo gitlab-runner verify
sudo gitlab-runner list
```

**Runner configuration (`/etc/gitlab-runner/config.toml`):**
```toml
concurrent = 4
check_interval = 0

[[runners]]
  name = "docker-runner"
  url = "https://gitlab.com/"
  token = "RUNNER_TOKEN"
  executor = "docker"
  [runners.docker]
    tls_verify = false
    image = "alpine:latest"
    privileged = false
    disable_cache = false
    volumes = ["/cache"]
    shm_size = 0
  [runners.cache]
    Type = "s3"
    Shared = true
    [runners.cache.s3]
      ServerAddress = "s3.amazonaws.com"
      BucketName = "gitlab-runner-cache"
      BucketLocation = "us-east-1"
```

### 2.3 Тестирование PoC pipeline

**Validation checklist:**
- ✅ Build успешно завершается
- ✅ Tests проходят и результаты видны в GitLab UI
- ✅ Artifacts сохраняются и доступны для скачивания
- ✅ Deploy срабатывает только на `main` branch
- ✅ Environment tracking работает
- ✅ Pipeline execution time сравним с Jenkins (или быстрее)

**Success criteria:**
- PoC pipeline работает без ошибок
- Время выполнения: ±20% от Jenkins
- Team комфортно с GitLab UI

---

## Phase 3: Bulk Migration (2-4 недели)

### 3.1 Конвертация всех pipelines

**Strategy: Параллельный запуск (Jenkins + GitLab CI)**

**Benefits:**
- ✅ Zero downtime
- ✅ Постепенная миграция (по одному pipeline за раз)
- ✅ Возможность rollback в любой момент
- ✅ Team постепенно привыкает к GitLab CI

**Process:**
1. Конвертировать Jenkinsfile → `.gitlab-ci.yml`
2. Добавить `.gitlab-ci.yml` в repository
3. Trigger оба pipeline (Jenkins + GitLab) параллельно
4. Сравнить результаты
5. Если GitLab CI работает корректно → disable Jenkins job
6. Перейти к следующему pipeline

**Automation tool:**
```bash
# Используем jenkins2gitlab converter (open source)
git clone https://github.com/vbauzysvmware/jenkins-to-gitlab
cd jenkins-to-gitlab

# Convert Jenkinsfile
python3 jenkins_to_gitlab.py --input Jenkinsfile --output .gitlab-ci.yml

# Manual review required! Converter не идеален
```

### 3.2 Миграция секретов и credentials

**Jenkins Credentials → GitLab CI/CD Variables**

**Export from Jenkins:**
```bash
# Get all credentials
java -jar jenkins-cli.jar -s http://jenkins.local/ \
  groovy = <<EOF
import com.cloudbees.plugins.credentials.*;

def creds = CredentialsProvider.lookupCredentials(
  Credentials.class
)

creds.each { c ->
  println("${c.id}: ${c.description}")
}
EOF
```

**Import to GitLab:**
```bash
# Using GitLab API
curl --request POST "https://gitlab.com/api/v4/projects/${PROJECT_ID}/variables" \
  --header "PRIVATE-TOKEN: ${GITLAB_TOKEN}" \
  --form "key=AWS_ACCESS_KEY_ID" \
  --form "value=AKIAIOSFODNN7EXAMPLE" \
  --form "masked=true" \
  --form "protected=true" \
  --form "environment_scope=production"
```

**Variable types mapping:**
| Jenkins | GitLab CI | Notes |
|---------|-----------|-------|
| Secret text | Masked variable | Use `masked: true` |
| Username/Password | 2 masked variables | `USER` and `PASS` |
| SSH key | File variable | Use `variable_type: file` |
| Certificate | File variable | Use `variable_type: file` |
| Secret file | File variable | Use `variable_type: file` |

### 3.3 Shared Library → CI/CD Components

**Jenkins Shared Library (before):**
```groovy
// vars/deployApp.groovy
def call(Map config) {
    sh "kubectl apply -f ${config.manifest}"
    sh "kubectl rollout status deployment/${config.name}"
}
```

**GitLab CI/CD Component (after):**
```yaml
# templates/deploy.yml
.deploy_template:
  stage: deploy
  image: bitnami/kubectl:latest
  script:
    - kubectl apply -f ${MANIFEST}
    - kubectl rollout status deployment/${APP_NAME}
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
```

**Usage:**
```yaml
# .gitlab-ci.yml
include:
  - local: 'templates/deploy.yml'

deploy_production:
  extends: .deploy_template
  variables:
    MANIFEST: k8s/production.yml
    APP_NAME: myapp
```

### 3.4 Update webhooks & integrations

**Services to update:**
- ✅ GitHub/GitLab webhooks (trigger на push/PR)
- ✅ Slack notifications (Jenkins plugin → GitLab integration)
- ✅ Jira integration (link commits → issues)
- ✅ SonarQube (quality gate)
- ✅ Artifactory / Nexus (artifact upload)
- ✅ PagerDuty / OpsGenie (alerting)

**GitLab Slack integration:**
```yaml
# .gitlab-ci.yml
notify_success:
  stage: .post
  script:
    - 'curl -X POST --data-urlencode "payload={\"text\": \"Build SUCCESS: ${CI_PROJECT_NAME} - ${CI_COMMIT_REF_NAME}\"}" ${SLACK_WEBHOOK_URL}'
  when: on_success

notify_failure:
  stage: .post
  script:
    - 'curl -X POST --data-urlencode "payload={\"text\": \"Build FAILED: ${CI_PROJECT_NAME} - ${CI_COMMIT_REF_NAME}\"}" ${SLACK_WEBHOOK_URL}'
  when: on_failure
```

---

## Phase 4: Cutover & Decommission (1 неделя)

### 4.1 Final cutover

**Pre-cutover checklist:**
- ✅ Все pipelines успешно работают в GitLab CI >1 недели
- ✅ Team обучен GitLab CI workflows
- ✅ Все секреты мигрированы
- ✅ Все интеграции переключены на GitLab
- ✅ Monitoring настроен (pipeline failures → alerts)
- ✅ Documentation обновлена

**Cutover steps:**
1. Announcement: "Jenkins будет отключен через 48 часов"
2. Disable new builds в Jenkins (read-only mode)
3. Дождаться завершения всех running jobs
4. Final backup Jenkins configuration
5. Stop Jenkins service
6. Remove webhooks pointing to Jenkins

### 4.2 Мониторинг GitLab CI stability

**Key metrics to monitor (first 2 weeks):**
- ✅ Pipeline success rate (target: ≥95%)
- ✅ Pipeline execution time (compare with Jenkins baseline)
- ✅ Number of pipeline failures due to GitLab CI bugs
- ✅ Runner capacity (queue time, concurrent jobs)
- ✅ Artifact storage usage

**Alerting rules:**
```yaml
# Prometheus alert
- alert: GitLabCIPipelineFailureSpike
  expr: rate(gitlab_ci_pipeline_failure_total[5m]) > 0.1
  for: 10m
  annotations:
    summary: "High pipeline failure rate"
```

### 4.3 Documentation

**Update:**
- ✅ CI/CD documentation → migrate to GitLab CI syntax
- ✅ Onboarding guides for new developers
- ✅ Troubleshooting runbook
- ✅ Architecture Decision Records (ADR)

**Create:**
- ✅ `.gitlab-ci.yml` best practices guide
- ✅ GitLab Runner maintenance guide
- ✅ Pipeline optimization guide
- ✅ Secrets management guide

### 4.4 Jenkins decommission

**After 4 weeks of stable GitLab CI operation:**
1. ✅ Final export of Jenkins historical data (build logs, artifacts)
2. ✅ Archive Jenkins configuration to S3/archive storage
3. ✅ Decommission Jenkins servers
4. ✅ Remove Jenkins from monitoring
5. ✅ Update DNS/firewall rules

---

## Migration Complexity Matrix

| Pipeline Type | Complexity | Estimated Time | Notes |
|--------------|-----------|----------------|-------|
| **Simple build+test** | 🟢 LOW | 1-2 hours | Direct 1:1 mapping |
| **Multibranch pipeline** | 🟢 LOW | 2-4 hours | GitLab handles this natively |
| **Matrix builds** | 🟡 MEDIUM | 4-8 hours | Use `parallel:matrix:` |
| **Shared Library usage** | 🟡 MEDIUM | 1-2 days | Refactor to CI/CD Components |
| **Custom plugins** | 🟠 HIGH | 2-5 days | Containerize or rewrite |
| **Blue Ocean UI customization** | 🟡 MEDIUM | N/A | Use GitLab native UI |

---

## Risk Management

| Risk | Impact | Probability | Mitigation |
|------|--------|------------|-----------|
| **Pipeline downtime** | HIGH | LOW | Parallel run Jenkins + GitLab CI |
| **Lost historical data** | MEDIUM | LOW | Full Jenkins backup before migration |
| **Team resistance** | MEDIUM | MEDIUM | Training sessions, gradual migration |
| **Secrets exposure** | CRITICAL | LOW | Audit all variable visibility settings |
| **Performance regression** | MEDIUM | LOW | Benchmark before/after, optimize runners |
| **Blocker plugins** | HIGH | MEDIUM | Research alternatives early (Phase 1) |

---

## Cost Analysis

### Jenkins (current)

**Infrastructure:**
- 3x Jenkins master (HA setup): $500/month
- 10x Jenkins agents: $1,000/month
- Maintenance: 20h/month × $50/h = $1,000/month
- **Total: $2,500/month**

### GitLab CI (after migration)

**Option A: GitLab.com SaaS (shared runners)**
- GitLab Premium: $19/user/month × 20 users = $380/month
- Shared runners: included (2000 CI/CD minutes/month free, then $10/1000 min)
- Estimated extra minutes: 5000 min/month = $30/month
- **Total: $410/month** (84% cost reduction)

**Option B: Self-hosted GitLab + runners**
- GitLab instance: 1x VM ($100/month)
- GitLab runners: 5x VMs ($500/month)
- Maintenance: 10h/month × $50/h = $500/month
- **Total: $1,100/month** (56% cost reduction)

**Recommendation:** Start with GitLab.com SaaS (Option A), migrate to self-hosted if needed.

---

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|-----------------|
| **Phase 1: Assessment** | 1 week | Inventory, mapping, blocker analysis |
| **Phase 2: PoC** | 1 week | 2 working pipelines, runner setup |
| **Phase 3: Bulk Migration** | 2-4 weeks | All pipelines migrated, parallel run |
| **Phase 4: Cutover** | 1 week | Jenkins decommissioned, monitoring |
| **TOTAL** | **5-7 weeks** | Full migration complete |

---

## Success Criteria

✅ **Migration complete when:**
1. 100% of pipelines migrated to GitLab CI
2. Pipeline success rate ≥95% for 2 consecutive weeks
3. Jenkins fully decommissioned
4. Team trained and comfortable with GitLab CI
5. Documentation updated
6. Cost savings realized (≥50% reduction)

---

**Authoritative Sources:**
- GitLab CI/CD Documentation: https://docs.gitlab.com/ee/ci/
- Jenkins Migration Guide: https://about.gitlab.com/blog/2023/03/17/migrating-from-jenkins/
- GitLab Runner Documentation: https://docs.gitlab.com/runner/
- CI/CD Components: https://docs.gitlab.com/ee/ci/components/
