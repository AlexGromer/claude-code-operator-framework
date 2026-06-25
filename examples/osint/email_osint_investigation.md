# Example: Email OSINT Investigation

## User Request

```
Найди информацию о человеке по email: target@example.com
```

## Reasoning

**Domain:** OSINT (email reconnaissance)
**Complexity:** Simple
**Model:** Haiku

## Response

### Email OSINT Workflow

```bash
# 1. Email validation & syntax check
python3 -c "import re; print(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', 'target@example.com'))"

# 2. Holehe - check account presence on 120+ sites
holehe target@example.com --only-used

# Output: Account found on:
# - GitHub
# - Twitter
# - LinkedIn
# - Adobe

# 3. Email reputation check
curl -s "https://emailrep.io/target@example.com" | jq

# 4. Breach check (HaveIBeenPwned API)
curl -s "https://haveibeenpwned.com/api/v3/breachedaccount/target@example.com" \
  -H "hibp-api-key: YOUR_KEY" | jq

# 5. Google dorking
google-search "target@example.com" site:github.com
google-search "target@example.com" site:pastebin.com

# 6. Sherlock - username enumeration (if username extracted)
sherlock target_username

# 7. theHarvester - gather emails from domain
theHarvester -d example.com -b google,bing,linkedin
```

### Findings Template

```markdown
## Email OSINT Report: target@example.com

**Date:** 2026-01-27
**Analyst:** [Name]

### Summary
- Email valid: ✅
- Accounts found: 4 platforms
- Breaches: 2 incidents
- Public profiles: GitHub, LinkedIn

### Platform Presence
| Platform | Status | Profile URL |
|----------|--------|-------------|
| GitHub | ✅ Found | github.com/target |
| LinkedIn | ✅ Found | linkedin.com/in/target |
| Twitter | ✅ Found | twitter.com/target |
| Adobe | ✅ Found | — |

### Breach History
- **2019-03** — Collection #1 (773M emails)
- **2021-07** — LinkedIn (700M users)

### Public Information
- Name: John Doe
- Location: San Francisco, CA
- Occupation: Software Engineer
- Skills: Python, DevOps, Kubernetes

### Recommendations
- User should enable 2FA on all accounts
- Change passwords for breached services
- Monitor dark web for credential sales
```

---

## Key Takeaways

1. **holehe** — fastest way to find account presence (120+ sites)
2. **HaveIBeenPwned** — check breach history
3. **Google dorking** — find public mentions
4. **theHarvester** — domain-wide email enumeration
5. **Always document** — structured report for findings

**Legal:** OSINT must be for authorized purposes only (security research, investigations)
**Ethics:** Don't use for stalking, harassment, or unauthorized access
