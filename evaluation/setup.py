#!/usr/bin/env python3
"""
Claude Evaluation Framework Setup Wizard
Version: 1.0.0

Interactive configuration wizard for first-time setup.
Generates config.yaml with user preferences.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import yaml


class SetupWizard:
    """Interactive setup wizard for Claude evaluation framework."""

    def __init__(self):
        self.config_path = Path.home() / ".claude" / "evaluation" / "config.yaml"
        self.config = {}

    def welcome(self):
        """Display welcome message."""
        print("=" * 70)
        print(" " * 15 + "Claude Evaluation Framework Setup")
        print(" " * 25 + "Version 1.0.0")
        print("=" * 70)
        print()
        print("This wizard will help you configure the evaluation framework.")
        print("You can change these settings later by editing config.yaml")
        print()

    def ask_yes_no(self, question: str, default: bool = True) -> bool:
        """Ask a yes/no question."""
        default_str = "Y/n" if default else "y/N"
        while True:
            response = input(f"{question} [{default_str}]: ").strip().lower()
            if not response:
                return default
            if response in ['y', 'yes']:
                return True
            if response in ['n', 'no']:
                return False
            print("Please answer 'y' or 'n'")

    def ask_choice(self, question: str, choices: list, default: int = 0) -> str:
        """Ask a multiple-choice question."""
        print(f"\n{question}")
        for i, choice in enumerate(choices, 1):
            marker = "(*)" if i == default + 1 else "( )"
            print(f"  {marker} {i}. {choice}")

        while True:
            response = input(f"Choice [1-{len(choices)}] (default: {default + 1}): ").strip()
            if not response:
                return choices[default]
            try:
                idx = int(response) - 1
                if 0 <= idx < len(choices):
                    return choices[idx]
            except ValueError:
                pass
            print(f"Please enter a number between 1 and {len(choices)}")

    def ask_string(self, question: str, default: str = "") -> str:
        """Ask for a string input."""
        if default:
            response = input(f"{question} [{default}]: ").strip()
            return response if response else default
        else:
            while True:
                response = input(f"{question}: ").strip()
                if response:
                    return response
                print("This field is required")

    def configure_metrics(self):
        """Configure metrics collection settings."""
        print("\n" + "=" * 70)
        print("METRICS COLLECTION")
        print("=" * 70)

        self.config['evaluation'] = {
            'metrics': {
                'enabled': self.ask_yes_no("Enable automatic metrics collection?", True),
                'collection': 'automatic',
                'storage_path': '~/.claude/evaluation/data/metrics.jsonl'
            },
            'reporting': {},
            'test_cases': {
                'baseline_path': '~/.claude/evaluation/test_cases.json',
                'min_coverage': 95
            },
            'regression': {
                'enabled': True,
                'threshold_accuracy': 0.05,
                'threshold_hallucination': 0.03,
                'threshold_tool_errors': 0.10
            },
            'ab_testing': {
                'enabled': False,
                'sample_size': 30,
                'confidence_level': 0.95
            }
        }

    def configure_reporting(self):
        """Configure reporting settings."""
        print("\n" + "=" * 70)
        print("REPORTING CONFIGURATION")
        print("=" * 70)

        schedule_choices = ['manual', 'weekly', 'daily', 'on-commit']
        schedule = self.ask_choice(
            "How often should reports be generated?",
            schedule_choices,
            default=0  # manual
        )

        format_choices = ['markdown', 'json', 'html']
        report_format = self.ask_choice(
            "Preferred report format?",
            format_choices,
            default=0  # markdown
        )

        self.config['evaluation']['reporting'] = {
            'schedule': schedule,
            'format': report_format,
            'output_path': '~/.claude/evaluation/reports/',
            'weekly_day': 'monday',
            'weekly_time': '09:00'
        }

    def configure_few_shot(self):
        """Configure few-shot examples settings."""
        print("\n" + "=" * 70)
        print("FEW-SHOT EXAMPLES")
        print("=" * 70)

        mode_choices = ['manual', 'assisted', 'semi-automated']
        mode_descriptions = [
            'manual - You create and update examples',
            'assisted - Metrics suggest improvements',
            'semi-automated - System suggests new examples (Phase 3)'
        ]

        print("\nFew-shot example curation modes:")
        for desc in mode_descriptions:
            print(f"  • {desc}")

        mode = self.ask_choice(
            "\nChoose curation mode:",
            mode_choices,
            default=0  # manual
        )

        auto_load = self.ask_yes_no("Automatically load examples based on task domain?", True)

        self.config['few_shot'] = {
            'mode': mode,
            'library_path': '~/.claude/examples/',
            'auto_load': auto_load,
            'max_examples_per_domain': 3,
            'curation': {
                'enabled': mode != 'manual',
                'min_corrections': 3,
                'auto_suggest': mode == 'semi-automated'
            }
        }

    def configure_tools(self):
        """Configure custom tools settings."""
        print("\n" + "=" * 70)
        print("CUSTOM TOOLS")
        print("=" * 70)

        custom_tools = self.ask_yes_no("Enable custom tools (security, devops)?", True)

        mcp_enabled = False
        if custom_tools:
            mcp_enabled = self.ask_yes_no("Enable MCP server for structured tool interfaces?", False)

        self.config['tools'] = {
            'custom_tools_enabled': custom_tools,
            'tools_path': '~/.claude/tools/',
            'mcp_enabled': mcp_enabled,
            'mcp_server_path': '~/.claude/tools/mcp_server.py',
            'mcp_port': 8765,
            'security_tools_require_confirmation': True,
            'destructive_tools_require_explicit': True
        }

    def configure_automation(self):
        """Configure automation settings."""
        print("\n" + "=" * 70)
        print("AUTOMATION")
        print("=" * 70)

        backend_choices = ['none', 'cron', 'systemd', 'launchd', 'manual']
        backend_descriptions = [
            'none - No automation, run commands manually',
            'cron - Traditional Linux/Unix scheduling',
            'systemd - Modern Linux systemd timers',
            'launchd - macOS scheduling',
            'manual - Run scripts manually when needed'
        ]

        print("\nAutomation backends:")
        for desc in backend_descriptions:
            print(f"  • {desc}")

        backend = self.ask_choice(
            "\nChoose automation backend:",
            backend_choices,
            default=0  # none
        )

        hooks_enabled = self.ask_yes_no("Enable hooks for automatic metric logging?", False)

        self.config['automation'] = {
            'backend': backend,
            'hooks': {
                'enabled': hooks_enabled,
                'after_tool_use': '~/.claude/evaluation/hooks/log_tool_use.py',
                'pre_commit': '~/.claude/evaluation/hooks/pre_commit_check.sh'
            },
            'cron': {
                'weekly_report': '0 9 * * 1',
                'monthly_summary': '0 10 1 * *'
            },
            'systemd': {
                'timer_weekly': 'Mon *-*-* 09:00:00',
                'timer_monthly': '*-*-01 10:00:00'
            }
        }

    def configure_notifications(self):
        """Configure notification settings."""
        print("\n" + "=" * 70)
        print("NOTIFICATIONS")
        print("=" * 70)

        notifications_enabled = self.ask_yes_no("Enable notifications?", False)

        desktop_enabled = False
        telegram_enabled = False
        email_enabled = False

        if notifications_enabled:
            desktop_enabled = self.ask_yes_no("  Enable desktop notifications?", True)
            telegram_enabled = self.ask_yes_no("  Enable Telegram notifications?", False)
            email_enabled = self.ask_yes_no("  Enable email notifications?", False)

        self.config['notifications'] = {
            'enabled': notifications_enabled,
            'desktop': {'enabled': desktop_enabled},
            'telegram': {
                'enabled': telegram_enabled,
                'bot_token_env': 'TELEGRAM_BOT_TOKEN',
                'chat_id_env': 'TELEGRAM_CHAT_ID'
            },
            'email': {
                'enabled': email_enabled,
                'smtp_host': 'localhost',
                'smtp_port': 25,
                'from_address': 'claude@localhost',
                'to_address': 'user@localhost'
            },
            'triggers': {
                'on_weekly_report': True,
                'on_regression_detected': True,
                'on_threshold_exceeded': True
            }
        }

    def configure_security(self):
        """Configure security settings."""
        print("\n" + "=" * 70)
        print("SECURITY & COMPLIANCE")
        print("=" * 70)

        pre_commit = self.ask_yes_no("Enable pre-commit security checks?", True)
        audit_logging = self.ask_yes_no("Enable audit logging?", True)

        self.config['security'] = {
            'pre_commit_checks': {
                'secrets_detection': pre_commit,
                'gitignore_verification': pre_commit
            },
            'audit_logging': {
                'enabled': audit_logging,
                'log_path': '~/.claude/evaluation/audit.log',
                'log_level': 'INFO'
            },
            'data_retention': {
                'metrics_days': 365,
                'logs_days': 90,
                'reports_days': 730
            }
        }

    def configure_advanced(self):
        """Configure advanced settings."""
        self.config['advanced'] = {
            'async_enabled': True,
            'max_concurrent_requests': 5,
            'cache_enabled': True,
            'cache_ttl': 300,
            'debug_mode': False,
            'verbose_logging': False,
            'api_timeout': 60,
            'max_retries': 3,
            'retry_delay': 1
        }

        self.config['experimental'] = {
            'example_learner': {
                'enabled': False,
                'clustering_algorithm': 'kmeans',
                'min_cluster_size': 3
            },
            'dashboard': {
                'enabled': False,
                'port': 8080,
                'host': 'localhost'
            },
            'go_mcp_server': {
                'enabled': False,
                'binary_path': '~/.claude/tools/mcp-server-go'
            }
        }

    def save_config(self):
        """Save configuration to YAML file."""
        print("\n" + "=" * 70)
        print("SAVING CONFIGURATION")
        print("=" * 70)

        # Backup existing config if it exists
        if self.config_path.exists():
            backup_path = self.config_path.with_suffix('.yaml.backup')
            print(f"Backing up existing config to: {backup_path}")
            self.config_path.rename(backup_path)

        # Write new config
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)

        print(f"✅ Configuration saved to: {self.config_path}")

    def show_next_steps(self):
        """Display next steps after setup."""
        print("\n" + "=" * 70)
        print("SETUP COMPLETE!")
        print("=" * 70)
        print("\nNext steps:")
        print()
        print("1. Install dependencies:")
        print("   cd ~/.claude/evaluation")
        print("   pip install -r requirements.txt")
        print()
        print("2. Test metrics tracker:")
        print("   python metrics_tracker.py --quick-check")
        print()
        print("3. Generate your first report:")
        print("   python metrics_tracker.py --report weekly")
        print()
        print("4. Create few-shot examples:")
        print("   Edit files in ~/.claude/examples/")
        print()
        print("5. Update Claude settings.json (if using hooks):")
        print("   Add permissions for custom tools and hooks")
        print()
        print("Full documentation: ~/.claude/evaluation/README.md")
        print()

    def run(self):
        """Run the setup wizard."""
        self.welcome()

        # Configuration sections
        self.configure_metrics()
        self.configure_reporting()
        self.configure_few_shot()
        self.configure_tools()
        self.configure_automation()
        self.configure_notifications()
        self.configure_security()
        self.configure_advanced()

        # Save configuration
        self.save_config()

        # Show next steps
        self.show_next_steps()


def main():
    """CLI entry point."""
    wizard = SetupWizard()
    try:
        wizard.run()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
