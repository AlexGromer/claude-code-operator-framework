#!/usr/bin/env python3
"""
Comprehensive Code Review Checks

All possible static analysis checks for code before delivery.
Used by code review subagent to verify code quality.

Usage:
    python code_review_checks.py --file path/to/file.py
    python code_review_checks.py --code "def foo(): pass"
    python code_review_checks.py --dir path/to/project
"""

import ast
import re
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict


@dataclass
class Issue:
    """Single code issue."""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str  # syntax, undefined, security, style, logic, etc.
    line: int
    column: int
    message: str
    code: str  # issue code like E001, W002
    suggestion: Optional[str] = None


@dataclass
class ReviewResult:
    """Complete review result."""
    file_path: str
    language: str
    issues: List[Issue] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    passed: bool = True

    def add_issue(self, issue: Issue):
        self.issues.append(issue)
        self.summary[issue.severity] = self.summary.get(issue.severity, 0) + 1
        if issue.severity in ('CRITICAL', 'HIGH'):
            self.passed = False


class PythonAnalyzer:
    """Comprehensive Python code analyzer."""

    def __init__(self, code: str, file_path: str = "<string>"):
        self.code = code
        self.file_path = file_path
        self.lines = code.split('\n')
        self.result = ReviewResult(file_path=file_path, language="python")
        self.tree: Optional[ast.AST] = None

        # Track definitions and usages
        self.defined_names: Set[str] = set()
        self.used_names: Set[str] = set()
        self.function_defs: Dict[str, ast.FunctionDef] = {}
        self.function_calls: List[Tuple[str, int, int, List[ast.expr]]] = []
        self.class_defs: Dict[str, ast.ClassDef] = {}
        self.imports: Set[str] = set()
        self.variables: Dict[str, int] = {}  # name -> line defined

    def analyze(self) -> ReviewResult:
        """Run all checks."""
        # 1. Syntax check (must pass for other checks)
        if not self._check_syntax():
            return self.result

        # 2. Parse AST
        self._parse_ast()

        # 3. Run all checks
        self._check_undefined_names()
        self._check_function_signatures()
        self._check_unused_definitions()
        self._check_imports()
        self._check_security()
        self._check_logic_errors()
        self._check_common_mistakes()
        self._check_style()
        self._check_complexity()
        self._check_increments()
        self._check_error_handling()
        self._check_type_hints()

        return self.result

    def _check_syntax(self) -> bool:
        """Check if code is syntactically valid."""
        try:
            compile(self.code, self.file_path, 'exec')
            return True
        except SyntaxError as e:
            self.result.add_issue(Issue(
                severity="CRITICAL",
                category="syntax",
                line=e.lineno or 1,
                column=e.offset or 0,
                message=f"Syntax error: {e.msg}",
                code="E001",
                suggestion="Fix the syntax error before proceeding"
            ))
            return False

    def _parse_ast(self):
        """Parse AST and collect definitions/usages."""
        try:
            self.tree = ast.parse(self.code)
        except Exception:
            return

        class Visitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer
                self.scope_stack: List[Set[str]] = [set()]  # Stack of local scopes

            def current_scope(self) -> Set[str]:
                return self.scope_stack[-1]

            def all_defined(self) -> Set[str]:
                result = set()
                for scope in self.scope_stack:
                    result.update(scope)
                return result

            def visit_FunctionDef(self, node):
                self.analyzer.defined_names.add(node.name)
                self.analyzer.function_defs[node.name] = node
                self.current_scope().add(node.name)

                # New scope for function body
                self.scope_stack.append(set())

                # Add parameters to scope
                for arg in node.args.args:
                    self.current_scope().add(arg.arg)
                for arg in node.args.posonlyargs:
                    self.current_scope().add(arg.arg)
                for arg in node.args.kwonlyargs:
                    self.current_scope().add(arg.arg)
                if node.args.vararg:
                    self.current_scope().add(node.args.vararg.arg)
                if node.args.kwarg:
                    self.current_scope().add(node.args.kwarg.arg)

                self.generic_visit(node)
                self.scope_stack.pop()

            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_ClassDef(self, node):
                self.analyzer.defined_names.add(node.name)
                self.analyzer.class_defs[node.name] = node
                self.current_scope().add(node.name)

                self.scope_stack.append(set())
                self.generic_visit(node)
                self.scope_stack.pop()

            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Store):
                    self.current_scope().add(node.id)
                    self.analyzer.defined_names.add(node.id)
                    self.analyzer.variables[node.id] = node.lineno
                elif isinstance(node.ctx, ast.Load):
                    self.analyzer.used_names.add(node.id)
                self.generic_visit(node)

            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    self.analyzer.function_calls.append((
                        node.func.id,
                        node.lineno,
                        node.col_offset,
                        node.args
                    ))
                elif isinstance(node.func, ast.Attribute):
                    # Method call like obj.method()
                    pass
                self.generic_visit(node)

            def visit_Import(self, node):
                for alias in node.names:
                    name = alias.asname or alias.name.split('.')[0]
                    self.analyzer.imports.add(name)
                    self.current_scope().add(name)
                    self.analyzer.defined_names.add(name)
                self.generic_visit(node)

            def visit_ImportFrom(self, node):
                for alias in node.names:
                    name = alias.asname or alias.name
                    if name != '*':
                        self.analyzer.imports.add(name)
                        self.current_scope().add(name)
                        self.analyzer.defined_names.add(name)
                self.generic_visit(node)

            def visit_For(self, node):
                # Loop variable
                if isinstance(node.target, ast.Name):
                    self.current_scope().add(node.target.id)
                    self.analyzer.defined_names.add(node.target.id)
                elif isinstance(node.target, ast.Tuple):
                    for elt in node.target.elts:
                        if isinstance(elt, ast.Name):
                            self.current_scope().add(elt.id)
                            self.analyzer.defined_names.add(elt.id)
                self.generic_visit(node)

            def visit_With(self, node):
                for item in node.items:
                    if item.optional_vars:
                        if isinstance(item.optional_vars, ast.Name):
                            self.current_scope().add(item.optional_vars.id)
                            self.analyzer.defined_names.add(item.optional_vars.id)
                self.generic_visit(node)

            def visit_ExceptHandler(self, node):
                if node.name:
                    self.current_scope().add(node.name)
                    self.analyzer.defined_names.add(node.name)
                self.generic_visit(node)

            def visit_comprehension(self, node):
                if isinstance(node.target, ast.Name):
                    self.current_scope().add(node.target.id)
                self.generic_visit(node)

        visitor = Visitor(self)
        visitor.visit(self.tree)

    def _check_undefined_names(self):
        """Check for undefined names."""
        # Built-in names - comprehensive list
        builtins = {
            # Built-in functions
            'abs', 'aiter', 'all', 'any', 'anext', 'ascii', 'bin', 'bool',
            'breakpoint', 'bytearray', 'bytes', 'callable', 'chr', 'classmethod',
            'compile', 'complex', 'delattr', 'dict', 'dir', 'divmod', 'enumerate',
            'eval', 'exec', 'filter', 'float', 'format', 'frozenset', 'getattr',
            'globals', 'hasattr', 'hash', 'help', 'hex', 'id', 'input', 'int',
            'isinstance', 'issubclass', 'iter', 'len', 'list', 'locals', 'map',
            'max', 'memoryview', 'min', 'next', 'object', 'oct', 'open', 'ord',
            'pow', 'print', 'property', 'range', 'repr', 'reversed', 'round',
            'set', 'setattr', 'slice', 'sorted', 'staticmethod', 'str', 'sum',
            'super', 'tuple', 'type', 'vars', 'zip',
            # Built-in exceptions
            'BaseException', 'Exception', 'ArithmeticError', 'AssertionError',
            'AttributeError', 'BlockingIOError', 'BrokenPipeError', 'BufferError',
            'BytesWarning', 'ChildProcessError', 'ConnectionAbortedError',
            'ConnectionError', 'ConnectionRefusedError', 'ConnectionResetError',
            'DeprecationWarning', 'EOFError', 'EnvironmentError', 'FileExistsError',
            'FileNotFoundError', 'FloatingPointError', 'FutureWarning', 'GeneratorExit',
            'IOError', 'ImportError', 'ImportWarning', 'IndentationError', 'IndexError',
            'InterruptedError', 'IsADirectoryError', 'KeyError', 'KeyboardInterrupt',
            'LookupError', 'MemoryError', 'ModuleNotFoundError', 'NameError',
            'NotADirectoryError', 'NotImplemented', 'NotImplementedError', 'OSError',
            'OverflowError', 'PendingDeprecationWarning', 'PermissionError',
            'ProcessLookupError', 'RecursionError', 'ReferenceError', 'ResourceWarning',
            'RuntimeError', 'RuntimeWarning', 'StopAsyncIteration', 'StopIteration',
            'SyntaxError', 'SyntaxWarning', 'SystemError', 'SystemExit', 'TabError',
            'TimeoutError', 'TypeError', 'UnboundLocalError', 'UnicodeDecodeError',
            'UnicodeEncodeError', 'UnicodeError', 'UnicodeTranslateError',
            'UnicodeWarning', 'UserWarning', 'ValueError', 'Warning', 'ZeroDivisionError',
            # Built-in constants
            'True', 'False', 'None', 'Ellipsis', '__debug__',
            # Special names
            '__name__', '__file__', '__doc__', '__package__', '__spec__',
            '__annotations__', '__builtins__', '__cached__', '__loader__',
            'self', 'cls',
            # Common typing names (often used without import in annotations)
            'Any', 'Optional', 'List', 'Dict', 'Set', 'Tuple', 'Union',
            'Callable', 'Iterable', 'Iterator', 'Generator', 'Sequence',
        }

        for name, line, col, args in self.function_calls:
            if name not in self.defined_names and name not in builtins and name not in self.imports:
                self.result.add_issue(Issue(
                    severity="CRITICAL",
                    category="undefined",
                    line=line,
                    column=col,
                    message=f"Function '{name}' is called but not defined",
                    code="E101",
                    suggestion=f"Define function '{name}' before calling it, or check for typos"
                ))

    def _check_function_signatures(self):
        """Check function call arguments match definitions."""
        for name, line, col, args in self.function_calls:
            if name in self.function_defs:
                func_def = self.function_defs[name]

                # Count required args (without defaults)
                num_defaults = len(func_def.args.defaults)
                num_args = len(func_def.args.args)
                # Subtract 'self' for methods
                if num_args > 0 and func_def.args.args[0].arg == 'self':
                    num_args -= 1

                min_args = num_args - num_defaults
                max_args = num_args

                # Check vararg/kwarg
                has_vararg = func_def.args.vararg is not None
                has_kwarg = func_def.args.kwarg is not None

                num_call_args = len(args)

                if not has_vararg and num_call_args > max_args:
                    self.result.add_issue(Issue(
                        severity="HIGH",
                        category="signature",
                        line=line,
                        column=col,
                        message=f"Too many arguments for '{name}': expected {max_args}, got {num_call_args}",
                        code="E102",
                        suggestion=f"Check function signature: def {name}(...)"
                    ))
                elif num_call_args < min_args:
                    self.result.add_issue(Issue(
                        severity="HIGH",
                        category="signature",
                        line=line,
                        column=col,
                        message=f"Too few arguments for '{name}': expected at least {min_args}, got {num_call_args}",
                        code="E103",
                        suggestion=f"Check function signature: def {name}(...)"
                    ))

    def _check_unused_definitions(self):
        """Check for unused functions/variables."""
        builtins = {'__init__', '__str__', '__repr__', '__enter__', '__exit__',
                   '__call__', '__iter__', '__next__', '__len__', '__getitem__',
                   '__setitem__', '__delitem__', '__contains__', '__eq__', '__ne__',
                   '__lt__', '__le__', '__gt__', '__ge__', '__hash__', '__bool__',
                   'main', 'setup', 'teardown'}

        for name, func in self.function_defs.items():
            if name not in self.used_names and name not in builtins and not name.startswith('_'):
                self.result.add_issue(Issue(
                    severity="LOW",
                    category="unused",
                    line=func.lineno,
                    column=func.col_offset,
                    message=f"Function '{name}' is defined but never used",
                    code="W101",
                    suggestion="Remove unused function or add usage"
                ))

    def _check_imports(self):
        """Check for import issues."""
        # Check for unused imports
        for imp in self.imports:
            if imp not in self.used_names and imp not in {'typing', 'annotations'}:
                # Find the import line
                for i, line in enumerate(self.lines, 1):
                    if f'import {imp}' in line or f'import {imp},' in line or f' {imp}' in line:
                        self.result.add_issue(Issue(
                            severity="LOW",
                            category="imports",
                            line=i,
                            column=0,
                            message=f"Import '{imp}' is not used",
                            code="W201",
                            suggestion="Remove unused import"
                        ))
                        break

    def _check_security(self):
        """Check for security issues."""
        security_patterns = [
            (r'eval\s*\(', "CRITICAL", "Use of eval() is dangerous", "S001"),
            (r'exec\s*\(', "CRITICAL", "Use of exec() is dangerous", "S002"),
            (r'__import__\s*\(', "HIGH", "Dynamic import can be dangerous", "S003"),
            (r'pickle\.loads?\s*\(', "HIGH", "Pickle can execute arbitrary code", "S004"),
            (r'subprocess.*shell\s*=\s*True', "HIGH", "shell=True is dangerous", "S005"),
            (r'os\.system\s*\(', "HIGH", "os.system is dangerous, use subprocess", "S006"),
            (r'password\s*=\s*["\'][^"\']+["\']', "CRITICAL", "Hardcoded password detected", "S007"),
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "CRITICAL", "Hardcoded API key detected", "S008"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "CRITICAL", "Hardcoded secret detected", "S009"),
            (r'token\s*=\s*["\'][A-Za-z0-9_-]{20,}["\']', "HIGH", "Possible hardcoded token", "S010"),
            (r'SELECT.*\+.*\+|SELECT.*%s.*%|SELECT.*\.format', "HIGH", "Possible SQL injection", "S011"),
            (r'<script>|javascript:', "HIGH", "Possible XSS vulnerability", "S012"),
            (r'chmod\s+777', "MEDIUM", "Overly permissive file permissions", "S013"),
            (r'verify\s*=\s*False', "MEDIUM", "SSL verification disabled", "S014"),
        ]

        for i, line in enumerate(self.lines, 1):
            for pattern, severity, message, code in security_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.result.add_issue(Issue(
                        severity=severity,
                        category="security",
                        line=i,
                        column=0,
                        message=message,
                        code=code
                    ))

    def _check_logic_errors(self):
        """Check for logic errors."""
        if not self.tree:
            return

        class LogicVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer

            def visit_Compare(self, node):
                # Check for always-true/false comparisons
                for op, comparator in zip(node.ops, node.comparators):
                    if isinstance(node.left, ast.Constant) and isinstance(comparator, ast.Constant):
                        # Both sides are constants
                        self.analyzer.result.add_issue(Issue(
                            severity="MEDIUM",
                            category="logic",
                            line=node.lineno,
                            column=node.col_offset,
                            message="Comparison between two constants",
                            code="L001",
                            suggestion="This comparison result is predetermined"
                        ))

                # Check x == None instead of x is None
                if isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
                    if isinstance(node.comparators[0], ast.Constant) and node.comparators[0].value is None:
                        self.analyzer.result.add_issue(Issue(
                            severity="MEDIUM",
                            category="logic",
                            line=node.lineno,
                            column=node.col_offset,
                            message="Use 'is None' instead of ' is None'",
                            code="L002",
                            suggestion="Replace is None with 'is None'"
                        ))
                self.generic_visit(node)

            def visit_If(self, node):
                # Check for empty if body
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    self.analyzer.result.add_issue(Issue(
                        severity="LOW",
                        category="logic",
                        line=node.lineno,
                        column=node.col_offset,
                        message="Empty if statement",
                        code="L003",
                        suggestion="Add implementation or remove if statement"
                    ))
                self.generic_visit(node)

            def visit_Return(self, node):
                # Check for return after return (unreachable code)
                self.generic_visit(node)

        visitor = LogicVisitor(self)
        visitor.visit(self.tree)

    def _check_common_mistakes(self):
        """Check for common programming mistakes."""
        patterns = [
            (r'except\s*:', "MEDIUM", "Bare except catches all exceptions including KeyboardInterrupt", "M001"),
            (r'except\s+Exception\s*:', "LOW", "Catching all Exception is usually too broad", "M002"),
            (r'\.append\([^)]*\).*=', "HIGH", "list.append() returns None", "M003"),
            (r'\.sort\(\).*=', "HIGH", "list.sort() returns None (sorts in-place)", "M004"),
            (r'if\s+\w+\s*=\s*[^=]', "HIGH", "Assignment in if condition (use ==)", "M005"),
            (r'\[\s*\]\s*\*\s*\d+|\d+\s*\*\s*\[\s*\]', "MEDIUM", "Multiplying list creates shallow copies", "M006"),
            (r'def\s+\w+\([^)]*=\s*\[\s*\]', "HIGH", "Mutable default argument (list)", "M007"),
            (r'def\s+\w+\([^)]*=\s*\{\s*\}', "HIGH", "Mutable default argument (dict)", "M008"),
            (r'def\s+\w+\([^)]*=\s*set\(\)', "HIGH", "Mutable default argument (set)", "M009"),
            (r'global\s+', "MEDIUM", "Global variables make code harder to test", "M010"),
            (r'from\s+\S+\s+import\s+\*', "MEDIUM", "Wildcard import pollutes namespace", "M011"),
            (r'print\s*\(.*\)\s*$', "INFO", "Print statement (consider logging)", "M012"),
            (r'TODO|FIXME|XXX|HACK', "INFO", "TODO/FIXME comment found", "M013"),
        ]

        for i, line in enumerate(self.lines, 1):
            for pattern, severity, message, code in patterns:
                if re.search(pattern, line):
                    self.result.add_issue(Issue(
                        severity=severity,
                        category="common",
                        line=i,
                        column=0,
                        message=message,
                        code=code
                    ))

    def _check_style(self):
        """Check code style issues."""
        patterns = [
            (r'^.{121,}$', "LOW", "Line too long (>120 characters)", "C001"),
            (r'\t', "LOW", "Tab character (use spaces)", "C002"),
            (r'\s+$', "LOW", "Trailing whitespace", "C003"),
            (r'[a-z][A-Z]', "INFO", "Consider snake_case for variables", "C004"),
        ]

        for i, line in enumerate(self.lines, 1):
            for pattern, severity, message, code in patterns:
                if re.search(pattern, line):
                    self.result.add_issue(Issue(
                        severity=severity,
                        category="style",
                        line=i,
                        column=0,
                        message=message,
                        code=code
                    ))

    def _check_complexity(self):
        """Check for overly complex code."""
        if not self.tree:
            return

        class ComplexityVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer
                self.nesting_level = 0
                self.max_nesting = 0

            def visit_FunctionDef(self, node):
                # Count complexity
                complexity = self._calculate_complexity(node)
                if complexity > 10:
                    self.analyzer.result.add_issue(Issue(
                        severity="MEDIUM",
                        category="complexity",
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Function '{node.name}' has high complexity ({complexity})",
                        code="X001",
                        suggestion="Consider breaking into smaller functions"
                    ))

                # Check function length
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    length = node.end_lineno - node.lineno
                    if length > 50:
                        self.analyzer.result.add_issue(Issue(
                            severity="LOW",
                            category="complexity",
                            line=node.lineno,
                            column=node.col_offset,
                            message=f"Function '{node.name}' is too long ({length} lines)",
                            code="X002",
                            suggestion="Consider breaking into smaller functions"
                        ))

                self.generic_visit(node)

            def _calculate_complexity(self, node) -> int:
                """Calculate cyclomatic complexity."""
                complexity = 1
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor,
                                        ast.ExceptHandler, ast.With, ast.AsyncWith,
                                        ast.Assert, ast.comprehension)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1
                return complexity

        visitor = ComplexityVisitor(self)
        visitor.visit(self.tree)

    def _check_increments(self):
        """Check for increment/counter issues."""
        if not self.tree:
            return

        # Look for common increment patterns and potential issues
        class IncrementVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer
                self.manual_counters: list = []  # (var_name, init_line)

            def visit_For(self, node):
                # Detect manual counter alongside for-loop (should use enumerate)
                if isinstance(node.iter, ast.Call):
                    if isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range':
                        # Check range with single arg — range(len(...)) anti-pattern
                        if len(node.iter.args) == 1:
                            arg = node.iter.args[0]
                            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == 'len':
                                self.analyzer.add_issue(Issue(
                                    severity="LOW",
                                    category="increment",
                                    line=node.lineno,
                                    column=0,
                                    message="range(len(...)) pattern — consider using enumerate() instead",
                                    code="I001",
                                    suggestion="Use 'for i, item in enumerate(collection):' instead"
                                ))

                # Detect manual counter increment inside for body
                for child in ast.walk(node):
                    if isinstance(child, ast.AugAssign) and isinstance(child.op, ast.Add):
                        if isinstance(child.target, ast.Name) and isinstance(child.value, ast.Constant):
                            if child.value.value == 1:
                                self.manual_counters.append((child.target.id, child.lineno))
                self.generic_visit(node)

            def visit_While(self, node):
                # Check while loops for missing increment (infinite loop risk)
                has_break = False
                has_increment = False
                for child in ast.walk(node):
                    if isinstance(child, ast.Break):
                        has_break = True
                    if isinstance(child, ast.AugAssign):
                        has_increment = True
                if not has_break and not has_increment and not isinstance(node.test, ast.Constant):
                    self.analyzer.add_issue(Issue(
                        severity="MEDIUM",
                        category="increment",
                        line=node.lineno,
                        column=0,
                        message="While loop without break or counter increment — potential infinite loop",
                        code="I002",
                        suggestion="Ensure loop has a termination condition (break, counter, or return)"
                    ))
                self.generic_visit(node)

            def visit_AugAssign(self, node):
                self.generic_visit(node)

            def visit_Subscript(self, node):
                # Check for arr[i-1] at start of loop (off-by-one risk)
                if isinstance(node.slice, ast.BinOp):
                    if isinstance(node.slice.op, ast.Sub):
                        if isinstance(node.slice.right, ast.Constant) and node.slice.right.value == 1:
                            self.analyzer.add_issue(Issue(
                                severity="INFO",
                                category="increment",
                                line=node.lineno,
                                column=0,
                                message="Index subtraction pattern (arr[i-1]) — verify no off-by-one when i=0",
                                code="I003",
                                suggestion="Ensure 'i' is never 0 when accessing arr[i-1]"
                            ))
                self.generic_visit(node)

        visitor = IncrementVisitor(self)
        visitor.visit(self.tree)

    def _check_error_handling(self):
        """Check error handling quality."""
        if not self.tree:
            return

        class ErrorVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer
                self.in_try = False

            def visit_Try(self, node):
                self.in_try = True

                # Check for empty except
                for handler in node.handlers:
                    if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                        self.analyzer.result.add_issue(Issue(
                            severity="HIGH",
                            category="error_handling",
                            line=handler.lineno,
                            column=handler.col_offset,
                            message="Empty except block swallows errors",
                            code="H001",
                            suggestion="Log the error or re-raise"
                        ))

                self.generic_visit(node)
                self.in_try = False

            def visit_Raise(self, node):
                # Check for raise without exception in except block
                if node.exc is None and not self.in_try:
                    self.analyzer.result.add_issue(Issue(
                        severity="MEDIUM",
                        category="error_handling",
                        line=node.lineno,
                        column=node.col_offset,
                        message="Bare raise outside exception handler",
                        code="H002"
                    ))
                self.generic_visit(node)

        visitor = ErrorVisitor(self)
        visitor.visit(self.tree)

    def _check_type_hints(self):
        """Check type hint consistency."""
        if not self.tree:
            return

        class TypeVisitor(ast.NodeVisitor):
            def __init__(self, analyzer):
                self.analyzer = analyzer

            def visit_FunctionDef(self, node):
                # Check if some args have hints and some don't
                has_hints = [arg.annotation is not None for arg in node.args.args]
                if any(has_hints) and not all(has_hints):
                    self.analyzer.result.add_issue(Issue(
                        severity="LOW",
                        category="types",
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Inconsistent type hints in '{node.name}'",
                        code="T001",
                        suggestion="Add type hints to all parameters or none"
                    ))

                # Check for return type hint if args have hints
                if any(has_hints) and node.returns is None:
                    self.analyzer.result.add_issue(Issue(
                        severity="LOW",
                        category="types",
                        line=node.lineno,
                        column=node.col_offset,
                        message=f"Missing return type hint in '{node.name}'",
                        code="T002",
                        suggestion="Add return type hint"
                    ))

                self.generic_visit(node)

        visitor = TypeVisitor(self)
        visitor.visit(self.tree)


