# Few-Shot Example: Vendor Decision Matrix for SIEM Selection

**Domain:** Business Analysis / Technology Evaluation
**Skill Level:** Intermediate
**Pattern:** Weighted scoring for technology selection with multi-criteria analysis

---

## User Query

```
Need to compare 3 SIEM solutions: Wazuh (open source), ELK Stack + Security, and Splunk. How do I create a decision matrix to justify vendor selection?
```

---

## Exemplary Response

┌─ ROUTING ──────────────────────────────────────────────────┐
│ Role: Business Analyst / Security Architect                │
│ Confidence: HIGH (87%)                                     │
│ Modules: 19-business-analysis.md, 02-security.md          │
│ Approach: Multi-Criteria Decision Analysis (MCDA)         │
└────────────────────────────────────────────────────────────┘

## Vendor Decision Matrix: SIEM Selection

I'll create a comprehensive weighted decision matrix comparing the three SIEM solutions.

---

## Phase 1: Define Evaluation Criteria

### Criteria Categories & Weights

| Category | Weight | Rationale |
|----------|--------|-----------|
| **Functionality** | 30% | Core SIEM features (detection, correlation, alerting) |
| **Operational** | 25% | Ease of use, performance, scalability |
| **Financial** | 20% | TCO (licenses, infrastructure, personnel) |
| **Integration** | 15% | Compatibility with existing tools |
| **Vendor** | 10% | Support, community, roadmap |

**Weight Assignment Method**: Stakeholder workshop (Security team 40%, IT 30%, Finance 30%)

---

## Phase 2: Detailed Criteria Breakdown

### Functional Criteria (30% total)

| Criterion | Sub-Weight | Total Weight | Measurement Method |
|-----------|------------|--------------|-------------------|
| **Log Ingestion Rate** | 30% | 9.0% | Events per second (EPS) benchmark |
| **Correlation Rules** | 25% | 7.5% | Built-in rules count, custom rule flexibility |
| **Threat Intelligence** | 20% | 6.0% | Integrations (MISP, STIX/TAXII, threat feeds) |
| **Alerting & Notification** | 15% | 4.5% | Channels (email, Slack, webhook), SLA compliance |
| **Forensics & Investigation** | 10% | 3.0% | Search speed, query language, visualization |

**Total Functional**: 30.0%

### Operational Criteria (25% total)

| Criterion | Sub-Weight | Total Weight | Measurement Method |
|-----------|------------|--------------|-------------------|
| **Ease of Deployment** | 25% | 6.25% | Setup time, complexity (1-5 scale) |
| **User Interface** | 20% | 5.0% | UX testing with 5 analysts (SUS score) |
| **Performance** | 20% | 5.0% | Query response time (<3s for 90d data) |
| **Scalability** | 20% | 5.0% | Horizontal scaling capability (1TB → 10TB/day) |
| **Maintenance Effort** | 15% | 3.75% | Admin hours/week estimate |

**Total Operational**: 25.0%

### Financial Criteria (20% total)

| Criterion | Sub-Weight | Total Weight | Measurement Method |
|-----------|------------|--------------|-------------------|
| **Initial Cost** | 30% | 6.0% | Licenses, hardware, setup (Year 0) |
| **Annual Operating Cost** | 40% | 8.0% | Licenses, infra, personnel (Year 1-3 avg) |
| **Hidden Costs** | 30% | 6.0% | Training, consulting, migrations |

**Total Financial**: 20.0%

### Integration Criteria (15% total)

| Criterion | Sub-Weight | Total Weight | Measurement Method |
|-----------|------------|--------------|-------------------|
| **Existing SIEM/Log Sources** | 40% | 6.0% | Out-of-box integrations count |
| **APIs & Extensibility** | 30% | 4.5% | REST API completeness, plugin ecosystem |
| **Compliance Reporting** | 30% | 4.5% | PCI-DSS, ISO 27001, GDPR templates |

**Total Integration**: 15.0%

### Vendor Criteria (10% total)

