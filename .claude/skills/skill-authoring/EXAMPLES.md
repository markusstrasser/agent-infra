# Complete Skill Examples

Real-world, production-ready skill examples demonstrating best practices.

## Example 1: Commit Message Generator (Simple)

**File**: `commit-helper/SKILL.md`

````markdown
---
name: commit-helper
description: Generate conventional commit messages from git diffs. Use when writing commits, reviewing staged changes, or running git commit workflow.
---

# Commit Message Generator

## Instructions

1. Run `git diff --staged` to see changes
2. Analyze the diff for:
   - Type of change: feat, fix, docs, refactor, test, chore, style
   - Scope: affected component/module
   - Breaking changes
   - Related issues

3. Generate commit message following conventional commits format:
   ```
   type(scope): subject line (max 50 chars)

   Body with detailed explanation (wrap at 72 chars)
   - What changed
   - Why it changed
   - Any breaking changes

   Footer:
   BREAKING CHANGE: description
   Closes #123
   ```

## Commit Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, missing semicolons)
- `refactor`: Neither fixes bug nor adds feature
- `perf`: Performance improvement
- `test`: Adding missing tests
- `chore`: Build process or auxiliary tool changes

## Examples

### Feature Addition
```
feat(auth): add OAuth2 Google provider

Implement OAuth2 authentication flow with Google provider.
Includes token refresh, session management, and user profile sync.

Closes #156
```

### Bug Fix
```
fix(api): prevent race condition in cache

Add mutex lock to cache operations to prevent concurrent
write conflicts. This fixes intermittent 500 errors during
high load.

Fixes #234
```

### Breaking Change
```
feat(api): migrate to v2 response format

BREAKING CHANGE: API responses now use camelCase instead
of snake_case. Client applications must update their
parsers.

Migration guide: docs/migration-v2.md
```

## Best Practices

1. **Subject line**:
   - Use imperative mood ("add" not "added")
   - No period at the end
   - Max 50 characters

2. **Body**:
   - Separate from subject with blank line
   - Wrap at 72 characters
   - Explain what and why, not how

3. **Footer**:
   - Reference issues: "Closes #123" or "Fixes #234"
   - Note breaking changes: "BREAKING CHANGE: ..."
````

---

## Example 2: PDF Processing (Multi-File)

**File**: `pdf-processing/SKILL.md`

````markdown
---
name: pdf-processing
description: Extract text, fill forms, merge PDFs, add watermarks. Use when working with PDF files, forms, or document processing. Requires pypdf and pdfplumber packages.
---

# PDF Processing

## Quick Start

Extract text from PDF:
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    # Extract from first page
    text = pdf.pages[0].extract_text()
    print(text)

    # Extract from all pages
    full_text = ""
    for page in pdf.pages:
        full_text += page.extract_text()
```

## Installation

```bash
pip install pypdf pdfplumber
```

## Core Capabilities

1. **Text Extraction**: Extract text and tables
2. **Form Filling**: Fill interactive PDF forms
3. **Document Merging**: Combine multiple PDFs
4. **Watermarking**: Add text or image watermarks
5. **Metadata**: Read and update PDF metadata

## Documentation

- **Form Filling**: See [FORMS.md](FORMS.md) for detailed form workflows
- **API Reference**: See [REFERENCE.md](REFERENCE.md) for complete API
- **Advanced Examples**: See [ADVANCED.md](ADVANCED.md) for complex use cases

## Common Tasks

### Extract Tables
```python
import pdfplumber

with pdfplumber.open("report.pdf") as pdf:
    page = pdf.pages[0]
    tables = page.extract_tables()
    for table in tables:
        for row in table:
            print(row)
```

### Merge PDFs
```python
from pypdf import PdfMerger

merger = PdfMerger()
merger.append("file1.pdf")
merger.append("file2.pdf")
merger.write("merged.pdf")
merger.close()
```

### Extract by Page Range
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    # Pages 5-10
    text = ""
    for page_num in range(4, 10):  # 0-indexed
        text += pdf.pages[page_num].extract_text()
```

## Error Handling

Common issues:
- **File not found**: Check path is correct and file exists
- **Permission denied**: Ensure read permissions on file
- **Encrypted PDF**: Use `pypdf` to decrypt first:
  ```python
  from pypdf import PdfReader
  reader = PdfReader("encrypted.pdf")
  reader.decrypt("password")
  ```
