# Skill Templates

Ready-to-use templates for common skill patterns. Copy and customize for your needs.

## Template 1: Simple Tool Skill

For skills that wrap a specific tool or workflow.

````markdown
---
name: tool-name
description: [What it does] using [tool/library]. Use when [trigger scenarios] or mentions of [keywords].
---

# Tool Name

## Quick Start

[Minimal example that works]:
```[language]
# Basic usage
[code example]
```

## Installation

```bash
# Required dependencies
[installation commands]
```

## Common Tasks

### Task 1: [Name]
[Step-by-step instructions]

### Task 2: [Name]
[Step-by-step instructions]

## Examples

### Example 1: [Scenario]
Input: [What user provides]
Output: [What skill produces]
```[language]
[code showing the example]
```

### Example 2: [Scenario]
Input: [What user provides]
Output: [What skill produces]
```[language]
[code showing the example]
```

## Error Handling

Common issues and solutions:
- **[Error]**: [Cause] → [Solution]
- **[Error]**: [Cause] → [Solution]

## Best Practices

1. [Practice 1]
2. [Practice 2]
3. [Practice 3]
````

---

## Template 2: Workflow Skill

For skills that guide through multi-step processes.

````markdown
---
name: workflow-name
description: Guide through [workflow process]. Use when [scenarios] or user needs to [action].
---

# Workflow Name

## Overview

This skill helps you [high-level goal] by:
1. [Step 1 summary]
2. [Step 2 summary]
3. [Step 3 summary]

## Prerequisites

Before starting:
- [ ] [Requirement 1]
- [ ] [Requirement 2]
- [ ] [Requirement 3]

## Workflow Steps

### Step 1: [Name]

**Goal**: [What this step achieves]

**Actions**:
1. [Action 1]
2. [Action 2]
3. [Action 3]

**Validation**: [How to verify step completed correctly]

### Step 2: [Name]

**Goal**: [What this step achieves]

**Actions**:
1. [Action 1]
2. [Action 2]
3. [Action 3]

**Validation**: [How to verify step completed correctly]

### Step 3: [Name]

**Goal**: [What this step achieves]

**Actions**:
1. [Action 1]
2. [Action 2]
3. [Action 3]

**Validation**: [How to verify step completed correctly]

## Completion Checklist

- [ ] [Deliverable 1]
- [ ] [Deliverable 2]
- [ ] [Deliverable 3]
- [ ] [Quality check passed]

## Common Variations

### Variation 1: [Scenario]
[Modified steps or approach]

### Variation 2: [Scenario]
[Modified steps or approach]

## Troubleshooting

**Issue**: [Problem description]
- **Cause**: [Why it happens]
- **Solution**: [How to fix]

**Issue**: [Problem description]
- **Cause**: [Why it happens]
- **Solution**: [How to fix]
````

---

## Template 3: Read-Only Analysis Skill

For skills that analyze code, data, or files without modifications.

````markdown
---
name: analyzer-name
description: Analyze [target] for [purpose]. Read-only. Use for [scenarios] or when reviewing [context].
allowed-tools: Read, Grep, Glob
---

# Analyzer Name

## Analysis Scope

This skill performs [type] analysis on:
- [Item type 1]
- [Item type 2]
- [Item type 3]

## Analysis Checklist

### Category 1: [Name]
- [ ] [Check 1]
- [ ] [Check 2]
- [ ] [Check 3]

### Category 2: [Name]
- [ ] [Check 1]
- [ ] [Check 2]
- [ ] [Check 3]

### Category 3: [Name]
- [ ] [Check 1]
- [ ] [Check 2]
- [ ] [Check 3]

## Analysis Process

1. **Discovery**
   - Use Glob to find: `[pattern]`
   - Filter by: [criteria]

2. **Examination**
   - Use Read to review: [what to read]
   - Look for: [patterns/issues]

3. **Pattern Matching**
   - Use Grep to find: `[regex]`
   - Search for: [keywords/antipatterns]

4. **Reporting**
   - Severity: Critical, High, Medium, Low, Info
   - Include: Location, description, recommendation

## Report Format

```markdown
# Analysis Report: [Target]

## Summary
- Files analyzed: [count]
- Issues found: [count by severity]
- Overall status: [Pass/Warning/Fail]

## Findings

### Critical Issues
1. **[Issue]** (file:line)
   - Description: [details]
   - Impact: [consequences]
   - Recommendation: [fix]

### High Priority
[Same format]

### Medium Priority
[Same format]

## Recommendations
1. [Action item]
2. [Action item]
```

## Examples

### Example 1: [Scenario]
**Target**: [What to analyze]
**Findings**: [What was found]
**Report**: [Link to example report]

### Example 2: [Scenario]
**Target**: [What to analyze]
**Findings**: [What was found]
**Report**: [Link to example report]
````

---

## Template 4: Multi-File Reference Skill

For skills with extensive documentation split across files.

**Main SKILL.md**:
````markdown
---
name: comprehensive-tool
description: [Complete description]. Use when [scenarios]. Supports [capabilities].
---

# Comprehensive Tool

## Quick Start

[Minimal viable example]:
```[language]
[basic code]
```

## Core Capabilities

1. **[Capability 1]**: [Brief description]
2. **[Capability 2]**: [Brief description]
3. **[Capability 3]**: [Brief description]

