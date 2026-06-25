# Example: Social Media Footprint Analysis

## User Request

```
Проанализируй digital footprint человека по username "johndoe123".
```

## Reasoning

**Domain:** OSINT (social media investigation)
**Complexity:** Simple
**Model:** Haiku

## Response

### Social Media OSINT Workflow

```bash
# 1. Sherlock - check username across 400+ sites
sherlock johndoe123 --timeout 10 --print-found

# 2. WhatsMyName - alternative username checker
./whatsmyname.py -u johndoe123

# 3. Maigret - comprehensive username search
maigret johndoe123 --timeout 30

# 4. Social-Analyzer - detailed profile analysis
social-analyzer --username johndoe123 --metadata

# 5. Twitter/X OSINT
twint -u johndoe123 --since 2023-01-01 -o tweets.csv

# 6. Instagram OSINT (if public)
instaloader profile johndoe123

# 7. LinkedIn enumeration
linkedin2username target-company > employees.txt
grep -i "john" employees.txt

# 8. Metadata extraction from social posts
exiftool downloaded_images/*.jpg | grep -i "gps\|location\|camera"

# 9. TinEye reverse image search
curl -s "https://tineye.com/search?url=https://profile-image-url.jpg"

# 10. Timeline reconstruction
python timeline_tool.py --username johndoe123 --platforms twitter,instagram,github
```

### OSINT Findings Template

```markdown
## Social Media Footprint: johndoe123

### Platform Presence (8 found)
| Platform | Profile | Last Activity | Followers |
|----------|---------|---------------|-----------|
| Twitter | @johndoe123 | 2 days ago | 1.2K |
| GitHub | github.com/johndoe123 | 1 week ago | 345 |
| LinkedIn | linkedin.com/in/johndoe123 | Active | 500+ |
| Instagram | @johndoe123 | 1 month ago | 892 |
| Reddit | u/johndoe123 | 5 days ago | 45 karma |

### Personal Information Disclosed
- **Full Name:** John Doe
- **Location:** San Francisco Bay Area
- **Occupation:** Senior DevOps Engineer @ TechCorp
- **Education:** Stanford University (2015)
- **Skills:** Kubernetes, Python, Terraform
- **Phone:** +1-555-0123 (from old tweet)
- **Email:** john.doe@techcorp.com (from GitHub commits)

### Behavioral Patterns
- Active hours: 9 AM - 6 PM PST (work hours)
- Tweet frequency: 5-10/day (professional content)
- Topics: Cloud computing, DevOps, open-source
- Sentiment: Positive, professional tone

### Security Concerns
- ⚠️ Phone number exposed in 2022 tweet
- ⚠️ Home address visible in Instagram photo metadata (GPS)
- ⚠️ Work schedule predictable (always posts 9 AM - 6 PM)
- ✅ No password/credential leaks found

### Timeline of Activities
- **2015-2019:** College student (Stanford mentions)
- **2019-2022:** Junior engineer (frequent tech tweets)
- **2022-present:** Senior role (leadership content)

### Recommendations
- Remove tweet with phone number
- Disable GPS on phone camera
- Review privacy settings on all platforms
- Use different usernames for personal vs professional
```

---

## Key Takeaways

1. **sherlock/maigret** — find accounts across 400+ platforms
2. **Metadata extraction** — images often contain GPS coordinates
3. **Timeline analysis** — reconstruct digital history
4. **Cross-reference** — correlate data across platforms
5. **Privacy audit** — identify exposed PII

**Legal:** OSINT for authorized purposes only (investigations, security research)
**Ethics:** Respect privacy, don't use for stalking/harassment
**Tools:** sherlock, maigret, twint, exiftool, instaloader