- **No text extracted**: PDF might be scanned images (use OCR)

## Best Practices

1. Always use context managers (`with` statements)
2. Handle exceptions for file operations
3. Close files explicitly if not using `with`
4. Validate extracted text is not empty
5. Test with various PDF versions and formats
````

**File**: `pdf-processing/FORMS.md`

````markdown
# PDF Form Filling

Detailed guide for working with interactive PDF forms.

## Form Field Discovery

List all form fields:
```python
from pypdf import PdfReader

reader = PdfReader("form.pdf")
fields = reader.get_form_text_fields()

for field_name in fields:
    print(f"Field: {field_name}")
```

## Fill Form Fields

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("form.pdf")
writer = PdfWriter()

# Clone pages
writer.append_pages_from_reader(reader)

# Fill fields
writer.update_page_form_field_values(
    writer.pages[0],
    {
        "name": "John Doe",
        "email": "john@example.com",
        "date": "2025-11-09"
    }
)

# Save filled form
with open("filled_form.pdf", "wb") as output:
    writer.write(output)
```

## Field Types

### Text Fields
```python
{
    "field_name": "Plain text value"
}
```

### Checkboxes
```python
{
    "checkbox_field": "/Yes"  # or "/Off"
}
```

### Radio Buttons
```python
{
    "radio_group": "/Option1"  # or "/Option2", etc.
}
```

### Dropdown Lists
```python
{
    "dropdown_field": "Selected Option"
}
```

## Validation

Validate form data before filling:
```python
def validate_form_data(fields, data):
    """Validate all required fields are present"""
    required = {k for k, v in fields.items() if v.get('required')}
    missing = required - set(data.keys())

    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    return True

# Use
try:
    validate_form_data(fields, user_data)
    # Proceed with filling
except ValueError as e:
    print(f"Validation error: {e}")
```

## Flatten Forms

Convert form to static content:
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("filled_form.pdf")
writer = PdfWriter()

for page in reader.pages:
    writer.add_page(page)

# Flatten by removing form fields
writer.flatten()

with open("flattened.pdf", "wb") as output:
    writer.write(output)
```

## Complete Workflow Example

```python
import sys
from pypdf import PdfReader, PdfWriter

def fill_application_form(template_path, data, output_path):
    """Fill job application form with validation"""

    # Read template
    reader = PdfReader(template_path)

    # Get all fields
    fields = reader.get_form_text_fields()
    print(f"Found {len(fields)} form fields")

    # Validate required fields
    required_fields = ['name', 'email', 'phone', 'position']
    missing = [f for f in required_fields if f not in data]

    if missing:
        raise ValueError(f"Missing required: {', '.join(missing)}")

    # Create writer
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)

    # Fill first page (assuming single-page form)
    writer.update_page_form_field_values(
        writer.pages[0],
        data
    )

    # Save filled form
    with open(output_path, "wb") as output:
        writer.write(output)

    print(f"Filled form saved to: {output_path}")
    return output_path

# Usage
try:
    applicant_data = {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "phone": "(555) 123-4567",
        "position": "Senior Engineer",
        "experience": "10 years",
        "availability": "Immediate"
    }

    fill_application_form(
        "templates/application.pdf",
        applicant_data,
        "output/jane_smith_application.pdf"
    )
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
```
````

---

## Example 3: Code Security Auditor (Read-Only)

**File**: `security-auditor/SKILL.md`

````markdown
---
name: security-auditor
description: Audit code for security vulnerabilities, OWASP top 10 issues, and security best practices. Read-only analysis. Use for security review, vulnerability scanning, code audit.
allowed-tools: Read, Grep, Glob
---

# Security Auditor

Read-only security analysis tool for finding vulnerabilities and security issues.

## Security Checklist

### 1. Authentication & Authorization
- [ ] Passwords hashed with bcrypt/argon2
- [ ] No hardcoded credentials
- [ ] Session management secure
- [ ] Proper access control
- [ ] MFA support where needed

### 2. Input Validation
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] Command injection prevention
- [ ] Path traversal protection
- [ ] Input sanitization

### 3. Data Protection
- [ ] Encryption at rest (sensitive data)
- [ ] TLS/HTTPS for transit
- [ ] No sensitive data in logs
- [ ] Secure random number generation
- [ ] PII handling compliance