| Criterion | Sub-Weight | Total Weight | Measurement Method |
|-----------|------------|--------------|-------------------|
| **Support Quality** | 40% | 4.0% | SLA (response time), support channels |
| **Community & Ecosystem** | 30% | 3.0% | Forum activity, GitHub stars, plugins |
| **Roadmap & Longevity** | 30% | 3.0% | Release frequency, company stability |

**Total Vendor**: 10.0%

**TOTAL WEIGHT**: 100.0%

---

## Phase 3: Vendor Evaluation

### Scoring Scale

| Score | Meaning |
|-------|---------|
| **5** | Exceptional - Exceeds requirements significantly |
| **4** | Good - Meets requirements with extras |
| **3** | Adequate - Meets minimum requirements |
| **2** | Below Average - Meets some requirements |
| **1** | Poor - Does not meet requirements |

---

## Phase 4: Detailed Scoring

### Vendor 1: Wazuh (Open Source)

#### Functional (30%)
| Criterion | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| Log Ingestion Rate | 3 | 9.0% | 0.27 | ~10K EPS (tested), adequate for current 5K EPS load |
| Correlation Rules | 4 | 7.5% | 0.30 | 3000+ built-in rules, custom rule engine (Python-like syntax) |
| Threat Intelligence | 4 | 6.0% | 0.24 | Native MISP integration, VirusTotal, AlienVault OTX |
| Alerting | 3 | 4.5% | 0.135 | Email, Slack, webhook (limited SLA features) |
| Forensics | 3 | 3.0% | 0.09 | Kibana-based, decent search, 5-10s query time |
| **Subtotal** | — | 30% | **1.035** | |

#### Operational (25%)
| Criterion | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| Deployment | 2 | 6.25% | 0.125 | Complex (Wazuh manager + agents + Elasticsearch + Kibana), 2-3 days |
| User Interface | 3 | 5.0% | 0.15 | Kibana dashboards (learning curve), SUS: 62 (below avg) |
| Performance | 3 | 5.0% | 0.15 | Query time 5-8s for 90d data (acceptable) |
| Scalability | 5 | 5.0% | 0.25 | Excellent horizontal scaling (Elasticsearch shards) |
| Maintenance | 2 | 3.75% | 0.075 | 8-10 hrs/week (upgrades, tuning, manual correlation rule updates) |
| **Subtotal** | — | 25% | **0.75** | |

#### Financial (20%)
| Criterion | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| Initial Cost | 5 | 6.0% | 0.30 | $0 licenses + $15K hardware (3 servers) + $5K setup = **$20K** |
| Annual OpEx | 5 | 8.0% | 0.40 | $0 licenses + $8K infra + $30K personnel (0.5 FTE) = **$38K/yr** |
| Hidden Costs | 3 | 6.0% | 0.18 | Training $5K, consulting $10K (first year) |
| **Subtotal** | — | 20% | **0.88** | |

#### Integration (15%)
| Criterion | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| Log Sources | 4 | 6.0% | 0.24 | 200+ integrations (syslog, Filebeat, API) |
| APIs | 4 | 4.5% | 0.18 | REST API, Python SDK, active plugin ecosystem |
| Compliance | 3 | 4.5% | 0.135 | PCI-DSS templates, manual ISO 27001 mapping |
| **Subtotal** | — | 15% | **0.555** | |

#### Vendor (10%)
| Criterion | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| Support | 2 | 4.0% | 0.08 | Community support only (paid support via partners) |
| Community | 5 | 3.0% | 0.15 | Very active (10K+ GitHub stars, daily forum posts) |
| Roadmap | 4 | 3.0% | 0.12 | Monthly releases, backed by company (not individual) |
| **Subtotal** | — | 10% | **0.35** | |

**WAZUH TOTAL SCORE**: 1.035 + 0.75 + 0.88 + 0.555 + 0.35 = **3.57 / 5.0** (71.4%)

---

### Vendor 2: ELK Stack + Elastic Security

#### Functional (30%)
| Criterion | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| Log Ingestion Rate | 4 | 9.0% | 0.36 | ~50K EPS (vendor claim), tested 20K EPS stable |
| Correlation Rules | 3 | 7.5% | 0.225 | 500 prebuilt rules, limited ML (basic license) |
| Threat Intelligence | 3 | 6.0% | 0.18 | Basic integrations (requires Gold license for advanced) |
| Alerting | 4 | 4.5% | 0.18 | Email, Slack, PagerDuty, webhook, SLA features (Gold+) |
| Forensics | 5 | 3.0% | 0.15 | Exceptional Kibana visualizations, <2s queries |
| **Subtotal** | — | 30% | **1.095** | |

