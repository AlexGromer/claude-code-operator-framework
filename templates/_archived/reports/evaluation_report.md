---
title: Evaluation Report
type: evaluation
generated: {{timestamp}}
session_id: {{session_id}}
evaluation_type: {{evaluation_type}}
score: {{overall_score}}
---

# Evaluation Report: {{evaluation_name}}

**Type:** {{evaluation_type}}
**Generated:** {{timestamp}}
**Session:** `{{session_id}}`
**Overall Score:** {{overall_score}}/100

## Executive Summary

{{executive_summary}}

## Evaluation Criteria

| Criterion | Weight | Score | Status |
|-----------|--------|-------|--------|
{{#each criteria}}
| {{this.name}} | {{this.weight}}% | {{this.score}}/100 | {{this.status_icon}} |
{{/each}}

## Detailed Results

{{#each criteria}}
### {{this.name}} ({{this.score}}/100)

**Description:** {{this.description}}

**Findings:**
{{#each this.findings}}
- {{this.severity_icon}} {{this.message}}
{{/each}}

**Recommendations:**
{{#each this.recommendations}}
- {{this}}
{{/each}}

---

{{/each}}

## Metrics Summary

### Performance Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
{{#each performance_metrics}}
| {{this.name}} | {{this.value}} | {{this.target}} | {{this.status_icon}} |
{{/each}}

### Quality Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
{{#each quality_metrics}}
| {{this.name}} | {{this.value}} | {{this.target}} | {{this.status_icon}} |
{{/each}}

## Issues Detected

{{#critical_issues}}
### 🔴 Critical Issues

{{#each critical_issues}}
{{@index}}. **{{this.title}}**
   - Location: `{{this.location}}`
   - Impact: {{this.impact}}
   - Fix: {{this.suggested_fix}}
{{/each}}
{{/critical_issues}}

{{#high_issues}}
### 🟠 High Priority Issues

{{#each high_issues}}
{{@index}}. **{{this.title}}**
   - Location: `{{this.location}}`
   - Fix: {{this.suggested_fix}}
{{/each}}
{{/high_issues}}

{{#medium_issues}}
### 🟡 Medium Priority Issues

{{#each medium_issues}}
{{@index}}. {{this.title}} (`{{this.location}}`)
{{/each}}
{{/medium_issues}}

## Test Coverage

**Overall Coverage:** {{test_coverage.overall}}%

| Module | Coverage | Lines Covered | Lines Total |
|--------|----------|---------------|-------------|
{{#each test_coverage.by_module}}
| `{{this.name}}` | {{this.percentage}}% | {{this.covered}} | {{this.total}} |
{{/each}}

## Recommendations

### Immediate Actions (P1)

{{#each p1_recommendations}}
{{@index}}. {{this}}
{{/each}}

### Short-term Improvements (P2)

{{#each p2_recommendations}}
{{@index}}. {{this}}
{{/each}}

### Long-term Enhancements (P3)

{{#each p3_recommendations}}
{{@index}}. {{this}}
{{/each}}

## Trend Analysis

{{#if has_historical_data}}
**Comparison with Previous Evaluation:**

| Metric | Previous | Current | Change |
|--------|----------|---------|--------|
{{#each trend_data}}
| {{this.name}} | {{this.previous}} | {{this.current}} | {{this.change_icon}} {{this.change}} |
{{/each}}

{{else}}
*No historical data available for trend analysis.*
{{/if}}

## Next Steps

{{#each next_steps}}
{{@index}}. {{this.action}} (Due: {{this.due_date}})
{{/each}}

---

**Evaluated by:** Claude Code Agent
**Evaluation Framework:** {{framework_version}}
**Report Version:** 1.0.0
