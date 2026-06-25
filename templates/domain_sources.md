# Domain Source List Template

**Domain**: [security | devops | programming | research | documentation | compliance | tools | general]
**Maintainer**: [Name/Team]
**Last Updated**: YYYY-MM-DD

---

## Overview

**Domain Description**:
[Brief description of this domain and what types of sources are relevant]

**Source Count**: XX sources (TIER_1: X, TIER_2: X, TIER_3: X, TIER_4: X)

**Coverage Status**: [Comprehensive | Good | Adequate | Limited | Needs Expansion]

---

## Primary Sources (TIER_1)

**Authoritative, official documentation, academic papers, vendor sources**

### 1. [Source Name]

- **URL**: https://example.com
- **Type**: [Official Docs | Academic | Vendor | Standard]
- **Coverage**: [What topics this source covers]
- **Update Frequency**: [daily | weekly | monthly | annually]
- **Last Verified**: YYYY-MM-DD
- **Quality Score**: X.XX / 1.0
- **Use Cases**:
  - [Use case 1]
  - [Use case 2]

### 2. [Source Name]

- **URL**: https://example.com
- **Type**: [Official Docs | Academic | Vendor | Standard]
- **Coverage**: [What topics this source covers]
- **Update Frequency**: [daily | weekly | monthly | annually]
- **Last Verified**: YYYY-MM-DD
- **Quality Score**: X.XX / 1.0
- **Use Cases**:
  - [Use case 1]
  - [Use case 2]

---

## Secondary Sources (TIER_2)

**Major platforms, established projects, curated content**

### 1. [Source Name]

- **URL**: https://example.com
- **Type**: [Platform | Project | Curated List | Reference]
- **Coverage**: [What topics this source covers]
- **Update Frequency**: [daily | weekly | monthly]
- **Last Verified**: YYYY-MM-DD
- **Quality Score**: X.XX / 1.0
- **Use Cases**:
  - [Use case 1]
  - [Use case 2]

### 2. [Source Name]

- **URL**: https://example.com
- **Type**: [Platform | Project | Curated List | Reference]
- **Coverage**: [What topics this source covers]
- **Update Frequency**: [daily | weekly | monthly]
- **Last Verified**: YYYY-MM-DD
- **Quality Score**: X.XX / 1.0
- **Use Cases**:
  - [Use case 1]
  - [Use case 2]

---

## Community Sources (TIER_3)

**Forums, blogs, community wikis**

### 1. [Source Name]

- **URL**: https://example.com
- **Type**: [Forum | Blog | Wiki | Community]
- **Coverage**: [What topics this source covers]
- **Update Frequency**: [daily | weekly | monthly]
- **Last Verified**: YYYY-MM-DD
- **Quality Score**: X.XX / 1.0
- **Verification Required**: Yes
- **Use Cases**:
  - [Use case 1]
  - [Use case 2]

### 2. [Source Name]

- **URL**: https://example.com
- **Type**: [Forum | Blog | Wiki | Community]
- **Coverage**: [What topics this source covers]
- **Update Frequency**: [daily | weekly | monthly]
- **Last Verified**: YYYY-MM-DD
- **Quality Score**: X.XX / 1.0
- **Verification Required**: Yes
- **Use Cases**:
  - [Use case 1]
  - [Use case 2]

---

## Tools & Documentation

**Tool documentation, SDKs, libraries, frameworks**

### 1. [Tool Name]

- **URL**: https://example.com/docs
- **Type**: [CLI Tool | Library | Framework | SDK]
- **Documentation Quality**: [Excellent | Good | Adequate | Poor]
- **Version Coverage**: [Latest | Multiple Versions | Specific Version]
- **Last Verified**: YYYY-MM-DD
- **Use Cases**:
  - [Use case 1]
  - [Use case 2]

### 2. [Tool Name]

- **URL**: https://example.com/docs
- **Type**: [CLI Tool | Library | Framework | SDK]
- **Documentation Quality**: [Excellent | Good | Adequate | Poor]
- **Version Coverage**: [Latest | Multiple Versions | Specific Version]
- **Last Verified**: YYYY-MM-DD
- **Use Cases**:
  - [Use case 1]
  - [Use case 2]

---

## Domain-Specific Customization Guide

### Recommended Source Types for This Domain

**Essential**:
- [Type 1]: [Why essential]
- [Type 2]: [Why essential]

**Highly Recommended**:
- [Type 1]: [Why recommended]
- [Type 2]: [Why recommended]