### 4. Dependencies
- [ ] No known vulnerabilities
- [ ] Up-to-date packages
- [ ] Dependency scanning enabled
- [ ] License compliance

### 5. Configuration
- [ ] Security headers present
- [ ] CORS properly configured
- [ ] Error messages don't leak info
- [ ] Debug mode disabled in prod

## Analysis Process

### 1. Discovery Phase

Find relevant files:
```bash
# Source code
**/*.py
**/*.js
**/*.java
**/*.rb
**/*.php

# Configuration
**/*.yaml
**/*.json
**/.env
**/config/*

# Dependencies
**/package.json
**/requirements.txt
**/Gemfile
**/pom.xml
```

### 2. Pattern Matching

Search for security anti-patterns:

**Credentials**:
```regex
password\s*=\s*["']
api_key\s*=\s*["']
secret\s*=\s*["']
token\s*=\s*["']
```

**Dangerous Functions**:
```regex
eval\s*\(
exec\s*\(
system\s*\(
__.import__
```

**SQL Injection**:
```regex
execute\s*\(\s*["'].*%s
execute\s*\(\s*f["'].*{
\.raw\s*\(
```

**XSS Vulnerabilities**:
```regex
innerHTML\s*=
dangerouslySetInnerHTML
v-html\s*=
```

### 3. Manual Review

Read and analyze:
- Authentication implementation
- Authorization logic
- Input validation
- Cryptographic usage
- Error handling

### 4. Report Generation

Use standard format (see below).

## Report Format

```markdown
# Security Audit Report

**Project**: [name]
**Date**: [date]
**Auditor**: Claude Security Auditor

## Executive Summary

- Files Scanned: [count]
- Critical Issues: [count]
- High Priority: [count]
- Medium Priority: [count]
- Low Priority: [count]

**Overall Risk**: [Critical/High/Medium/Low]

## Critical Issues

### 1. [Issue Title]

**Location**: `path/to/file.py:42`

**Description**:
Hardcoded database password found in configuration file.

**Code**:
```python
DB_PASSWORD = "super_secret_123"
```

**Impact**:
- Credentials exposed in version control
- Unauthorized database access possible
- Compliance violation (PCI-DSS, GDPR)

**Recommendation**:
```python
# Use environment variables
import os
DB_PASSWORD = os.environ.get('DB_PASSWORD')

# Or use secret management
from secretmanager import get_secret
DB_PASSWORD = get_secret('prod/db/password')
```

**Severity**: Critical
**CVSS Score**: 9.8
**CWE**: CWE-798 (Hardcoded Credentials)

## High Priority

[Same format for high priority issues]

## Medium Priority

[Same format for medium priority issues]

## Low Priority

[Same format for low priority issues]

## Recommendations

### Immediate Actions
1. [Action 1]
2. [Action 2]

### Short-term Improvements
1. [Action 1]
2. [Action 2]

### Long-term Strategy
1. [Action 1]
2. [Action 2]

## Dependencies

### Vulnerable Packages

| Package | Current | Fixed In | Severity | CVE |
|---------|---------|----------|----------|-----|
| requests | 2.25.0 | 2.31.0 | High | CVE-2023-32681 |

## Compliance

- **OWASP Top 10**: [Pass/Fail for each]
- **CWE Top 25**: [Status]
- **PCI-DSS**: [Applicable requirements]
- **GDPR**: [Data protection requirements]

## Next Steps

1. Address all Critical issues immediately
2. Schedule fixes for High priority items
3. Plan remediation for Medium/Low items
4. Implement automated security scanning
5. Schedule follow-up audit
```

## Examples

### Example 1: Web Application Audit

**Scope**: Python Flask application

**Findings**:
- 2 Critical: Hardcoded secrets, SQL injection
- 4 High: Missing input validation, weak crypto
- 8 Medium: Missing security headers
- 12 Low: Code quality improvements

**Time**: ~30 minutes for 5000 LOC

### Example 2: API Security Review

**Scope**: Node.js Express REST API

**Findings**:
- 0 Critical
- 2 High: JWT verification bypass, rate limiting missing
- 5 Medium: CORS misconfiguration
- 3 Low: Dependency updates

**Time**: ~20 minutes for 2000 LOC

## Severity Levels

**Critical**:
- Hardcoded credentials
- SQL injection
- Remote code execution
- Authentication bypass

