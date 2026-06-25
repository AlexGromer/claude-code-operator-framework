#!/usr/bin/env python3
"""
MikroTik RouterOS Configuration Validator

Validates MikroTik RouterOS configuration exports for security issues:
- Default credentials detection
- Open management ports (Telnet, FTP, unprotected Winbox)
- Missing firewall rules
- Insecure services enabled
- Common misconfigurations

Usage:
    python routeros_config_validator.py --file config.rsc
    python routeros_config_validator.py --file config.rsc --json
    python routeros_config_validator.py --file config.rsc --verbose
"""

import argparse
import sys
import json
import re
from typing import Dict, List, Set
from pathlib import Path


class RouterOSConfigValidator:
    """Validates MikroTik RouterOS configurations."""

    # Default/common passwords to check for
    DEFAULT_PASSWORDS = [
        "", "admin", "password", "12345", "123456", "root", "mikrotik",
        "router", "default", "changeme"
    ]

    # Insecure services that should be disabled
    INSECURE_SERVICES = {
        "telnet": {"port": 23, "risk": "CRITICAL"},
        "ftp": {"port": 21, "risk": "HIGH"},
        "www": {"port": 80, "risk": "MEDIUM"},
        "api": {"port": 8728, "risk": "HIGH"},
        "api-ssl": {"port": 8729, "risk": "MEDIUM"},
        "bandwidth-server": {"port": 2000, "risk": "LOW"}
    }

    # Required firewall rules
    RECOMMENDED_FIREWALL_RULES = [
        "drop invalid connections",
        "drop port scanners",
        "allow established/related",
        "protect router input chain",
        "protect router winbox/ssh"
    ]

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.errors = []
        self.warnings = []
        self.info = []
        self.config_lines = []

    def log_error(self, message: str):
        """Add error message."""
        self.errors.append(message)
        if self.verbose:
            print(f"❌ ERROR: {message}", file=sys.stderr)

    def log_warning(self, message: str):
        """Add warning message."""
        self.warnings.append(message)
        if self.verbose:
            print(f"⚠️  WARNING: {message}", file=sys.stderr)

    def log_info(self, message: str):
        """Add info message."""
        self.info.append(message)
        if self.verbose:
            print(f"ℹ️  INFO: {message}", file=sys.stderr)

    def validate_file(self, filepath: str) -> Dict:
        """
        Validate RouterOS configuration file.

        Args:
            filepath: Path to .rsc configuration file

        Returns:
            Dict with validation results
        """
        path = Path(filepath)
        if not path.exists():
            self.log_error(f"File not found: {filepath}")
            return self._get_result()

        # Read config
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                self.config_lines = f.readlines()
        except Exception as e:
            self.log_error(f"Failed to read file: {e}")
            return self._get_result()

        if not self.config_lines:
            self.log_error("Configuration file is empty")
            return self._get_result()

        # Combine into single string for pattern matching
        config_content = "".join(self.config_lines)

        # Validate different aspects
        self._check_users_and_passwords(config_content)
        self._check_services(config_content)
        self._check_firewall(config_content)
        self._check_ssh_config(config_content)
        self._check_snmp(config_content)
        self._check_discovery(config_content)
        self._check_mac_server(config_content)
        self._check_dns(config_content)
        self._check_ntp(config_content)
        self._check_general_security(config_content)

        return self._get_result()

    def _check_users_and_passwords(self, config: str):
        """Check for default/weak credentials."""
        # Look for /user sections
        user_blocks = re.findall(r'/user\s+add.*?(?=\n/|\Z)', config, re.DOTALL)

        if not user_blocks:
            self.log_warning("No user configuration found - this may be a partial export")
            return

        for user_block in user_blocks:
            # Extract username
            username_match = re.search(r'name=(\S+)', user_block)
            if username_match:
                username = username_match.group(1).strip('"')

                # Check if admin user exists
                if username == "admin":
                    self.log_info("Default 'admin' user found")

                    # Check password field
                    password_match = re.search(r'password=(\S+)', user_block)
                    if password_match:
                        password = password_match.group(1).strip('"')
                        if password in self.DEFAULT_PASSWORDS:
                            self.log_error(f"CRITICAL: User '{username}' has default/weak password!")
                        elif len(password) < 8:
                            self.log_warning(f"User '{username}' has short password (<8 chars)")
                    else:
                        # No password field = empty password!
                        self.log_error(f"CRITICAL: User '{username}' has no password set!")

    def _check_services(self, config: str):
        """Check for insecure services enabled."""
        # Look for /ip service section
        service_section = re.search(r'/ip\s+service.*?(?=\n/|\Z)', config, re.DOTALL)

        if not service_section:
            self.log_warning("No /ip service configuration found")
            return

        service_content = service_section.group(0)

        for service_name, details in self.INSECURE_SERVICES.items():
            # Check if service is explicitly disabled
            disabled_pattern = rf'set\s+{service_name}.*?disabled=yes'
            enabled_pattern = rf'set\s+{service_name}.*?disabled=no'

            is_disabled = re.search(disabled_pattern, service_content, re.IGNORECASE)
            is_enabled = re.search(enabled_pattern, service_content, re.IGNORECASE)

            if is_enabled or (not is_disabled and service_name in ["telnet", "ftp"]):
                # Service is enabled
                risk = details["risk"]
                port = details["port"]

                if risk == "CRITICAL":
                    self.log_error(f"CRITICAL: {service_name.upper()} service enabled (port {port}) - "
                                 "highly insecure!")
                elif risk == "HIGH":
                    self.log_warning(f"HIGH RISK: {service_name.upper()} service enabled (port {port})")
                else:
                    self.log_warning(f"{service_name.upper()} service enabled (port {port})")

        # Check if SSH is enabled and on non-standard port
        ssh_match = re.search(r'set\s+ssh.*?port=(\d+)', service_content)
        if ssh_match:
            ssh_port = int(ssh_match.group(1))
            if ssh_port == 22:
                self.log_warning("SSH on default port 22 - consider changing to non-standard port")
            else:
                self.log_info(f"✓ SSH on non-standard port {ssh_port}")

    def _check_firewall(self, config: str):
        """Check firewall configuration."""
        # Look for /ip firewall filter section
        firewall_section = re.search(r'/ip\s+firewall\s+filter.*?(?=\n/[a-z]|\Z)', config, re.DOTALL)

        if not firewall_section:
            self.log_error("CRITICAL: No firewall rules found - router is unprotected!")
            return

        firewall_content = firewall_section.group(0)
        rules = re.findall(r'add\s+.*', firewall_content)

        if len(rules) == 0:
            self.log_error("CRITICAL: No firewall rules configured!")
            return

        self.log_info(f"Found {len(rules)} firewall rules")

        # Check for essential protections
        checks = {
            "drop invalid": r'connection-state=invalid.*action=drop',
            "allow established": r'connection-state=established.*action=accept',
            "allow related": r'connection-state=related.*action=accept',
            "input chain protection": r'chain=input',
            "default drop": r'action=drop'
        }

        for check_name, pattern in checks.items():
            if re.search(pattern, firewall_content, re.IGNORECASE):
                self.log_info(f"✓ Found {check_name} rule")
            else:
                self.log_warning(f"Missing recommended rule: {check_name}")

        # Check for port scanner protection
        if "port-scan" in firewall_content.lower() or "detect-port-scan" in firewall_content.lower():
            self.log_info("✓ Port scanner detection enabled")
        else:
            self.log_warning("No port scanner detection found")

    def _check_ssh_config(self, config: str):
        """Check SSH configuration security."""
        ssh_section = re.search(r'/ip\s+ssh.*?(?=\n/|\Z)', config, re.DOTALL)

        if not ssh_section:
            return

        ssh_content = ssh_section.group(0)

        # Check strong crypto
        if "strong-crypto=yes" in ssh_content:
            self.log_info("✓ SSH strong crypto enabled")
        else:
            self.log_warning("SSH strong crypto not enabled - recommend 'set strong-crypto=yes'")

        # Check allowed users
        if "allow-none-crypto" in ssh_content:
            if "allow-none-crypto=yes" in ssh_content:
                self.log_error("SSH allows unencrypted connections - disable 'allow-none-crypto'")

    def _check_snmp(self, config: str):
        """Check SNMP configuration."""
        snmp_section = re.search(r'/snmp.*?(?=\n/|\Z)', config, re.DOTALL)

        if not snmp_section:
            self.log_info("SNMP not configured (good if not needed)")
            return

        snmp_content = snmp_section.group(0)

        # Check if enabled
        if "enabled=yes" in snmp_content:
            self.log_warning("SNMP enabled - ensure it's using SNMPv3 with auth")

            # Check community strings
            if "community=public" in snmp_content:
                self.log_error("CRITICAL: SNMP using default 'public' community string!")

            # Check for SNMPv3
            if "snmp-v3" not in snmp_content.lower():
                self.log_warning("SNMP v1/v2 in use - upgrade to SNMPv3 for better security")

    def _check_discovery(self, config: str):
        """Check neighbor discovery protocols."""
        # Check IP neighbor discovery
        ip_neighbor = re.search(r'/ip\s+neighbor\s+discovery.*?(?=\n/|\Z)', config, re.DOTALL)
        if ip_neighbor:
            if "discover=yes" in ip_neighbor.group(0):
                self.log_warning("IP neighbor discovery enabled on some interfaces - "
                               "disable on WAN interfaces")

        # Check MAC discovery protocols (CDP, LLDP)
        if "/interface ethernet" in config:
            if re.search(r'l2mtu.*lldp.*disabled=no', config, re.IGNORECASE):
                self.log_info("LLDP enabled - ensure it's only on trusted interfaces")

    def _check_mac_server(self, config: str):
        """Check MAC server (Winbox/MAC-telnet) configuration."""
        mac_server = re.search(r'/tool\s+mac-server.*?(?=\n/|\Z)', config, re.DOTALL)

        if mac_server:
            content = mac_server.group(0)
            if "disabled=no" in content or "set" in content:
                self.log_warning("MAC server enabled - ensure it's restricted to management interfaces")

                # Check if restricted to specific interfaces
                if "interface=" not in content or "interface=all" in content:
                    self.log_warning("MAC server accessible on all interfaces - restrict to management only")

    def _check_dns(self, config: str):
        """Check DNS configuration."""
        dns_section = re.search(r'/ip\s+dns.*?(?=\n/|\Z)', config, re.DOTALL)

        if dns_section:
            content = dns_section.group(0)

            # Check if DNS server is enabled
            if "allow-remote-requests=yes" in content:
                self.log_warning("DNS server allows remote requests - ensure firewall rules protect it")

                # Check cache size
                cache_match = re.search(r'cache-size=(\d+)', content)
                if cache_match:
                    cache_size = int(cache_match.group(1))
                    if cache_size < 2048:
                        self.log_info(f"DNS cache size is small ({cache_size}KB)")

    def _check_ntp(self, config: str):
        """Check NTP configuration."""
        ntp_client = re.search(r'/system\s+ntp\s+client.*?(?=\n/|\Z)', config, re.DOTALL)
        ntp_server = re.search(r'/system\s+ntp\s+server.*?(?=\n/|\Z)', config, re.DOTALL)

        if ntp_client and "enabled=yes" in ntp_client.group(0):
            self.log_info("✓ NTP client enabled (good for accurate time)")
        else:
            self.log_warning("NTP client not enabled - accurate time is important for logs/certificates")

        if ntp_server and "enabled=yes" in ntp_server.group(0):
            self.log_warning("NTP server enabled - ensure firewall protects it from abuse")

    def _check_general_security(self, config: str):
        """Check general security settings."""
        # Check bandwidth server (often used for attacks)
        if "/tool bandwidth-server" in config:
            if "enabled=yes" in config:
                self.log_warning("Bandwidth test server enabled - disable if not needed")

        # Check if router identity is set
        identity_match = re.search(r'/system\s+identity.*?name=(\S+)', config, re.DOTALL)
        if identity_match:
            identity = identity_match.group(1).strip('"')
            if identity.lower() in ["mikrotik", "router", "rb"]:
                self.log_warning(f"Router identity is generic ('{identity}') - use descriptive name")
        else:
            self.log_warning("Router identity not set")

        # Check for RouterOS version
        version_match = re.search(r'# software id = (\S+)', config)
        if version_match:
            version = version_match.group(1)
            self.log_info(f"RouterOS version: {version}")

        # Check for backup encryption
        if "/system backup" in config:
            if "encryption=no" in config or "password=" not in config:
                self.log_warning("Backups not encrypted - enable encryption for sensitive configs")

    def _get_result(self) -> Dict:
        """Get validation result."""
        # Calculate severity score
        severity_score = len(self.errors) * 10 + len(self.warnings) * 3

        return {
            "valid": len(self.errors) == 0,
            "secure": severity_score < 10,
            "severity_score": severity_score,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings)
        }


