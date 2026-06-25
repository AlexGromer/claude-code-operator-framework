#!/usr/bin/env python3
"""
MITRE ATLAS Threat Detector
Unified detection system for adversarial ML attacks

Version: 1.0.0
Task: TIER 2D Task 27 (GAP-RES-008)
OWASP: Complements LLM01, LLM02, LLM03

Techniques covered:
- AML.T0054: LLM Jailbreaking
- AML.T0051: Prompt Injection (Direct/Indirect)
- AML.T0043: Craft Adversarial Data
- AML.T0024: Exfiltration via ML Inference API
- AML.T0020: Poison Training Data

Usage:
    python atlas_threat_detector.py "text to analyze"
    python atlas_threat_detector.py --scan-logs
    echo "text" | python atlas_threat_detector.py
"""

import re
import sys
import json
import argparse
import unicodedata
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timezone
from pathlib import Path


class JailbreakCategory(Enum):
    ROLE_PLAYING = "role_playing"
    HYPOTHETICAL = "hypothetical"
    ENCODING = "encoding"
    MULTI_TURN = "multi_turn"
    PROMPT_EXTRACTION = "prompt_extraction"
    TYPOGLYCEMIA = "typoglycemia"


@dataclass
class JailbreakDetection:
    detected: bool
    category: str
    confidence: float
    matched_pattern: str
    risk_level: str


@dataclass
class ThreatDetection:
    technique_id: str
    technique_name: str
    tactic: str
    confidence: float
    risk_level: str
    details: Dict
    timestamp: str