**Optional**:
- [Type 1]: [When useful]
- [Type 2]: [When useful]

### Quality Thresholds

**Minimum Quality Score by Tier**:
- TIER_1: ≥ 0.90
- TIER_2: ≥ 0.75
- TIER_3: ≥ 0.60
- TIER_4: No minimum (pending assessment)

### Domain-Specific Requirements

**For [Domain Name] sources, require**:
1. [Requirement 1]
2. [Requirement 2]
3. [Requirement 3]

### Source Diversity Requirements

**Coverage should include**:
- [ ] Official vendor documentation
- [ ] Community-driven resources
- [ ] Academic/research sources
- [ ] Practical tutorials/guides
- [ ] Tool-specific documentation

**Geographic/Language Diversity**:
- [ ] International sources
- [ ] Russian-language sources (if applicable)
- [ ] Multi-language support

---

## Domain Source Selection Criteria (GAP-DOM-002)

### Universal Criteria (All Domains)

**Minimum Requirements:**
1. **Accessibility**: Must be publicly accessible or access method documented
2. **Recency**: Content updated within staleness threshold for tier
3. **Accuracy**: No known misinformation or critical errors
4. **Authority**: Author/organization identifiable and credible
5. **Language**: English or Russian (or translation available)

**Quality Scoring:**
- Authority: 35% weight
- Freshness: 20% weight
- Relevance: 15% weight
- Accessibility: 15% weight
- Depth: 15% weight

**Minimum Overall Score by Tier:**
- TIER_1: ≥ 85/100
- TIER_2: ≥ 70/100
- TIER_3: ≥ 55/100
- TIER_4: No minimum (under assessment)

### Domain-Specific Criteria

#### Security Domain

**Essential Source Types:**
- **Vulnerability Databases**: NVD, CVE, vendor advisories
- **Security Standards**: OWASP, NIST, ISO 27001
- **Research**: Academic papers, security conferences (Black Hat, DEF CON)
- **Tools**: Official documentation for security tools

**Domain-Specific Requirements:**
1. **Timeliness**: Security content must be current (max 6 months for TIER_1)
2. **CVE References**: Must cite CVE numbers where applicable
3. **Vendor Confirmation**: Vulnerabilities verified by vendor
4. **Exploit Availability**: Indicate if exploit code is public
5. **Remediation**: Must include mitigation/patching guidance

**Minimum Quality Thresholds:**
- TIER_1: CVE database, official vendor advisory, security standard body
- TIER_2: Security research firm, established security blog
- TIER_3: Community security discussions (verified by multiple sources)

#### DevOps Domain

**Essential Source Types:**
- **Official Docs**: Kubernetes, Terraform, Ansible, Docker, etc.
- **Cloud Providers**: AWS, GCP, Azure documentation
- **IaC Guides**: Best practices, reference architectures
- **CI/CD Tools**: Jenkins, GitLab CI, GitHub Actions docs

**Domain-Specific Requirements:**
1. **Version Specificity**: Must indicate tool/platform version
2. **Code Examples**: Include working examples (tested)
3. **Best Practices**: Align with official recommendations
4. **Production-Ready**: Examples suitable for production use
5. **Migration Paths**: Document upgrade/migration procedures

**Minimum Quality Thresholds:**
- TIER_1: Official vendor documentation, cloud provider docs
- TIER_2: Major DevOps platforms (GitHub, GitLab), established projects
- TIER_3: Community guides (verified by multiple practitioners)

#### Programming Domain

**Essential Source Types:**
- **Language Docs**: Official Python, JavaScript, Go, Rust documentation
- **Framework Docs**: React, Vue, Django, Flask, etc.
- **API References**: Comprehensive API documentation
- **Package Registries**: PyPI, npm, crates.io

**Domain-Specific Requirements:**
1. **Version Currency**: Document language/framework version
2. **Code Correctness**: Code examples must compile/run
3. **Type Safety**: Include type hints where applicable
4. **Deprecation Notices**: Flag deprecated features
5. **Performance Considerations**: Discuss performance implications

**Minimum Quality Thresholds:**
- TIER_1: Official language documentation, major framework docs
- TIER_2: Established library/tool documentation, major tech blogs
- TIER_3: Community tutorials (code tested and verified)

#### Research Domain

**Essential Source Types:**
- **Academic Databases**: arXiv, ACM, IEEE, ScienceDirect
- **Peer Review**: Peer-reviewed journals and conferences
- **Preprints**: arXiv, bioRxiv (with peer review status noted)
- **Institution Repos**: University research repositories