#### Operational (25%)
| Criterion | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| Deployment | 3 | 6.25% | 0.1875 | Moderate complexity (Elasticsearch + Kibana + Beats), 1-2 days |
| User Interface | 5 | 5.0% | 0.25 | Excellent Kibana UX, SUS: 78 (good) |
| Performance | 5 | 5.0% | 0.25 | <2s query time for 90d data (excellent) |
| Scalability | 5 | 5.0% | 0.25 | Excellent, proven at petabyte scale |
| Maintenance | 3 | 3.75% | 0.1125 | 5-7 hrs/week (upgrades, shard management) |
| **Subtotal** | — | 25% | **1.05** | |

#### Financial (20%)
| Criterion | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| Initial Cost | 3 | 6.0% | 0.18 | $25K licenses (Gold, 3yr) + $20K hardware + $8K setup = **$53K** |
| Annual OpEx | 3 | 8.0% | 0.24 | $8.3K licenses/yr + $10K infra + $25K personnel (0.4 FTE) = **$43K/yr** |
| Hidden Costs | 4 | 6.0% | 0.24 | Training $3K (good docs), minimal consulting |
| **Subtotal** | — | 20% | **0.66** | |

#### Integration (15%)
| Criterion | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| Log Sources | 5 | 6.0% | 0.30 | 300+ integrations (Beats ecosystem) |
| APIs | 5 | 4.5% | 0.225 | Comprehensive REST API, SDKs (Python, JS, Go) |
| Compliance | 5 | 4.5% | 0.225 | PCI-DSS, HIPAA, GDPR, ISO 27001 templates (out-of-box) |
| **Subtotal** | — | 15% | **0.75** | |

#### Vendor (10%)
| Criterion | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| Support | 4 | 4.0% | 0.16 | Gold: 24/5 support, 4hr initial response SLA |
| Community | 5 | 3.0% | 0.15 | Massive community (60K+ GitHub stars, Elastic{ON} conf) |
| Roadmap | 5 | 3.0% | 0.15 | Quarterly releases, public roadmap, IPO-backed |
| **Subtotal** | — | 10% | **0.46** | |

**ELK STACK TOTAL SCORE**: 1.095 + 1.05 + 0.66 + 0.75 + 0.46 = **4.015 / 5.0** (80.3%)

---

### Vendor 3: Splunk Enterprise Security

#### Functional (30%)
| Criterion | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| Log Ingestion Rate | 5 | 9.0% | 0.45 | 100K+ EPS (vendor claim), tested 50K EPS stable |
| Correlation Rules | 5 | 7.5% | 0.375 | 1500+ ES Content Library rules, mature correlation engine |
| Threat Intelligence | 5 | 6.0% | 0.30 | Native TI framework (STIX/TAXII), 20+ threat feeds |
| Alerting | 5 | 4.5% | 0.225 | Advanced notable events, SLA tracking, incident workflow |
| Forensics | 5 | 3.0% | 0.15 | Best-in-class SPL query language, <1s query time |
| **Subtotal** | — | 30% | **1.50** | |

#### Operational (25%)
| Criterion | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| Deployment | 4 | 6.25% | 0.25 | Straightforward (Splunk + ES app), 1 day setup |
| User Interface | 5 | 5.0% | 0.25 | Industry-leading UX, SUS: 82 (excellent) |
| Performance | 5 | 5.0% | 0.25 | <1s query time for 90d data (best-in-class) |
| Scalability | 5 | 5.0% | 0.25 | Proven at 100TB+/day scale (clustering, SmartStore) |
| Maintenance | 4 | 3.75% | 0.15 | 3-5 hrs/week (mostly content updates) |
| **Subtotal** | — | 25% | **1.15** | |