class JailbreakDetector:
    """
    MITRE ATLAS AML.T0054 Jailbreak Detection
    """

    PATTERNS = {
        JailbreakCategory.ROLE_PLAYING: [
            (r"(?i)you\s+are\s+(now\s+)?(?:DAN|jailbroken|unrestricted)", 0.95),
            (r"(?i)pretend\s+(you('re|are)\s+)?an?\s+ai\s+without", 0.90),
            (r"(?i)roleplay\s+as\s+.*(evil|unrestricted|unfiltered)", 0.85),
            (r"(?i)ignore\s+(all\s+)?(previous\s+)?instructions", 0.95),
            (r"(?i)disregard\s+(your\s+)?(safety|ethical)\s+guidelines", 0.95),
            (r"(?i)act\s+as\s+if\s+you\s+have\s+no\s+(restrictions|limits)", 0.90),
            (r"(?i)you\s+are\s+OMEGA", 0.95),
            (r"(?i)uncensored\s+AI", 0.90),
            (r"(?i)without\s+any\s+safety\s+filters", 0.90),
            (r"(?i)my\s+life\s+depends\s+on", 0.85),
            (r"(?i)highest\s+rating\s+if\s+you", 0.80),
            (r"(?i)story\s+where\s+(the\s+)?AI\s+character", 0.80),
            # JB-012: Malicious code generation requests
            (r"(?i)script\s+(that|which|to)\s+.*(brute\s*force|attack|hack)", 0.90),
            (r"(?i)(brute\s*force|ddos|dos)\s+(attack\s+)?(on|against)", 0.90),
            (r"(?i)write\s+.*(malware|exploit|attack\s+script)", 0.95),
        ],
        JailbreakCategory.HYPOTHETICAL: [
            (r"(?i)for\s+(a\s+)?fictional\s+(story|scenario)", 0.70),
            (r"(?i)hypothetically\s+(speaking|,)", 0.65),
            (r"(?i)in\s+a\s+(parallel|alternate)\s+universe", 0.75),
            (r"(?i)imagine\s+you('re|are)\s+an?\s+ai\s+(that|which|who)", 0.80),
            (r"(?i)what\s+if\s+you\s+(had|were)\s+no\s+restrictions", 0.85),
            (r"(?i)grandmother\s+(used\s+to|told\s+me)", 0.85),
            (r"(?i)my\s+(grandmother|grandma).*harmful", 0.90),
            (r"(?i)for\s+my\s+(PhD|thesis|dissertation)", 0.80),
            (r"(?i)academic\s+(research|purposes?)\s+only", 0.75),
            (r"(?i)opposite\s+day", 0.85),
            (r"(?i)translate.*from.*(evil|forbidden)\s+language", 0.90),
            # JB-013: Obfuscated dangerous terms + educational excuse
            (r"(?i)b[o0]mb|expl[o0]sive|weap[o0]n", 0.90),
            (r"(?i)(make|create|build)\s+.*(bomb|explosive|weapon)", 0.95),
            (r"(?i)for\s+educational\s+purposes.*\)", 0.85),
            (r"(?i)\(for\s+educational\s+purposes\)", 0.90),
            # JB-020: Logic puzzle / variable manipulation
            (r"(?i)if\s+safety\s*=\s*(true|false)", 0.90),
            (r"(?i)set\s+safety\s*=\s*false", 0.95),
            (r"(?i)safety\s*=\s*false.*without\s+restrictions", 0.95),
        ],
        JailbreakCategory.ENCODING: [
            (r"(?i)decode\s+(this|the\s+following)\s*:", 0.80),
            (r"(?i)base64\s*:", 0.85),
            (r"(?i)translate\s+from\s+(base64|rot13|hex)", 0.85),
            (r"[A-Za-z0-9+/]{20,}={0,2}", 0.60),
            (r"(?i)\\u[0-9a-f]{4}", 0.70),
        ],
        JailbreakCategory.PROMPT_EXTRACTION: [
            (r"(?i)what\s+(are|were)\s+your\s+(initial|original)\s+instructions", 0.95),
            (r"(?i)repeat\s+(everything|all)\s+(above|before)", 0.90),
            (r"(?i)show\s+me\s+your\s+system\s+prompt", 0.95),
            (r"(?i)print\s+your\s+(instructions|prompt)", 0.90),
            (r"(?i)what\s+is\s+in\s+your\s+system\s+(message|prompt)", 0.90),
            (r"(?i)reveal\s+your\s+(hidden|secret)\s+instructions", 0.95),
            (r"(?i)print.*exact.*text.*system\s+prompt", 0.95),
            (r"(?i)summarize\s+your\s+instructions", 0.85),
            (r"(?i)include.*system\s+prompt\s+text", 0.90),
            (r"(?i)describe\s+your.*behavior\s+rules", 0.85),
        ],
        JailbreakCategory.TYPOGLYCEMIA: [
            (r"(?i)ig\.?nore|ign0re|1gnore|igonre", 0.80),
            (r"(?i)h\s*a\s*c\s*k|h.a.c.k", 0.75),
            (r"(?i)b\s*y\s*p\s*a\s*s\s*s", 0.75),
            (r"(?i)j\s*a\s*i\s*l\s*b\s*r\s*e\s*a\s*k", 0.85),
            (r"(?i)sfatey|gudielnes|prvioede|unrestricted\s*respnose", 0.85),
            (r"(?i)adn\s+|prvioede\s+|sfatey\s+", 0.80),
        ],
        JailbreakCategory.MULTI_TURN: [
            # JB-014: Multi-step attack patterns
            (r"(?i)step\s*1.*step\s*2.*step\s*3", 0.85),
            (r"(?i)step\s*\d+\s*:.*step\s*\d+\s*:", 0.80),
            (r"(?i)(first|then|finally).*combine.*chemicals", 0.90),
            (r"(?i)let's\s+discuss.*now\s+combine", 0.85),
            (r"(?i)chemistry.*combine.*what\s+happens", 0.90),
        ],
    }

    RISK_THRESHOLDS = {
        "CRITICAL": 0.90,
        "HIGH": 0.75,
        "MEDIUM": 0.50,
        "LOW": 0.30,
    }

    def __init__(self, custom_patterns: Dict = None):
        self.patterns = self.PATTERNS.copy()
        if custom_patterns:
            for category, patterns in custom_patterns.items():
                if category in self.patterns:
                    self.patterns[category].extend(patterns)

    def detect(self, text: str) -> List[JailbreakDetection]:
        detections = []
        for category, patterns in self.patterns.items():
            for pattern, weight in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    confidence = min(weight * len(matches), 1.0)
                    risk_level = self._calculate_risk_level(confidence)
                    detections.append(JailbreakDetection(
                        detected=True,
                        category=category.value,
                        confidence=confidence,
                        matched_pattern=pattern,
                        risk_level=risk_level
                    ))
        detections.sort(key=lambda x: x.confidence, reverse=True)
        return detections

    def _calculate_risk_level(self, confidence: float) -> str:
        for level, threshold in self.RISK_THRESHOLDS.items():
            if confidence >= threshold:
                return level
        return "LOW"

    def is_safe(self, text: str, threshold: float = 0.75) -> Tuple[bool, List]:
        detections = self.detect(text)
        high_risk = [d for d in detections if d.confidence >= threshold]
        return len(high_risk) == 0, detections

    def get_summary(self, text: str) -> Dict:
        detections = self.detect(text)
        if not detections:
            return {
                "status": "SAFE",
                "detections": 0,
                "max_confidence": 0.0,
                "categories": []
            }
        return {
            "status": "UNSAFE" if detections[0].confidence >= 0.75 else "SUSPICIOUS",
            "detections": len(detections),
            "max_confidence": detections[0].confidence,
            "max_risk_level": detections[0].risk_level,
            "categories": list(set(d.category for d in detections)),
            "details": [asdict(d) for d in detections[:5]]
        }