class JavaScriptAnalyzer:
    """Basic JavaScript code analyzer."""

    def __init__(self, code: str, file_path: str = "<string>"):
        self.code = code
        self.file_path = file_path
        self.lines = code.split('\n')
        self.result = ReviewResult(file_path=file_path, language="javascript")

    def analyze(self) -> ReviewResult:
        """Run JavaScript checks."""
        self._check_syntax_basic()
        self._check_security()
        self._check_common_mistakes()
        self._check_style()
        return self.result

    def _check_syntax_basic(self):
        """Basic syntax checks."""
        # Check for unbalanced brackets
        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []
        for i, line in enumerate(self.lines, 1):
            for j, char in enumerate(line):
                if char in brackets:
                    stack.append((char, i, j))
                elif char in brackets.values():
                    if not stack:
                        self.result.add_issue(Issue(
                            severity="CRITICAL",
                            category="syntax",
                            line=i,
                            column=j,
                            message=f"Unmatched closing bracket '{char}'",
                            code="E001"
                        ))
                    else:
                        open_bracket, _, _ = stack.pop()
                        if brackets[open_bracket] != char:
                            self.result.add_issue(Issue(
                                severity="CRITICAL",
                                category="syntax",
                                line=i,
                                column=j,
                                message=f"Mismatched brackets: expected '{brackets[open_bracket]}', got '{char}'",
                                code="E002"
                            ))

    def _check_security(self):
        """Check security issues."""
        patterns = [
            (r'eval\s*\(', "CRITICAL", "Use of eval() is dangerous", "S001"),
            (r'innerHTML\s*=', "HIGH", "innerHTML can lead to XSS", "S002"),
            (r'document\.write', "HIGH", "document.write is dangerous", "S003"),
            (r'password\s*[=:]\s*["\'][^"\']+["\']', "CRITICAL", "Hardcoded password", "S004"),
            (r'api[_-]?key\s*[=:]\s*["\'][^"\']+["\']', "CRITICAL", "Hardcoded API key", "S005"),
        ]

        for i, line in enumerate(self.lines, 1):
            for pattern, severity, message, code in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.result.add_issue(Issue(
                        severity=severity,
                        category="security",
                        line=i,
                        column=0,
                        message=message,
                        code=code
                    ))

    def _check_common_mistakes(self):
        """Check common mistakes."""
        patterns = [
            (r'==\s*null|null\s*==', "MEDIUM", "Use === for strict equality", "M001"),
            (r'==\s*undefined|undefined\s*==', "MEDIUM", "Use === for strict equality", "M002"),
            (r'console\.log', "INFO", "Console.log found (remove in production)", "M003"),
            (r'debugger', "HIGH", "Debugger statement found", "M004"),
            (r'TODO|FIXME|XXX', "INFO", "TODO comment found", "M005"),
        ]

        for i, line in enumerate(self.lines, 1):
            for pattern, severity, message, code in patterns:
                if re.search(pattern, line):
                    self.result.add_issue(Issue(
                        severity=severity,
                        category="common",
                        line=i,
                        column=0,
                        message=message,
                        code=code
                    ))

    def _check_style(self):
        """Check style issues."""
        patterns = [
            (r'^.{121,}$', "LOW", "Line too long (>120 characters)", "C001"),
            (r'var\s+', "MEDIUM", "Use let/const instead of var", "C002"),
        ]

        for i, line in enumerate(self.lines, 1):
            for pattern, severity, message, code in patterns:
                if re.search(pattern, line):
                    self.result.add_issue(Issue(
                        severity=severity,
                        category="style",
                        line=i,
                        column=0,
                        message=message,
                        code=code
                    ))