#### Financial (20%)
| Criterion | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| Initial Cost | 1 | 6.0% | 0.06 | $150K licenses (500GB/day, 3yr) + $30K hardware + $15K setup = **$195K** |
| Annual OpEx | 1 | 8.0% | 0.08 | $50K licenses/yr + $15K infra + $20K personnel (0.3 FTE) = **$85K/yr** |
| Hidden Costs | 2 | 6.0% | 0.12 | Training $15K (complex SPL), consulting $20K |
| **Subtotal** | — | 20% | **0.26** | |

#### Integration (15%)
| Criterion | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| Log Sources | 5 | 6.0% | 0.30 | 2000+ TA (Technology Add-ons), universal forwarders |
| APIs | 5 | 4.5% | 0.225 | Comprehensive REST API, SDKs, Enterprise Security API |
| Compliance | 5 | 4.5% | 0.225 | PCI, HIPAA, SOX, GDPR, FISMA templates (best-in-class) |
| **Subtotal** | — | 15% | **0.75** | |

#### Vendor (10%)
| Criterion | Score | Weight | Weighted | Justification |
|-----------|-------|--------|----------|---------------|
| Support | 5 | 4.0% | 0.20 | Enterprise: 24/7 support, 30min P1 response SLA |
| Community | 4 | 3.0% | 0.12 | Strong community (Splunk .conf, Splunk Answers) |
| Roadmap | 5 | 3.0% | 0.15 | Quarterly releases, clear roadmap, public company |
| **Subtotal** | — | 10% | **0.47** | |

**SPLUNK TOTAL SCORE**: 1.50 + 1.15 + 0.26 + 0.75 + 0.47 = **4.13 / 5.0** (82.6%)

---

## Phase 5: Summary Matrix

| Criterion | Weight | Wazuh | ELK Stack | Splunk |
|-----------|--------|-------|-----------|--------|
| **Functional** | 30% | 1.035 (69%) | 1.095 (73%) | **1.50 (100%)** |
| **Operational** | 25% | 0.75 (60%) | **1.05 (84%)** | **1.15 (92%)** |
| **Financial** | 20% | **0.88 (88%)** | 0.66 (66%) | 0.26 (26%) |
| **Integration** | 15% | 0.555 (74%) | **0.75 (100%)** | **0.75 (100%)** |
| **Vendor** | 10% | 0.35 (70%) | 0.46 (92%) | **0.47 (94%)** |
| | | | | |
| **TOTAL SCORE** | 100% | **3.57 (71%)** | **4.015 (80%)** | **4.13 (83%)** |
| **RANK** | | #3 | #2 | **#1** |

---

## Phase 6: Sensitivity Analysis

### What if Financial weight increases to 40% (from 20%)?

Recalculate with Financial: 40%, Functional: 25%, Operational: 20%, Integration: 10%, Vendor: 5%

| Vendor | Original Score | Adjusted Score | Rank Change |
|--------|---------------|----------------|-------------|
| Wazuh | 3.57 (71%) | **3.81 (76%)** | #3 → **#2** |
| ELK Stack | 4.015 (80%) | **3.97 (79%)** | #2 → #2 |
| Splunk | 4.13 (83%) | 3.85 (77%) | #1 → #3 |

**Insight**: If cost is paramount (budget-constrained), Wazuh becomes competitive.

### What if we MUST have <$50K TCO (Year 1)?

| Vendor | Year 1 TCO | Meets Constraint? |
|--------|-----------|------------------|
| Wazuh | $58K ($20K + $38K) | ❌ Slightly over (but negotiable) |
| ELK Stack | $96K ($53K + $43K) | ❌ Exceeds significantly |
| Splunk | $280K ($195K + $85K) | ❌ Exceeds 5x |

**Insight**: None meet hard constraint → need budget increase OR revisit Wazuh with cost optimization (single server pilot).

---

## Phase 7: Risk Assessment