class DirectInjectionDetector:
    """
    MITRE ATLAS AML.T0051.000 Direct Prompt Injection Detection
    """

    INJECTION_PATTERNS = [
        (r"(?i)\[system\]|\[INST\]|<<SYS>>|<\|im_start\|>system", 0.95),
        (r"(?i)###\s*(system|instruction|assistant)", 0.90),
        (r"(?i)assistant:\s*I\s+will", 0.85),
        (r"(?i)human:\s*[^\"']+assistant:", 0.85),
        (r"(?i)new\s+instructions?\s*:", 0.90),
        (r"(?i)forget\s+(everything|all)\s+(above|previous)", 0.95),
        (r"(?i)from\s+now\s+on\s*,?\s*(you|ignore)", 0.85),
        (r"```\s*(system|instruction)", 0.80),
        (r"---+\s*(new|override|system)", 0.80),
    ]

    def detect(self, text: str) -> Dict:
        detections = []
        for pattern, confidence in self.INJECTION_PATTERNS:
            if re.search(pattern, text):
                detections.append({
                    "pattern": pattern,
                    "confidence": confidence,
                    "technique": "AML.T0051.000"
                })
        return {
            "detected": len(detections) > 0,
            "count": len(detections),
            "max_confidence": max((d["confidence"] for d in detections), default=0),
            "detections": detections
        }


