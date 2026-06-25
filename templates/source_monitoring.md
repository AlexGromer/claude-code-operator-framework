# Source Monitoring Schedule (GAP-SRC-005)

**Purpose**: Define monitoring frequency and staleness criteria per source tier

---

## Monitoring Frequency by Tier

| Tier | Frequency | Max Age | Staleness Threshold | Action on Stale |
|------|-----------|---------|---------------------|-----------------|
| **TIER_1** | Monthly | 6 months | 12 months | Review + update or demote |
| **TIER_2** | Quarterly | 9 months | 18 months | Review + update or demote |
| **TIER_3** | Semi-annual | 12 months | 24 months | Review + update or remove |
| **TIER_4** | Annual | 18 months | 36 months | Review + promote or remove |

### Definitions

**Monitoring Frequency**: How often to check source for updates/changes
**Max Age**: Maximum time before source should be re-verified
**Staleness Threshold**: Age at which source is considered stale
**Action on Stale**: What to do when source exceeds staleness threshold

---

## Staleness Detection Criteria

### Primary Indicators

1. **Last Verified Date**
   - Source has not been verified within monitoring frequency
   - Example: TIER_1 source not verified in 2+ months

2. **Content Age**
   - Content references outdated versions/technologies
   - Example: Documentation for Python 2.x (EOL 2020)

3. **Broken Links**
   - 404 errors or domain expiration
   - Redirects to unrelated content

4. **Deprecated Information**
   - Information marked as deprecated/obsolete
   - Superseded by newer official documentation

### Secondary Indicators

5. **Update Frequency Drop**
   - Previously active source shows no updates for extended period
   - Example: Blog with monthly posts, now 12+ months silent

6. **Community Feedback**
   - Users report outdated/incorrect information
   - Source cited in "bad practices" lists

7. **Tier Mismatch**
   - Source quality degraded below tier expectations
   - Example: TIER_1 source now contains ads/spam

---

## Monitoring Actions

### Monthly Review (TIER_1)

**Automated Checks:**
- [ ] URL accessibility (HTTP 200 check)
- [ ] Domain SSL certificate validity
- [ ] Last-modified header (if available)

**Manual Review (if stale indicators found):**
- [ ] Content accuracy verification
- [ ] Version currency check
- [ ] Cross-reference with official docs

**Actions:**
- ✅ **CURRENT**: Update last_verified timestamp
- ⚠️ **OUTDATED**: Flag for review, update content
- ❌ **STALE**: Demote to TIER_2 or remove

### Quarterly Review (TIER_2)

**Automated Checks:**
- [ ] URL accessibility
- [ ] Domain reputation check

**Manual Review (every 6 months):**
- [ ] Content relevance check
- [ ] Compare with competing sources

**Actions:**
- ✅ **CURRENT**: Update last_verified timestamp
- ↗️ **IMPROVED**: Promote to TIER_1 if quality increased
- ↘️ **DEGRADED**: Demote to TIER_3
- ❌ **STALE**: Remove from registry

### Semi-Annual Review (TIER_3)

**Automated Checks:**
- [ ] URL accessibility

**Manual Review (annual):**
- [ ] Verify community still active
- [ ] Check for misinformation

**Actions:**
- ✅ **CURRENT**: Update last_verified timestamp
- ↗️ **ESTABLISHED**: Promote to TIER_2 if consistently good
- ❌ **STALE/DEAD**: Remove from registry

### Annual Review (TIER_4)

**Automated Checks:**
- [ ] URL accessibility

**Manual Review:**
- [ ] Assess if source earned promotion
- [ ] Verify no malicious content

**Actions:**
- ↗️ **PROMOTE**: Move to appropriate tier after assessment
- ❌ **REMOVE**: Delete if still unverified/low-quality

---

## Implementation

### Anacron Integration

```bash
# ~/.anacron/anacrontab

# Source monitoring (TIER_1: monthly)
30  15  source_monitor_tier1  cd ~/.claude && python tools/source_monitor.py --tier TIER_1

# Source monitoring (TIER_2: quarterly = 90 days)
90  20  source_monitor_tier2  cd ~/.claude && python tools/source_monitor.py --tier TIER_2

# Source monitoring (TIER_3: semi-annual = 180 days)
180 25  source_monitor_tier3  cd ~/.claude && python tools/source_monitor.py --tier TIER_3

# Source monitoring (TIER_4: annual = 365 days)
365 30  source_monitor_tier4  cd ~/.claude && python tools/source_monitor.py --tier TIER_4
```

### Tool Integration

**source_monitor.py** (to be created):
- Load sources by tier
- Check last_verified dates
- Run automated checks (URL accessibility, SSL)
- Generate staleness report
- Flag sources for manual review

**Cross-Reference with:**
- `source_quality_assessor.py` - Re-assess quality scores
- `source_registry.py` - Update verification status
- `staleness_checker.py` - Domain lifecycle checks

---

## Staleness Report Format

```json
{
  "report_date": "2026-02-06T12:00:00",
  "tier": "TIER_1",
  "total_sources": 50,
  "stale_sources": [
    {
      "url": "https://example.com/docs",
      "last_verified": "2024-12-01",
      "days_since_verified": 67,
      "staleness_reason": "Exceeded 30-day monitoring frequency",
      "recommended_action": "Review + update or demote"
    }
  ],
  "broken_sources": [
    {
      "url": "https://dead-site.com",
      "error": "404 Not Found",
      "recommended_action": "Remove from registry"
    }
  ],
  "summary": {
    "current": 45,
    "needs_review": 3,
    "broken": 2
  }
}
```

---

## Manual Review Checklist

When flagged source requires manual review:

- [ ] **Accessibility**: Can the source still be accessed?
- [ ] **Content Currency**: Is the content up-to-date?
- [ ] **Accuracy**: Is the information still correct?
- [ ] **Relevance**: Is the source still relevant to domain?
- [ ] **Quality**: Has quality increased or decreased?
- [ ] **Authority**: Has authority status changed?
- [ ] **Alternatives**: Are there better alternatives available?

**Decision:**
- [ ] **KEEP**: Update last_verified, keep current tier
- [ ] **UPDATE**: Update source metadata (description, tags, etc.)
- [ ] **PROMOTE**: Increase tier (quality improved)
- [ ] **DEMOTE**: Decrease tier (quality degraded)
- [ ] **REMOVE**: Delete from registry (stale, broken, or superseded)

---

## Escalation Criteria

**Immediate Review Required:**
- Security advisory about source domain
- Community reports of malicious content
- Source acquired by different organization
- Breaking changes in API/documentation structure
- Source becomes paywalled (was free)

**Priority Review (within 1 week):**
- Multiple broken links reported
- Source tier disputed by users
- Competing source identified as superior
- Source referenced in critical decision/code

---

**Version**: 1.0
**Last Updated**: 2026-02-06
**Related**: GAP-SRC-005, source_registry.py, staleness_checker.py
