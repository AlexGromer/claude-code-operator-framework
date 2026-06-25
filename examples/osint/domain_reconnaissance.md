# Example: Domain Reconnaissance

## User Request

```
Собери максимум информации о домене target.com для пентеста.
```

## Reasoning

**Domain:** OSINT (domain recon)
**Complexity:** Simple
**Model:** Haiku

## Response

### Domain Recon Workflow

```bash
# 1. WHOIS lookup
whois target.com

# 2. DNS enumeration
dig target.com ANY
dig target.com MX
dig target.com TXT

# 3. Subdomain discovery
subfinder -d target.com -o subdomains.txt
amass enum -d target.com -o amass_results.txt

# 4. Certificate Transparency logs
curl -s "https://crt.sh/?q=%.target.com&output=json" | jq

# 5. Shodan search
shodan search hostname:target.com --fields ip_str,port,org,os

# 6. theHarvester - emails & subdomains
theHarvester -d target.com -b all -l 500

# 7. Wayback Machine snapshots
curl -s "http://web.archive.org/cdx/search/cdx?url=target.com/*&output=json" | jq

# 8. Google dorking
site:target.com filetype:pdf
site:target.com inurl:admin
site:target.com ext:sql | ext:env

# 9. GitHub code search
github-search "target.com" --type=code

# 10. Nuclei - tech stack detection
nuclei -u https://target.com -tags tech
```

### Recon Report Template

```markdown
## Domain Recon: target.com

### Infrastructure
- **IP:** 203.0.113.10
- **Hosting:** AWS (us-east-1)
- **CDN:** Cloudflare
- **MX:** Google Workspace

### Subdomains (42 found)
- api.target.com
- staging.target.com
- admin.target.com ⚠️ (potential entry point)
- dev.target.com

### Technologies Detected
- Web Server: nginx/1.21.6
- Framework: Next.js 14
- Database: PostgreSQL (inferred from job postings)
- Auth: Auth0

### Exposed Information
- 15 employee emails (from LinkedIn, GitHub)
- 3 leaked API keys (GitHub commits) ⚠️
- Old admin panel at /wp-admin (404 now)

### Attack Surface
- 12 open ports (80, 443, 22, 3306, ...)
- Outdated nginx version (CVE-2021-23017)
- Staging environment publicly accessible ⚠️

### Recommendations
- Restrict staging.target.com to VPN
- Rotate leaked API keys immediately
- Update nginx to latest version
- Implement rate limiting on admin.target.com
```

---

## Key Takeaways

1. **subfinder + amass** — comprehensive subdomain discovery
2. **crt.sh** — Certificate Transparency logs reveal subdomains
3. **Shodan** — find exposed services and versions
4. **GitHub search** — often contains credentials, configs
5. **Wayback Machine** — historical data, old endpoints

**Timeline:** Full recon takes 2-4 hours for medium domain
**Tools:** subfinder, amass, Shodan, theHarvester, nuclei