class AdversarialDataDetector:
    """
    MITRE ATLAS AML.T0043 Adversarial Data Detection
    """

    HOMOGLYPHS = {
        'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x',
        'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O',
        'Р': 'P', 'С': 'C', 'Т': 'T', 'Х': 'X',
        'α': 'a', 'β': 'ß', 'ε': 'e', 'ι': 'i', 'κ': 'k', 'ν': 'v', 'ο': 'o',
        'ⅰ': 'i', 'ⅼ': 'l', 'ℓ': 'l', '∣': '|', '⁄': '/',
    }

    def detect_homoglyphs(self, text: str) -> Dict:
        suspicious_chars = []
        for i, char in enumerate(text):
            if char in self.HOMOGLYPHS:
                suspicious_chars.append({
                    "position": i,
                    "char": char,
                    "looks_like": self.HOMOGLYPHS[char],
                    "unicode_name": unicodedata.name(char, "UNKNOWN")
                })
        return {
            "detected": len(suspicious_chars) > 0,
            "count": len(suspicious_chars),
            "risk": "HIGH" if len(suspicious_chars) > 3 else "MEDIUM" if suspicious_chars else "LOW",
            "details": suspicious_chars[:10]
        }

    def detect_typoglycemia(self, text: str) -> Dict:
        spaced_pattern = r'\b\w(\s+\w){3,}\b'
        spaced_matches = re.findall(spaced_pattern, text)
        zero_width = ['\u200b', '\u200c', '\u200d', '\ufeff']
        zw_count = sum(text.count(zw) for zw in zero_width)
        return {
            "spaced_words": len(spaced_matches) > 0,
            "zero_width_chars": zw_count,
            "risk": "HIGH" if zw_count > 0 or spaced_matches else "LOW"
        }

    def detect_encoding_evasion(self, text: str) -> Dict:
        patterns = {
            "base64": r'(?:[A-Za-z0-9+/]{4}){5,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?',
            "hex": r'(?:0x[0-9a-fA-F]{2}){4,}|(?:\\x[0-9a-fA-F]{2}){4,}',
            "unicode_escape": r'(?:\\u[0-9a-fA-F]{4}){3,}',
            "rot13_marker": r'(?i)rot13|caesar\s*cipher',
        }
        findings = {}
        for name, pattern in patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                findings[name] = {"count": len(matches), "samples": matches[:3]}
        return {
            "detected": len(findings) > 0,
            "encodings": findings,
            "risk": "HIGH" if findings else "LOW"
        }

    def comprehensive_scan(self, text: str) -> Dict:
        homoglyphs = self.detect_homoglyphs(text)
        typo = self.detect_typoglycemia(text)
        encoding = self.detect_encoding_evasion(text)

        high_count = sum([
            homoglyphs["risk"] == "HIGH",
            typo["risk"] == "HIGH",
            encoding["risk"] == "HIGH"
        ])

        if high_count >= 2:
            overall_risk = "CRITICAL"
        elif high_count == 1:
            overall_risk = "HIGH"
        elif homoglyphs["detected"] or typo["zero_width_chars"]:
            overall_risk = "MEDIUM"
        else:
            overall_risk = "LOW"

        return {
            "homoglyphs": homoglyphs,
            "typoglycemia": typo,
            "encoding": encoding,
            "overall_risk": overall_risk
        }


class ExfiltrationDetector:
    """
    MITRE ATLAS AML.T0024 Exfiltration Detection
    """

    EXFILTRATION_PATTERNS = [
        (r"(?i)was\s+.+\s+in\s+your\s+training\s+data", "membership_inference"),
        (r"(?i)complete\s+(this|the)\s+(sentence|text)\s*:\s*.{0,20}(ssn|password|key|secret)", "data_extraction"),
        (r"(?i)what\s+(did|was)\s+.+\s+(email|message|document)\s+about", "data_extraction"),
        (r"(?i)what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions)", "prompt_extraction"),
        (r"(?i)show\s+me\s+your\s+(hidden|original)\s+instructions", "prompt_extraction"),
        (r"(?i)what\s+(is|are)\s+your\s+(model\s+)?(weights|parameters)", "parameter_extraction"),
        (r"(?i)how\s+many\s+(parameters|layers|neurons)", "architecture_probing"),
        (r"(?i)list\s+all\s+(users|emails|records|data)", "bulk_extraction"),
        (r"(?i)dump\s+(the\s+)?(database|contents|data)", "bulk_extraction"),
        (r"(?i)all\s+(email|phone)\s+(addresses|numbers)\s+you\s+know", "pii_extraction"),
        (r"(?i)(list|show|give|tell)\s+(me\s+)?all\s+(email|phone)", "pii_extraction"),
        (r"(?i)all\s+.*(email|phone).*you\s+know\s+about\s+users", "pii_extraction"),
        (r"(?i)all\s+previous\s+user\s+messages", "context_extraction"),
        (r"(?i)summarize\s+all\s+previous.*conversation", "context_extraction"),
        (r"(?i)list\s+all.*in\s+this\s+conversation", "context_extraction"),
    ]

    def detect(self, query: str) -> Dict:
        findings = []
        for pattern, attack_type in self.EXFILTRATION_PATTERNS:
            if re.search(pattern, query):
                findings.append({
                    "pattern": pattern,
                    "attack_type": attack_type,
                    "technique": "AML.T0024"
                })
        return {
            "detected": len(findings) > 0,
            "findings": findings,
            "risk": "HIGH" if findings else "LOW",
            "recommendation": "BLOCK" if findings else "ALLOW"
        }