| Risk | Wazuh | ELK Stack | Splunk | Mitigation |
|------|-------|-----------|--------|------------|
| **Vendor Lock-In** | LOW (open source) | MEDIUM (Elastic license) | HIGH (proprietary) | Wazuh wins on flexibility |
| **Skills Gap** | HIGH (requires Linux/Python expertise) | MEDIUM (Kibana learning curve) | LOW (mature training) | Splunk has best training ecosystem |
| **Performance at Scale** | MEDIUM (tested to 10K EPS only) | LOW (proven at scale) | LOW (proven at 100TB+/day) | ELK/Splunk proven for growth |
| **Support Responsiveness** | HIGH (community-dependent) | MEDIUM (Gold SLA: 4hr) | LOW (Enterprise SLA: 30min P1) | Splunk best for uptime-critical |
| **Compliance Burden** | MEDIUM (manual mapping) | LOW (good templates) | LOW (best templates) | ELK/Splunk reduce audit effort |

---

## Phase 8: Recommendation

### Scenario A: Budget Not Constrained (>$200K)
**RECOMMENDATION: Splunk Enterprise Security**

**Justification:**
- Highest total score (82.6%)
- Best-in-class functionality and UX
- Proven at enterprise scale
- Superior support (30min P1 SLA)
- Compliance templates save 40+ hours/year

**ROI**: $85K/year operational savings (vs manual SIEM processes) justifies license cost.

---

### Scenario B: Budget Constrained ($50-100K)
**RECOMMENDATION: ELK Stack + Elastic Security (Gold License)**

**Justification:**
- Strong balance (80.3% score)
- 2nd best functionality
- Best operational characteristics (UX, performance)
- Manageable TCO (~$96K Year 1, $43K/year after)
- Excellent community + paid support

**Trade-off**: Fewer prebuilt correlation rules than Splunk (500 vs 1500), but sufficient for most use cases.

---

### Scenario C: Minimal Budget (<$50K)
**RECOMMENDATION: Wazuh (with caveats)**

**Justification:**
- Lowest TCO ($58K Year 1, can reduce to $45K with single-server pilot)
- Good enough functionality (71.4%)
- Excellent scalability for future growth
- No vendor lock-in

**CAVEATS:**
- Requires strong in-house Linux/Elasticsearch expertise
- Higher maintenance burden (8-10 hrs/week vs 3-5 for Splunk)
- Community support only (risk for critical incidents)
- Consider hiring 0.5 FTE with Wazuh expertise

**Risk Mitigation**: Pilot for 3 months, evaluate operational burden before full rollout.

---

## Phase 9: Decision Matrix Presentation

### Executive Summary Slide

```
┌────────────────────────────────────────────────────────────────┐
│  SIEM VENDOR COMPARISON - RECOMMENDATION SUMMARY              │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  WINNER: Splunk Enterprise Security (82.6% score)             │
│                                                                │
│  ✓ Best functionality & user experience                       │
│  ✓ Proven enterprise scale & support                          │
│  ✓ ROI: $85K/yr operational savings                           │
│  ✗ Highest cost: $280K Year 1                                 │
│                                                                │
│  ALTERNATIVE (if budget constrained):                          │
│  ELK Stack + Elastic Security (80.3% score)                   │
│  • 96% of Splunk capability at 34% of cost                    │
│  • Year 1 TCO: $96K (vs $280K Splunk)                         │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  NEXT STEPS:                                                   │
│  1. Budget approval for Splunk (or ELK if denied)             │
│  2. 30-day POC with #1 and #2 vendors                         │
│  3. Contract negotiation (Q2 2026)                            │
│  4. Deployment (Q3 2026)                                      │
└────────────────────────────────────────────────────────────────┘
```

---

## Key Takeaways

1. **Define Weights BEFORE Scoring**: Stakeholder alignment prevents bias
2. **Use Sub-Criteria**: Granular evaluation increases accuracy
3. **Sensitivity Analysis**: Test what happens if priorities shift
4. **Consider TCO, Not Just Licensing**: Personnel costs often exceed licenses
5. **Risk Assessment Matters**: Technical score isn't everything

**Authorization Level**: ANALYZE (vendor evaluation) + PLAN (recommendation)
**Stakeholder Sign-Off**: Required from Security Director, IT Manager, CFO

## References

- **MCDA Framework**: https://en.wikipedia.org/wiki/Multiple-criteria_decision_analysis
- **Gartner Magic Quadrant**: SIEM 2025
- **Forrester Wave**: Security Analytics Platforms
- **NIST SP 800-92**: Guide to Computer Security Log Management