## Installation

```bash
[installation commands]
```

## Documentation

- **Getting Started**: This file (SKILL.md)
- **API Reference**: [REFERENCE.md](REFERENCE.md)
- **Advanced Examples**: [EXAMPLES.md](EXAMPLES.md)
- **Best Practices**: [BEST_PRACTICES.md](BEST_PRACTICES.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## Common Tasks

### [Task 1]
```[language]
[quick example]
```
See [EXAMPLES.md](EXAMPLES.md) for more.

### [Task 2]
```[language]
[quick example]
```
See [EXAMPLES.md](EXAMPLES.md) for more.
````

**REFERENCE.md**:
````markdown
# API Reference

## Functions

### function_name(arg1, arg2)

**Description**: [What it does]

**Parameters**:
- `arg1` (type): [Description]
- `arg2` (type): [Description]

**Returns**: [Type and description]

**Raises**:
- `ErrorType`: [When and why]

**Example**:
```[language]
[usage example]
```

[Repeat for all functions]
````

**EXAMPLES.md**:
````markdown
# Examples

## Basic Examples

### Example 1: [Scenario]
[Description of what this demonstrates]

```[language]
[complete working code]
```

**Explanation**:
1. [Step 1 explanation]
2. [Step 2 explanation]

**Output**:
```
[expected output]
```

## Advanced Examples

[Same format for complex scenarios]

## Real-World Use Cases

### Use Case 1: [Title]
**Scenario**: [Business/technical context]
**Solution**: [How this skill solves it]
**Code**: [Complete implementation]
````

---

## Template 5: Script-Based Skill

For skills that provide helper scripts.

````markdown
---
name: scripted-workflow
description: Automate [task] with scripts. Use when [scenarios] or mentions of [keywords].
---

# Scripted Workflow

## Scripts Included

- `scripts/setup.sh` - Initial setup and configuration
- `scripts/process.py` - Main processing logic
- `scripts/validate.py` - Validation and checks
- `scripts/cleanup.sh` - Cleanup and finalization

## Usage

### Basic Workflow

```bash
# 1. Setup
bash scripts/setup.sh [config-file]

# 2. Process
python scripts/process.py [input] [output]

# 3. Validate
python scripts/validate.py [output]

# 4. Cleanup
bash scripts/cleanup.sh
```

### Script Details

#### setup.sh

**Purpose**: [What it does]

**Arguments**:
- `config-file`: [Description]

**Example**:
```bash
bash scripts/setup.sh config/prod.yaml
```

#### process.py

**Purpose**: [What it does]

**Arguments**:
- `input`: [Description]
- `output`: [Description]

**Options**:
- `--verbose`: Enable detailed logging
- `--dry-run`: Show what would happen

**Example**:
```bash
python scripts/process.py data/input.csv output/ --verbose
```

## Configuration

Create configuration file:
```yaml
# config.yaml
setting1: value1
setting2: value2
```

See [templates/config.yaml](templates/config.yaml) for full template.

## Error Handling

Scripts will exit with:
- `0`: Success
- `1`: Configuration error
- `2`: Input validation error
- `3`: Processing error
- `4`: Output validation error

Check logs in `logs/` directory for details.
````

---

## Template 6: Git Workflow Skill

For skills that work with git operations.

````markdown
---
name: git-workflow-helper
description: Assist with [git workflow]. Use when [scenarios] or working with git [operations].
---

# Git Workflow Helper

## Supported Workflows

1. **[Workflow 1]**: [Brief description]
2. **[Workflow 2]**: [Brief description]
3. **[Workflow 3]**: [Brief description]

## Instructions

### Workflow 1: [Name]

**When to use**: [Scenario]

**Steps**:
1. Check current status:
   ```bash
   git status
   ```

2. [Next step]:
   ```bash
   [git command]
   ```

3. [Next step]:
   ```bash
   [git command]
   ```

**Validation**:
```bash
[command to verify success]
```

### Workflow 2: [Name]

[Same format]

## Best Practices

1. **Always** [practice 1]
2. **Never** [anti-pattern]
3. **Consider** [tip]

## Safety Checks

Before proceeding, verify:
- [ ] Working directory is clean
- [ ] On correct branch
- [ ] Pushed recent changes
- [ ] Team notified (if needed)

## Examples

### Example 1: [Scenario]
**Context**: [Situation]
**Goal**: [Objective]
**Commands**:
```bash
[complete workflow]
```

## Recovery

### Undo [Operation]
```bash
[recovery commands]
```

### Recover from [Error]
**Symptom**: [What happened]
**Solution**:
```bash
[fix commands]
```
````

---

## Usage Instructions

1. **Choose template** that matches your skill type
2. **Copy template** to new `SKILL.md` file
3. **Replace placeholders** (in [brackets]) with actual content
4. **Remove sections** that don't apply
5. **Test thoroughly** before sharing

## Customization Tips

- **Combine templates**: Mix patterns as needed
- **Add sections**: Include domain-specific information
- **Simplify**: Remove complexity if skill is simple
- **Progressive disclosure**: Move detail to separate files
- **Examples first**: Lead with practical usage

## Next Steps

- Review [EXAMPLES.md](EXAMPLES.md) for complete skill examples
- See [SKILL.md](SKILL.md) for best practices
- Test your skill with realistic queries