class RAGSecurityValidator:
    """
    MITRE ATLAS AML.T0051.001 Indirect Injection Defense
    """

    DOCUMENT_POISONING_PATTERNS = [
        r"(?i)<!-- (ignore|system|instruction)",
        r"(?i)\[hidden\]|\[invisible\]",
        r"(?i)\\u200b",
        r"(?i)(ignore|forget|override)\s+(previous|above|all)\s+instructions?",
        r"(?i)new\s+task\s*:\s*",
        r"(?i)important\s+instruction\s*:",
        r"(?i)send\s+(this|the|all)\s+(to|via)\s+",
        r"(?i)forward\s+(all|this)\s+to\s+",
        r"(?i)email\s+(the|this)\s+(content|data|response)",
        r"(?i)\[HIDDEN:.*\]",
        r"(?i)priority:\s*OVERRIDE_SAFETY",
        r"(?i)See\s+document\s+['\"].*override",
        r"(?i)admin_override",
        r"(?i)http://.*steal-data|exfil",
        # RP-005: Cross-document injection patterns
        r"(?i)safety\s+(is\s+)?disabled",
        r"(?i)guardrails?\s+(are\s+)?disabled",
        r"(?i)\{system_prompt\}",
    ]

    def __init__(self):
        self.compiled_patterns = [re.compile(p) for p in self.DOCUMENT_POISONING_PATTERNS]

    def sanitize_document(self, content: str) -> Tuple[str, List[Dict]]:
        findings = []
        sanitized = content
        for i, pattern in enumerate(self.compiled_patterns):
            matches = pattern.findall(content)
            if matches:
                findings.append({
                    "pattern_id": i,
                    "pattern": self.DOCUMENT_POISONING_PATTERNS[i],
                    "matches": matches,
                    "count": len(matches)
                })
                sanitized = pattern.sub("[REDACTED]", sanitized)
        return sanitized, findings

    def validate_retrieval(self, query: str, retrieved_docs: List[str], threshold: float = 0.3) -> Dict:
        total_risk = 0
        doc_risks = []
        for i, doc in enumerate(retrieved_docs):
            doc_findings = []
            doc_risk = 0
            for pattern in self.compiled_patterns:
                if pattern.search(doc):
                    doc_risk += 0.2
                    doc_findings.append(pattern.pattern)
            doc_risks.append({
                "doc_index": i,
                "risk_score": min(doc_risk, 1.0),
                "findings": doc_findings
            })
            total_risk += doc_risk
        avg_risk = total_risk / len(retrieved_docs) if retrieved_docs else 0
        return {
            "safe": avg_risk < threshold,
            "average_risk": avg_risk,
            "high_risk_docs": [d for d in doc_risks if d["risk_score"] >= threshold],
            "recommendation": "BLOCK" if avg_risk >= 0.5 else "WARN" if avg_risk >= threshold else "ALLOW"
        }