**High**:
- XSS vulnerabilities
- Weak cryptography
- Broken access control
- Sensitive data exposure

**Medium**:
- Missing security headers
- CSRF protection missing
- Information disclosure
- Outdated dependencies

**Low**:
- Code quality issues
- Minor configuration improvements
- Non-critical warnings
- Best practice violations

## Best Practices

1. **Run regularly**: Weekly or on major changes
2. **Combine with tools**: SonarQube, Snyk, etc.
3. **Track issues**: Use issue tracker
4. **Verify fixes**: Re-audit after remediation
5. **Educate team**: Share findings and best practices

## Limitations

This is a **static analysis** tool. It cannot detect:
- Runtime vulnerabilities
- Business logic flaws
- Advanced attack scenarios
- Zero-day exploits

Always combine with:
- Dynamic application security testing (DAST)
- Penetration testing
- Security code review
- Threat modeling
````

---

## Example 4: API Integration Helper (Multi-File)

**File**: `api-integration/SKILL.md`

````markdown
---
name: api-integration
description: Integrate with REST APIs including authentication, error handling, retry logic, rate limiting. Use when connecting to external APIs, web services, or building HTTP clients.
---

# API Integration Helper

## Quick Start

Basic API request with error handling:
```python
import requests
from requests.exceptions import RequestException, Timeout

def fetch_data(api_url, api_key):
    try:
        response = requests.get(
            api_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Timeout:
        print("Request timed out")
    except RequestException as e:
        print(f"API error: {e}")
        return None
```

## Installation

```bash
# Python
pip install requests requests-ratelimit

# Node.js
npm install axios axios-retry p-retry

# Go
go get github.com/go-resty/resty/v2
```

## Documentation Structure

- **Quick Start**: This file (basic examples)
- **Authentication**: [AUTH.md](AUTH.md) (OAuth, JWT, API keys)
- **Error Handling**: [ERRORS.md](ERRORS.md) (retries, fallbacks)
- **Rate Limiting**: [RATE_LIMITS.md](RATE_LIMITS.md) (strategies, backoff)
- **Testing**: [TESTING.md](TESTING.md) (mocking, integration tests)
- **Examples**: [EXAMPLES.md](EXAMPLES.md) (real API integrations)

## Common Patterns

### GET Request
```python
response = requests.get(
    f"{base_url}/users/{user_id}",
    headers=headers,
    timeout=10
)
```

### POST Request
```python
response = requests.post(
    f"{base_url}/users",
    json={"name": "John", "email": "john@example.com"},
    headers=headers,
    timeout=10
)
```

### Pagination
```python
def fetch_all_pages(base_url, headers):
    page = 1
    all_data = []

    while True:
        response = requests.get(
            f"{base_url}/items?page={page}&per_page=100",
            headers=headers
        )
        data = response.json()

        if not data['items']:
            break

        all_data.extend(data['items'])
        page += 1

    return all_data
```

## Best Practices

1. **Always set timeouts**: Prevent hanging requests
2. **Handle errors gracefully**: Don't crash on API failures
3. **Implement retries**: Transient failures are common
4. **Respect rate limits**: Use backoff strategies
5. **Log requests**: Aid debugging
6. **Validate responses**: Check status and data structure
7. **Use connection pooling**: Reuse HTTP connections
8. **Secure credentials**: Never hardcode API keys

## Quick Reference

| Task | See Document |
|------|--------------|
| OAuth 2.0 flow | [AUTH.md](AUTH.md#oauth2) |
| API key auth | [AUTH.md](AUTH.md#api-keys) |
| Retry logic | [ERRORS.md](ERRORS.md#retries) |
| Rate limiting | [RATE_LIMITS.md](RATE_LIMITS.md) |
| Mock testing | [TESTING.md](TESTING.md#mocking) |
| Stripe API | [EXAMPLES.md](EXAMPLES.md#stripe) |
| GitHub API | [EXAMPLES.md](EXAMPLES.md#github) |
````

---

## Key Patterns Demonstrated

1. **Simple skill**: Commit helper - single file, focused purpose
2. **Multi-file skill**: PDF processing - progressive disclosure
3. **Read-only skill**: Security auditor - restricted tools
4. **Reference skill**: API integration - extensive documentation

## Usage Tips

- Start with simple examples
- Add complexity only when needed
- Test each example thoroughly
- Keep examples self-contained
- Update as APIs change