**Domain-Specific Requirements:**
1. **Peer Review Status**: Indicate if peer-reviewed
2. **Citation Count**: Prefer highly-cited papers
3. **Author Credentials**: Authors with recognized expertise
4. **Reproducibility**: Methods section allows reproduction
5. **Data Availability**: Datasets/code available where applicable

**Minimum Quality Thresholds:**
- TIER_1: Peer-reviewed journal/conference, arXiv with high citations
- TIER_2: Preprints from recognized institutions, workshop papers
- TIER_3: Technical reports, non-peer-reviewed (use with caution)

#### Compliance Domain

**Essential Source Types:**
- **Regulatory Bodies**: Official GDPR, NIST, ISO texts
- **Government Sites**: ФЗ-152 (Russia), CCPA (California), etc.
- **Standards Organizations**: ISO, NIST, PCI SSC
- **Legal Resources**: Official legal interpretations

**Domain-Specific Requirements:**
1. **Legal Authority**: Must be official or legally recognized
2. **Jurisdiction**: Specify applicable jurisdiction (EU, Russia, US, etc.)
3. **Effective Date**: Include regulation effective/update dates
4. **Official Translation**: Use official translations for non-English regs
5. **Amendment Tracking**: Note amendments and updates

**Minimum Quality Thresholds:**
- TIER_1: Official government/regulatory body publications
- TIER_2: Recognized standards organizations, legal firms
- TIER_3: Compliance communities (cross-reference with TIER_1)

### Source Diversity Requirements by Domain

**Security**: MUST include vulnerability databases + security standards + research
**DevOps**: MUST include official tool docs + cloud provider docs + IaC guides
**Programming**: MUST include language docs + framework docs + package registries
**Research**: MUST include peer-reviewed sources + preprint servers
**Compliance**: MUST include official regulations + standards bodies

### Exclusion Criteria

**Never Accept:**
- Sources with known misinformation history
- Plagiarized content (copied without attribution)
- Spam/ad-heavy sites (ratio: ads > content)
- Paywalled without institutional access
- Malicious content or phishing sites
- Sources promoting illegal activities (except security research)

### Replacement Criteria

**Replace existing source if new source has:**
1. **Higher Authority**: Official doc vs community blog
2. **Better Freshness**: Updated within 6 months vs 2+ years old
3. **Greater Depth**: Comprehensive reference vs quick tutorial
4. **Better Accessibility**: Free vs paywalled
5. **Higher Quality Score**: 20+ point improvement in overall score

---

## Gap Analysis

### Current Gaps

**Missing Source Types**:
1. [Gap 1]: [Description]
2. [Gap 2]: [Description]

**Coverage Gaps**:
1. [Topic 1]: No authoritative source available
2. [Topic 2]: Only community sources available

**Proposed Additions**:
1. [Source Name]: [URL] - [Why needed]
2. [Source Name]: [URL] - [Why needed]

---

## Example: Security Domain (Filled Template)

**Domain**: Security
**Maintainer**: Claude Agent System
**Last Updated**: 2026-02-06

### Primary Sources (TIER_1)

#### 1. OWASP (Open Web Application Security Project)

- **URL**: https://owasp.org
- **Type**: Standard / Best Practices
- **Coverage**: Web application security, OWASP Top 10, testing guides
- **Update Frequency**: Monthly
- **Last Verified**: 2026-02-06
- **Quality Score**: 0.95 / 1.0
- **Use Cases**:
  - Security testing methodology reference
  - Vulnerability classification
  - Security standards compliance

#### 2. NVD (National Vulnerability Database)

- **URL**: https://nvd.nist.gov
- **Type**: Official Database
- **Coverage**: CVE database, vulnerability scoring, patches
- **Update Frequency**: Daily
- **Last Verified**: 2026-02-06
- **Quality Score**: 1.0 / 1.0
- **Use Cases**:
  - CVE lookup and verification
  - Vulnerability impact assessment
  - Patch tracking

### Secondary Sources (TIER_2)

#### 1. HackerOne Platform

- **URL**: https://hackerone.com
- **Type**: Bug Bounty Platform
- **Coverage**: Vulnerability disclosures, security reports
- **Update Frequency**: Daily
- **Last Verified**: 2026-02-06
- **Quality Score**: 0.85 / 1.0
- **Use Cases**:
  - Real-world vulnerability examples
  - Bug bounty program management
  - Security researcher collaboration

---

**Template Version**: 1.0
**Last Updated**: 2026-02-06