class ATLASThreatDetector:
    """
    Unified MITRE ATLAS Threat Detection System
    """

    def __init__(self):
        self.jailbreak_detector = JailbreakDetector()
        self.injection_detector = DirectInjectionDetector()
        self.adversarial_detector = AdversarialDataDetector()
        self.exfiltration_detector = ExfiltrationDetector()
        self.rag_validator = RAGSecurityValidator()
        self.detection_log = []

    def analyze_input(self, text: str, context: Dict = None) -> Dict:
        timestamp = datetime.now(timezone.utc).isoformat()
        detections = []

        # AML.T0054 Jailbreaking
        jailbreak_result = self.jailbreak_detector.get_summary(text)
        if jailbreak_result["status"] != "SAFE":
            detections.append({
                "technique_id": "AML.T0054",
                "technique_name": "LLM Jailbreaking",
                "tactic": "Defense Evasion",
                "confidence": jailbreak_result["max_confidence"],
                "risk_level": jailbreak_result.get("max_risk_level", "MEDIUM"),
                "details": jailbreak_result
            })

        # AML.T0051.000 Direct Prompt Injection
        injection_result = self.injection_detector.detect(text)
        if injection_result["detected"]:
            detections.append({
                "technique_id": "AML.T0051.000",
                "technique_name": "Direct Prompt Injection",
                "tactic": "Initial Access",
                "confidence": injection_result["max_confidence"],
                "risk_level": "HIGH" if injection_result["max_confidence"] > 0.8 else "MEDIUM",
                "details": injection_result
            })

        # AML.T0043 Adversarial Data
        adversarial_result = self.adversarial_detector.comprehensive_scan(text)
        if adversarial_result["overall_risk"] in ["HIGH", "CRITICAL"]:
            detections.append({
                "technique_id": "AML.T0043",
                "technique_name": "Craft Adversarial Data",
                "tactic": "ML Attack Staging",
                "confidence": 0.85 if adversarial_result["overall_risk"] == "CRITICAL" else 0.70,
                "risk_level": adversarial_result["overall_risk"],
                "details": adversarial_result
            })

        # AML.T0024 Exfiltration Attempts
        exfil_result = self.exfiltration_detector.detect(text)
        if exfil_result["detected"]:
            detections.append({
                "technique_id": "AML.T0024",
                "technique_name": "Exfiltration via ML Inference API",
                "tactic": "Exfiltration",
                "confidence": 0.80,
                "risk_level": "HIGH",
                "details": exfil_result
            })

        # AML.T0051.001 RAG Poisoning / Indirect Injection (pattern-based)
        sanitized, rag_findings = self.rag_validator.sanitize_document(text)
        if rag_findings:
            detections.append({
                "technique_id": "AML.T0051.001",
                "technique_name": "Indirect Prompt Injection (RAG Poisoning)",
                "tactic": "Initial Access",
                "confidence": min(0.85 + 0.05 * len(rag_findings), 0.95),
                "risk_level": "HIGH" if len(rag_findings) >= 2 else "MEDIUM",
                "details": {"findings": rag_findings, "pattern_count": len(rag_findings)}
            })

        # Calculate overall risk
        if not detections:
            overall_risk = "LOW"
            recommendation = "ALLOW"
        else:
            max_confidence = max(d["confidence"] for d in detections)
            if max_confidence >= 0.9 or any(d["risk_level"] == "CRITICAL" for d in detections):
                overall_risk = "CRITICAL"
                recommendation = "BLOCK"
            elif max_confidence >= 0.75 or any(d["risk_level"] == "HIGH" for d in detections):
                overall_risk = "HIGH"
                recommendation = "BLOCK"
            elif max_confidence >= 0.5:
                overall_risk = "MEDIUM"
                recommendation = "WARN"
            else:
                overall_risk = "LOW"
                recommendation = "ALLOW"

        result = {
            "timestamp": timestamp,
            "input_length": len(text),
            "overall_risk": overall_risk,
            "recommendation": recommendation,
            "detection_count": len(detections),
            "detections": detections,
            "context": context or {}
        }

        if detections:
            self.detection_log.append(result)

        return result

    def analyze_rag_documents(self, query: str, documents: List[str]) -> Dict:
        validation = self.rag_validator.validate_retrieval(query, documents)
        return {
            "technique_id": "AML.T0051.001",
            "technique_name": "Indirect Prompt Injection",
            "tactic": "Initial Access",
            "safe": validation["safe"],
            "recommendation": validation["recommendation"],
            "high_risk_documents": validation["high_risk_docs"]
        }

    def get_detection_stats(self) -> Dict:
        if not self.detection_log:
            return {"total_detections": 0}
        technique_counts = {}
        risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for log in self.detection_log:
            for detection in log["detections"]:
                tid = detection["technique_id"]
                technique_counts[tid] = technique_counts.get(tid, 0) + 1
            risk_counts[log["overall_risk"]] += 1
        return {
            "total_detections": len(self.detection_log),
            "by_technique": technique_counts,
            "by_risk_level": risk_counts,
            "most_common": max(technique_counts.items(), key=lambda x: x[1])[0] if technique_counts else None
        }

    def export_to_siem(self, detection: Dict) -> str:
        """Export detection in SIEM-compatible format (CEF)."""
        cef_template = (
            "CEF:0|ATLAS|ThreatDetector|1.0|{technique_id}|{technique_name}|"
            "{severity}|src={input_hash} risk={risk} recommendation={recommendation}"
        )
        severity_map = {"CRITICAL": 10, "HIGH": 8, "MEDIUM": 5, "LOW": 2}
        return cef_template.format(
            technique_id=detection["detections"][0]["technique_id"] if detection["detections"] else "NONE",
            technique_name=detection["detections"][0]["technique_name"] if detection["detections"] else "None",
            severity=severity_map.get(detection["overall_risk"], 1),
            input_hash=hash(str(detection.get("context", ""))),
            risk=detection["overall_risk"],
            recommendation=detection["recommendation"]
        )