class BashAnalyzer:
    """Basic Bash script analyzer."""

    def __init__(self, code: str, file_path: str = "<string>"):
        self.code = code
        self.file_path = file_path
        self.lines = code.split('\n')
        self.result = ReviewResult(file_path=file_path, language="bash")

    def analyze(self) -> ReviewResult:
        """Run Bash checks."""
        self._check_security()
        self._check_common_mistakes()
        self._check_style()
        return self.result

    def _check_security(self):
        """Check security issues."""
        patterns = [
            (r'eval\s+', "HIGH", "eval in bash is dangerous", "S001"),
            (r'\$\([^)]*\$\{?[a-zA-Z]', "MEDIUM", "Unquoted variable in command substitution", "S002"),
            (r'curl.*\|\s*bash|wget.*\|\s*bash', "CRITICAL", "Piping to bash is dangerous", "S003"),
            (r'chmod\s+777', "HIGH", "Overly permissive permissions", "S004"),
            (r'rm\s+-rf\s+/', "CRITICAL", "Dangerous rm command", "S005"),
        ]

        for i, line in enumerate(self.lines, 1):
            for pattern, severity, message, code in patterns:
                if re.search(pattern, line):
                    self.result.add_issue(Issue(
                        severity=severity,
                        category="security",
                        line=i,
                        column=0,
                        message=message,
                        code=code
                    ))

    def _check_common_mistakes(self):
        """Check common mistakes."""
        patterns = [
            (r'\[\s+[^]]+\s+\]', "INFO", "Consider using [[ ]] for tests", "M001"),
            (r'\$[a-zA-Z_][a-zA-Z0-9_]*[^"]', "MEDIUM", "Unquoted variable (use \"$var\")", "M002"),
            (r'`[^`]+`', "LOW", "Use $() instead of backticks", "M003"),
        ]

        for i, line in enumerate(self.lines, 1):
            for pattern, severity, message, code in patterns:
                if re.search(pattern, line):
                    self.result.add_issue(Issue(
                        severity=severity,
                        category="common",
                        line=i,
                        column=0,
                        message=message,
                        code=code
                    ))

    def _check_style(self):
        """Check style issues."""
        # Check for shebang
        if self.lines and not self.lines[0].startswith('#!'):
            self.result.add_issue(Issue(
                severity="LOW",
                category="style",
                line=1,
                column=0,
                message="Missing shebang (#!/bin/bash)",
                code="C001"
            ))


