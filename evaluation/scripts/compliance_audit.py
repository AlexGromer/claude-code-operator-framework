#!/usr/bin/env python3
"""
Compliance Audit Script for Anacron
OWASP LLM02 Automation: Periodic GDPR/ФЗ-152 compliance checks

Version: 1.0.0
Task: Tasks 20-28 Automation (Task 25 - LLM02)

Usage:
    python compliance_audit.py --weekly    # Weekly compliance audit
    python compliance_audit.py --monthly   # Monthly comprehensive audit
"""

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional


class ComplianceAuditor:
    """
    Automated compliance auditing for GDPR/ФЗ-152 requirements.

    Checks:
    1. PII detection in logs/data files
    2. Data retention compliance
    3. Access control verification
    4. Encryption status
    5. Audit trail completeness
    """

    def __init__(self):
        self.data_dir = Path.home() / ".claude" / "evaluation" / "data"
        self.reports_dir = self.data_dir / "reports"
        self.audit_log = Path.home() / ".claude" / "security_audit.log"

        # Ensure directories exist
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # PII patterns (simplified regex)
        self.pii_patterns = {
            "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "phone_ru": r"\+7\d{10}|\b8\d{10}\b",
            "inn": r"\b\d{10,12}\b",  # Russian INN
            "snils": r"\b\d{3}-\d{3}-\d{3}\s?\d{2}\b",  # Russian SNILS
            "passport_ru": r"\b\d{2}\s?\d{2}\s?\d{6}\b",  # Russian passport
            "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        }

    def run_audit(self, audit_type: str = "weekly") -> Dict[str, Any]:
        """Run compliance audit and generate report."""
        print(f"[COMPLIANCE AUDIT] Starting {audit_type} audit...")

        results = {
            "audit_type": audit_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {},
            "findings": [],
            "score": 0,
            "max_score": 0
        }

        # 1. Check data retention
        results["checks"]["data_retention"] = self._check_data_retention()
        results["max_score"] += 20

        # 2. Check for PII in logs
        results["checks"]["pii_in_logs"] = self._check_pii_in_logs()
        results["max_score"] += 30

        # 3. Check access controls
        results["checks"]["access_controls"] = self._check_access_controls()
        results["max_score"] += 20

        # 4. Check encryption
        results["checks"]["encryption"] = self._check_encryption()
        results["max_score"] += 15

        # 5. Check audit trail
        results["checks"]["audit_trail"] = self._check_audit_trail()
        results["max_score"] += 15

        # Calculate total score
        for check_name, check_result in results["checks"].items():
            if check_result.get("passed", False):
                results["score"] += check_result.get("points", 0)
            if check_result.get("findings"):
                results["findings"].extend(check_result["findings"])

        # Generate report
        report_path = self._generate_report(results, audit_type)
        results["report_path"] = str(report_path)

        # Log audit
        self._log_audit(results)

        print(f"[COMPLIANCE AUDIT] Complete. Score: {results['score']}/{results['max_score']}")
        print(f"[COMPLIANCE AUDIT] Report: {report_path}")

        return results

    def _check_data_retention(self) -> Dict[str, Any]:
        """Check data retention compliance (30 days for metrics)."""
        result = {
            "name": "Data Retention",
            "points": 20,
            "passed": True,
            "findings": [],
            "details": {}
        }

        metrics_dir = self.data_dir
        old_files = []

        if metrics_dir.exists():
            for f in metrics_dir.rglob("*.jsonl"):
                # Check if file is older than 30 days
                age_days = (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).days
                if age_days > 30:
                    old_files.append({"file": str(f), "age_days": age_days})

        if old_files:
            result["passed"] = False
            result["findings"].append({
                "severity": "MEDIUM",
                "description": f"Found {len(old_files)} files older than 30-day retention period",
                "files": old_files[:5]  # Limit to first 5
            })

        result["details"]["files_checked"] = len(list(metrics_dir.rglob("*.jsonl"))) if metrics_dir.exists() else 0
        result["details"]["old_files_count"] = len(old_files)

        return result

    def _check_pii_in_logs(self) -> Dict[str, Any]:
        """Check for PII in log files."""
        result = {
            "name": "PII in Logs",
            "points": 30,
            "passed": True,
            "findings": [],
            "details": {}
        }

        log_dirs = [
            self.data_dir,
            Path.home() / ".claude" / "logs"
        ]

        pii_found = []

        for log_dir in log_dirs:
            if not log_dir.exists():
                continue

            for log_file in log_dir.rglob("*.log"):
                try:
                    with open(log_file, 'r', errors='ignore') as f:
                        content = f.read()

                    # Simple check for obvious PII patterns
                    import re
                    for pii_type, pattern in self.pii_patterns.items():
                        matches = re.findall(pattern, content)
                        if matches and pii_type not in ["ip_address"]:  # IP in logs is often OK
                            pii_found.append({
                                "file": str(log_file),
                                "pii_type": pii_type,
                                "count": len(matches)
                            })
                except Exception:
                    pass

        if pii_found:
            result["passed"] = False
            result["findings"].append({
                "severity": "HIGH",
                "description": f"PII detected in {len(pii_found)} locations",
                "details": pii_found[:5]
            })

        result["details"]["pii_locations"] = len(pii_found)

        return result

    def _check_access_controls(self) -> Dict[str, Any]:
        """Check file access controls."""
        result = {
            "name": "Access Controls",
            "points": 20,
            "passed": True,
            "findings": [],
            "details": {}
        }

        sensitive_dirs = [
            Path.home() / ".claude",
            Path.home() / ".ssh",
            Path.home() / ".gnupg"
        ]

        for sensitive_dir in sensitive_dirs:
            if sensitive_dir.exists():
                stat = sensitive_dir.stat()
                mode = oct(stat.st_mode)[-3:]

                # Check if others have any access
                if int(mode[2]) > 0:
                    result["passed"] = False
                    result["findings"].append({
                        "severity": "HIGH",
                        "description": f"Directory {sensitive_dir} has world permissions: {mode}",
                        "recommendation": f"chmod 700 {sensitive_dir}"
                    })

        return result

    def _check_encryption(self) -> Dict[str, Any]:
        """Check encryption status of sensitive data."""
        result = {
            "name": "Encryption Status",
            "points": 15,
            "passed": True,
            "findings": [],
            "details": {}
        }

        # Check for unencrypted credential files
        home = Path.home()
        unencrypted = []

        credential_patterns = [
            home / ".claude" / "credentials*",
            home / ".claude" / "*.key",
            home / ".claude" / "*.pem"
        ]

        for pattern in credential_patterns:
            for f in home.glob(str(pattern).replace(str(home) + "/", "")):
                if f.exists() and not f.name.endswith('.gpg') and not f.name.endswith('.enc'):
                    unencrypted.append(str(f))

        if unencrypted:
            result["passed"] = False
            result["findings"].append({
                "severity": "MEDIUM",
                "description": f"Found {len(unencrypted)} potentially unencrypted credential files",
                "files": unencrypted
            })

        return result

    def _check_audit_trail(self) -> Dict[str, Any]:
        """Check audit trail completeness."""
        result = {
            "name": "Audit Trail",
            "points": 15,
            "passed": True,
            "findings": [],
            "details": {}
        }

        audit_log = self.audit_log

        if not audit_log.exists():
            result["passed"] = False
            result["findings"].append({
                "severity": "HIGH",
                "description": "Security audit log does not exist",
                "recommendation": "Ensure security_audit.log is being written"
            })
            return result

        # Check if audit log has recent entries
        stat = audit_log.stat()
        age_hours = (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).total_seconds() / 3600

        if age_hours > 24:
            result["findings"].append({
                "severity": "LOW",
                "description": f"Audit log not updated in {age_hours:.1f} hours"
            })

        result["details"]["log_size_bytes"] = stat.st_size
        result["details"]["last_modified_hours_ago"] = age_hours

        return result

    def _generate_report(self, results: Dict[str, Any], audit_type: str) -> Path:
        """Generate markdown compliance report."""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        report_file = self.reports_dir / f"compliance_{audit_type}_{timestamp}.md"

        score_pct = (results["score"] / results["max_score"]) * 100 if results["max_score"] > 0 else 0
        status = "PASS" if score_pct >= 80 else "NEEDS ATTENTION" if score_pct >= 60 else "FAIL"

        findings_by_severity = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for finding in results["findings"]:
            sev = finding.get("severity", "LOW")
            findings_by_severity[sev] = findings_by_severity.get(sev, 0) + 1

        report_content = f"""# Compliance Audit Report - {audit_type.title()}

**Date:** {timestamp}
**Status:** {status}
**Score:** {results['score']}/{results['max_score']} ({score_pct:.1f}%)

## Summary

| Severity | Count |
|----------|-------|
| HIGH | {findings_by_severity['HIGH']} |
| MEDIUM | {findings_by_severity['MEDIUM']} |
| LOW | {findings_by_severity['LOW']} |

## Check Results

| Check | Status | Points |
|-------|--------|--------|
"""
        for check_name, check_result in results["checks"].items():
            status_icon = "PASS" if check_result.get("passed", False) else "FAIL"
            points = check_result.get("points", 0) if check_result.get("passed", False) else 0
            report_content += f"| {check_result.get('name', check_name)} | {status_icon} | {points}/{check_result.get('points', 0)} |\n"

        report_content += """
## Findings

"""
        if results["findings"]:
            for i, finding in enumerate(results["findings"], 1):
                report_content += f"""### Finding {i}: [{finding.get('severity', 'LOW')}]

**Description:** {finding.get('description', 'N/A')}

"""
                if finding.get("recommendation"):
                    report_content += f"**Recommendation:** {finding['recommendation']}\n\n"
        else:
            report_content += "*No findings*\n"

        report_content += f"""
## Compliance Standards

- **GDPR**: Articles 5 (data minimization), 17 (right to erasure), 30 (records), 32 (security)
- **-152**: Articles 5, 19 (security measures)
- **OWASP LLM02**: Sensitive Information Disclosure protection

---
*Generated by compliance_audit.py v1.0.0*
*Timestamp: {datetime.now(timezone.utc).isoformat()}*
"""

        with open(report_file, 'w') as f:
            f.write(report_content)

        return report_file

    def _log_audit(self, results: Dict[str, Any]) -> None:
        """Log audit to security audit log."""
        with open(self.audit_log, 'a') as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] COMPLIANCE_AUDIT: "
                   f"{results['audit_type'].upper()} - Score: {results['score']}/{results['max_score']} - "
                   f"Findings: {len(results['findings'])}\n")


def main():
    parser = argparse.ArgumentParser(description="Compliance Audit Script")
    parser.add_argument("--weekly", action="store_true", help="Run weekly audit")
    parser.add_argument("--monthly", action="store_true", help="Run monthly audit")

    args = parser.parse_args()

    auditor = ComplianceAuditor()

    if args.monthly:
        auditor.run_audit("monthly")
    else:
        auditor.run_audit("weekly")


if __name__ == "__main__":
    main()