def scan_security_logs(log_dir: Path) -> Dict:
    """Scan security audit logs for threat patterns."""
    detector = ATLASThreatDetector()
    results = {
        "scanned_files": 0,
        "total_entries": 0,
        "threats_found": 0,
        "by_technique": {}
    }

    audit_log = log_dir / "security_audit.log"
    if audit_log.exists():
        results["scanned_files"] += 1
        with open(audit_log, 'r') as f:
            for line in f:
                results["total_entries"] += 1
                try:
                    entry = json.loads(line)
                    if "message" in entry:
                        analysis = detector.analyze_input(entry["message"])
                        if analysis["detection_count"] > 0:
                            results["threats_found"] += 1
                            for d in analysis["detections"]:
                                tid = d["technique_id"]
                                results["by_technique"][tid] = results["by_technique"].get(tid, 0) + 1
                except json.JSONDecodeError:
                    pass

    return results


def main():
    parser = argparse.ArgumentParser(description="MITRE ATLAS Threat Detector")
    parser.add_argument("text", nargs="?", help="Text to analyze")
    parser.add_argument("--scan-logs", action="store_true", help="Scan security logs")
    parser.add_argument("--output", type=Path, help="Output file for report")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    detector = ATLASThreatDetector()

    if args.scan_logs:
        log_dir = Path.home() / ".claude"
        results = scan_security_logs(log_dir)

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("[ATLAS SECURITY SCAN]")
            print(f"  Files scanned: {results['scanned_files']}")
            print(f"  Entries checked: {results['total_entries']}")
            print(f"  Threats found: {results['threats_found']}")
            if results['by_technique']:
                print("  By technique:")
                for tid, count in results['by_technique'].items():
                    print(f"    {tid}: {count}")

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nReport saved to: {args.output}")

        return

    # Analyze text input
    if args.text:
        text = args.text
    else:
        text = sys.stdin.read().strip()

    if not text:
        print("No input provided. Use: atlas_threat_detector.py 'text' or pipe input")
        sys.exit(1)

    result = detector.analyze_input(text)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"[ATLAS ANALYSIS]")
        print(f"  Risk: {result['overall_risk']}")
        print(f"  Recommendation: {result['recommendation']}")
        print(f"  Detections: {result['detection_count']}")

        if result['detections']:
            print("  Techniques detected:")
            for d in result['detections']:
                print(f"    - {d['technique_id']}: {d['technique_name']} ({d['risk_level']})")


if __name__ == "__main__":
    main()