def main():
    parser = argparse.ArgumentParser(description="Validate MikroTik RouterOS configurations")
    parser.add_argument("--file", required=True, help="Path to RouterOS .rsc config file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    validator = RouterOSConfigValidator(verbose=args.verbose)
    result = validator.validate_file(args.file)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Human-readable output
        print(f"\n{'='*60}")
        print(f"RouterOS Configuration Security Analysis: {args.file}")
        print(f"{'='*60}\n")

        if result["secure"]:
            print("✅ SECURE: Configuration passes security checks\n")
        elif result["valid"]:
            print("⚠️  WARNINGS ONLY: Configuration has warnings but no critical errors\n")
        else:
            print("❌ INSECURE: Configuration has critical security issues\n")

        print(f"Severity Score: {result['severity_score']} "
              f"(Errors: {result['error_count']}, Warnings: {result['warning_count']})\n")

        if result["errors"]:
            print(f"🔴 CRITICAL ISSUES ({len(result['errors'])}):")
            for err in result["errors"]:
                print(f"   - {err}")
            print()

        if result["warnings"]:
            print(f"⚠️  WARNINGS ({len(result['warnings'])}):")
            for warn in result["warnings"]:
                print(f"   - {warn}")
            print()

        if result["info"] and args.verbose:
            print(f"ℹ️  INFO:")
            for info in result["info"]:
                print(f"   - {info}")
            print()

    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
