# Module 01: Compliance — Russian Standards Reference

## Quick Reference: When to Apply What

| Data Type | Russian Standard | EU | Controls |
|-----------|------------------|----|----------|
| Russian citizens' PII | ФЗ-152 + Приказ №21 | GDPR | Consent, localization, encryption |
| Financial operations | ГОСТ Р 57580 | DORA/PCI DSS | Security levels, audit trails |
| Critical infrastructure | ФЗ-187 + Приказ №239 | NIS2 | КИИ category, incident reporting |
| Government systems | Приказ №17 | — | ГИС classification, ФСТЭК controls |
| ISMS enterprise | ГОСТ Р ИСО/МЭК 27001 | ISO 27001 | Risk-based controls |
| AI/ML (PII in training) | ФЗ-152 + ГОСТ Р 59276 | AI Act | Localization, transparency, bias testing |

---

## ФЗ-152 (О персональных данных)

**Applies when:** any processing of Russian citizens' personal data.

| Requirement | Key Points |
|-------------|------------|
| **Consent** | Explicit written or electronic consent; purpose must be specified |
| **Purpose limitation** | Processing only for declared purposes; re-use requires new consent |
| **Data localization** | Primary storage of Russian citizens' PII — in Russia (see below) |
| **Security measures** | Technical + organizational; class determined by Приказ №21 |
| **Breach notification** | Notify Роскомнадзор within 24h (fact) + 72h (circumstances); data subjects if high risk |
| **Data subject rights** | Access, rectification, erasure, restriction — response within 30 days |
| **Operator registration** | Register with Роскомнадзор before processing begins |

### Data Localization (ст. 18.1 ФЗ-152)

- **Rule:** First recording of Russian citizens' PII must occur on servers in Russia.
- **Backups:** Must also be in Russia if they contain PII.
- **CDN/Cache:** Any PII cache must be on Russian nodes.
- **Cross-border transfer** allowed after localization requirement is met, with adequate protection.
- **Роскомнадзор** can block violators (RKN enforcement via reestr.rkn.gov.ru).

**Localization checklist:**
- Identify all Russian PII data flows (collected → stored → processed → transferred)
- Primary DB in Russian DC (DataLine, Selectel, IXcellerate, Linxdatacenter)
- Backups in Russia; CDN configured for Russian nodes
- Cloud contracts include data residency clause (RU region)
- Log PII access with geography; monitor cross-border transfers

### Cross-Border Data Transfer (Russia)

- Transfer permitted only after localization is fulfilled
- Receiving country must ensure adequate protection (or use contractual safeguards)
- Роскомнадзор notification required for systematic transfers to "non-adequate" countries
- Special categories (биометрия, health, political views) — heightened restrictions

---

## ФСТЭК Приказы

| Приказ | Scope | Classes/Levels | Key |
|--------|-------|----------------|-----|
| **№17** | ГИС (government IS) | К1 (federal) / К2 (regional) / К3 (municipal) | Classify → threat model → controls → ФСТЭК certification |
| **№21** | ПДн technical controls (ФЗ-152) | УЗ-1 (biometrics/health) / УЗ-2 (>100k) / УЗ-3 (<100k) / УЗ-4 (basic) | УЗ-1/2: mandatory access control + logging + encryption |
| **№31** | АСУ ТП / SCADA / ICS | Classes 1-3 (critical→low) | Availability > confidentiality; air-gap at Class 1 |
| **№239** | КИИ subjects (ФЗ-187) | Category 1 (national) / 2 (regional) / 3 (object) | Identify → categorize → controls → notify ФСТЭК/ФСБ |

---

## ФЗ-187 (О безопасности КИИ)

**Applies when:** organization operates КИИ (energy, transport, finance, health, telecom, defense, nuclear, mining, rocket/space).

Key obligations:
- **Categorization** of КИИ objects (Приказ №239)
- **GosSOPKA connection** — mandatory incident reporting to ФСБ/НКЦКИ
- **Incident notification** within 3 hours (Category 1) / 24 hours (Category 2-3)
- **Interaction** with ФСБ on threat intelligence

---

## ГОСТ Р 57580 (Финансовый сектор)

**Applies when:** banking, payments, fintech, insurance, exchanges under надзор Банка России.

| Security Level | Applies To |
|----------------|------------|
| Стандартный (3) | Most financial orgs |
| Усиленный (2) | Systemically important banks, NPS participants |
| Минимальный (4) | Limited-scope entities |

Key domains: access management, protection from malware, incident management, application security, infrastructure, logging, cryptography. Annual compliance assessment (ГОСТ Р 57580.2).

---

## Russian AI Compliance

**Applies when:** AI/ML system processes Russian PII or used in government/critical infrastructure.

| Requirement | Source | Key Point |
|-------------|--------|-----------|
| PII localization | ФЗ-152 | Training data with Russian PII → must be stored in Russia |
| КИИ certification | ФЗ-187 + Приказ №239 | AI in critical infra → categorize, secure, report |
| AI safety standard | ГОСТ Р 59276 | Risk assessment, testing documentation, human oversight |
| Automated decisions | ФЗ-152 ст. 16 | Right to human review for decisions affecting rights |
| Government procurement | PP-1236 + Реестр ПО | Prefer Russian-registry AI tools; justify foreign software |
| Draft AI Law | Pending | Transparency, accountability (monitor for adoption) |

**Russian LLMs for localization-safe use:** GigaChat (SberCloud), YaLM (Yandex Cloud) — both on Russian infrastructure, simplify ФЗ-152 compliance.

---

## Routing: Standard Detection Logic

```
Personal data of Russian citizens  → ФЗ-152 + Приказ №21
Financial org (Russia)             → ГОСТ Р 57580 + ФЗ-152
Government system                  → Приказ №17 + ФЗ-152
Critical infrastructure            → ФЗ-187 + Приказ №239 + Приказ №31 (if АСУ ТП)
Cross-border transfer (from RU)    → ФЗ-152 localization first, then transfer rules
AI with Russian PII                → ФЗ-152 + ГОСТ Р 59276
Government IT procurement          → 44-ФЗ + PP-1236 (import substitution)
State corp procurement             → 223-ФЗ
```

**Examples:** `~/.claude/examples/compliance/fz152_compliance.md`, `fz152_russia_compliance.md`