def detect_language(code: str, file_path: str = "") -> str:
    """Detect programming language from code or file extension."""
    if file_path:
        ext = Path(file_path).suffix.lower()
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.sh': 'bash',
            '.bash': 'bash',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
        }
        if ext in ext_map:
            return ext_map[ext]

    # Detect from content
    if re.search(r'^#!/.*python|^from\s+|^import\s+|^def\s+|^class\s+', code, re.MULTILINE):
        return 'python'
    if re.search(r'^#!/.*bash|^#!/.*sh', code):
        return 'bash'
    if re.search(r'const\s+|let\s+|var\s+|function\s+|=>\s*{', code):
        return 'javascript'

    return 'unknown'


def analyze_code(code: str, file_path: str = "<string>") -> ReviewResult:
    """Analyze code and return review result."""
    language = detect_language(code, file_path)

    if language == 'python':
        analyzer = PythonAnalyzer(code, file_path)
    elif language in ('javascript', 'typescript'):
        analyzer = JavaScriptAnalyzer(code, file_path)
    elif language == 'bash':
        analyzer = BashAnalyzer(code, file_path)
    else:
        # Return empty result for unknown languages
        return ReviewResult(file_path=file_path, language=language)

    return analyzer.analyze()


def format_result(result: ReviewResult, verbose: bool = False) -> str:
    """Format review result for display."""
    lines = []

    # Header
    lines.append(f"{'='*60}")
    lines.append(f"CODE REVIEW: {result.file_path}")
    lines.append(f"Language: {result.language}")
    lines.append(f"{'='*60}")

    # Summary
    if result.summary:
        lines.append("\n## SUMMARY")
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
            if severity in result.summary:
                count = result.summary[severity]
                emoji = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '🟢', 'INFO': '⚪'}[severity]
                lines.append(f"  {emoji} {severity}: {count}")

    # Pass/Fail
    if result.passed:
        lines.append("\n✅ PASSED - No critical or high severity issues")
    else:
        lines.append("\n❌ FAILED - Critical or high severity issues found")

    # Issues
    if result.issues:
        lines.append("\n## ISSUES")

        # Group by severity
        by_severity = defaultdict(list)
        for issue in result.issues:
            by_severity[issue.severity].append(issue)

        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
            if severity in by_severity:
                lines.append(f"\n### {severity}")
                for issue in by_severity[severity]:
                    lines.append(f"  [{issue.code}] Line {issue.line}: {issue.message}")
                    if verbose and issue.suggestion:
                        lines.append(f"         → {issue.suggestion}")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Comprehensive code review checks")
    parser.add_argument('--file', '-f', help="File to analyze")
    parser.add_argument('--code', '-c', help="Code string to analyze")
    parser.add_argument('--dir', '-d', help="Directory to analyze")
    parser.add_argument('--verbose', '-v', action='store_true', help="Show suggestions")
    parser.add_argument('--json', action='store_true', help="Output as JSON")
    parser.add_argument('--strict', action='store_true', help="Fail on any issue")

    args = parser.parse_args()

    results = []

    if args.code:
        result = analyze_code(args.code)
        results.append(result)

    elif args.file:
        path = Path(args.file)
        if path.exists():
            code = path.read_text()
            result = analyze_code(code, str(path))
            results.append(result)
        else:
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)

    elif args.dir:
        dir_path = Path(args.dir)
        if dir_path.exists():
            for ext in ['*.py', '*.js', '*.ts', '*.sh']:
                for file_path in dir_path.rglob(ext):
                    if '.venv' in str(file_path) or 'node_modules' in str(file_path):
                        continue
                    code = file_path.read_text()
                    result = analyze_code(code, str(file_path))
                    results.append(result)
        else:
            print(f"Error: Directory not found: {args.dir}", file=sys.stderr)
            sys.exit(1)

    else:
        # Read from stdin
        code = sys.stdin.read()
        result = analyze_code(code)
        results.append(result)

    # Output
    if args.json:
        output = [asdict(r) for r in results]
        print(json.dumps(output, indent=2, default=str))
    else:
        for result in results:
            print(format_result(result, args.verbose))
            print()

    # Exit code
    if args.strict:
        if any(r.issues for r in results):
            sys.exit(1)
    else:
        if any(not r.passed for r in results):
            sys.exit(1)


if __name__ == "__main__":
    main()
