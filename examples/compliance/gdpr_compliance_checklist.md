# Example: GDPR Compliance Implementation

## User Request

```
Нужен чеклист для GDPR compliance нашего SaaS-приложения.
```

## Reasoning

**Domain:** Compliance (GDPR)
**Complexity:** Medium
**Model:** Sonnet

## Response

### GDPR Compliance Checklist

#### 1. Lawful Basis for Processing (Art. 6)

```markdown
☐ Identify lawful basis for each data processing activity:
  ☐ Consent (explicit, freely given, withdrawable)
  ☐ Contract (necessary for service delivery)
  ☐ Legal obligation
  ☐ Vital interests
  ☐ Public task
  ☐ Legitimate interests (balance test required)

☐ Document lawful basis in data processing register
☐ Implement consent management system (if using consent)
☐ Provide withdrawal mechanism (easy as giving consent)
```

#### 2. Data Subject Rights (Art. 12-23)

```python
# Example: Right to Access implementation
from flask import Flask, request, jsonify

@app.route('/api/gdpr/data-access', methods=['POST'])
def data_access_request():
    """
    Art. 15: Right of Access
    User can request copy of their personal data.
    """
    user_email = request.json.get('email')

    # Verify identity (2FA recommended)
    if not verify_identity(user_email):
        return jsonify({'error': 'Identity verification failed'}), 403

    # Gather all personal data (must respond within 30 days)
    user_data = {
        'profile': get_user_profile(user_email),
        'activities': get_user_activities(user_email),
        'preferences': get_user_preferences(user_email),
        'processing_purposes': get_processing_purposes(),
        'data_recipients': get_data_recipients(),
        'retention_periods': get_retention_periods()
    }

    # Generate report (machine-readable format)
    report = generate_gdpr_report(user_data)

    # Log request (audit trail)
    log_gdpr_request('access', user_email)

    return send_file(report, as_attachment=True)

# Right to Erasure ("Right to be Forgotten")
@app.route('/api/gdpr/delete', methods=['POST'])
def data_deletion_request():
    """Art. 16: Right to Erasure"""
    user_email = request.json.get('email')

    # Check if deletion is possible (exceptions: legal obligations, etc.)
    if not can_delete_user(user_email):
        return jsonify({
            'error': 'Deletion not possible',
            'reason': 'Legal retention requirement (6 years for invoices)'
        }), 400

    # Anonymize/delete data
    anonymize_user_data(user_email)

    # Notify third parties (if data was disclosed)
    notify_data_recipients_of_deletion(user_email)

    log_gdpr_request('deletion', user_email)

    return jsonify({'status': 'deleted', 'timestamp': datetime.utcnow()})
```

#### 3. Privacy by Design & Default (Art. 25)

```markdown
☐ Data minimization implemented
  ☐ Collect only necessary fields
  ☐ Remove optional fields from forms
  ☐ Auto-delete after retention period

☐ Pseudonymization/encryption implemented
  ☐ User IDs hashed
  ☐ Database encryption at rest
  ☐ TLS for data in transit

☐ Default privacy settings
  ☐ Marketing emails: opt-in (not pre-checked)
  ☐ Analytics: anonymized by default
  ☐ Data sharing: opt-in
```

#### 4. Data Protection Impact Assessment (Art. 35)

```markdown
☐ DPIA required for:
  ☐ Large-scale processing of sensitive data
  ☐ Systematic monitoring (tracking, profiling)
  ☐ Automated decision-making

☐ DPIA components:
  ☐ Processing description
  ☐ Necessity assessment
  ☐ Risk identification (likelihood × severity)
  ☐ Mitigation measures
  ☐ DPO consultation (if applicable)
```

#### 5. Data Breach Notification (Art. 33-34)

```python
# Incident response automation
def handle_data_breach(breach_details):
    """
    Art. 33: 72-hour notification requirement
    """
    severity = assess_breach_severity(breach_details)

    if severity >= 'high':
        # Notify supervisory authority within 72 hours
        notify_dpa(breach_details, deadline=72)  # hours

    if severity == 'critical':
        # Notify affected individuals without undue delay
        notify_affected_users(breach_details)

    # Document breach (required even if not notifying)
    log_breach_incident(breach_details)
```

#### 6. Vendor Management (Art. 28)

```markdown
☐ Data Processing Agreements (DPAs) with all vendors
☐ Verify vendor GDPR compliance
☐ Document data flows (who receives what data)
☐ Vendor audit rights in contracts
☐ Subprocessor notification mechanism
```

---

### GDPR Compliance Status Dashboard

```python
# Example: Compliance monitoring
def gdpr_compliance_score():
    checks = {
        'lawful_basis_documented': check_lawful_basis(),
        'consent_mechanism': check_consent_system(),
        'data_access_endpoint': check_endpoint('/api/gdpr/data-access'),
        'deletion_endpoint': check_endpoint('/api/gdpr/delete'),
        'privacy_policy_updated': check_privacy_policy_date(),
        'dpo_appointed': check_dpo(),
        'dpia_completed': check_dpia(),
        'vendor_dpas_signed': check_vendor_contracts(),
        'breach_procedure': check_breach_response_plan(),
        'staff_training': check_training_completion()
    }

    score = sum(checks.values()) / len(checks) * 100
    return {
        'score': score,
        'checks': checks,
        'status': 'compliant' if score >= 90 else 'non-compliant'
    }
```

---

## Key Takeaways

1. **30-day deadline** for data access requests
2. **72-hour deadline** for breach notification to DPA
3. **Explicit consent** required (pre-checked boxes invalid)
4. **Data minimization** — collect only what's necessary
5. **Vendor DPAs** mandatory for all data processors

**Penalties:** Up to €20M or 4% of global revenue (whichever higher)
**DPO:** Required if large-scale processing or sensitive data
**Documentation:** Maintain data processing register + DPIAs
