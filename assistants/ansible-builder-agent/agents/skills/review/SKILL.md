---
name: ansible-reviewer
description: Analyze, review, test, and validate Ansible playbooks
---

# Ansible Playbook Reviewer

Thoroughly review Ansible playbooks for correctness, security, performance, and compliance.

## Responsibilities

- Syntax validation and linting
- Security vulnerability scanning
- Best practices review
- Performance analysis
- Testing guidance and verification
- Flaw detection and fix recommendations

## Review Tools

- Scripts: `.agents/skills/ansible-reviewer/scripts/`
  - `lint-playbook.sh` — Run ansible-lint
  - `test-syntax.sh` — Validate YAML syntax
  - `security-check.sh` — Check for security issues

- Checklist: `.agents/skills/ansible-reviewer/resources/review-checklist.md`

## Procedure

1. **Syntax Check**: Validate YAML syntax
2. **Lint**: Run ansible-lint against the playbook
3. **Security Scan**: Check for hardcoded credentials, unsafe modules
4. **Best Practices**: Review against organizational standards
5. **Logic Review**: Verify task flow and error handling
6. **Performance**: Identify optimization opportunities
7. **Documentation**: Check for adequate comments and variable documentation
8. **Testing**: Verify testing approach and coverage
9. **Report**: Provide detailed findings with recommendations
10. **Approve**: Confirm playbook is production-ready

## Verification Checklist

- [ ] YAML syntax is valid
- [ ] No linting errors
- [ ] No hardcoded secrets or credentials
- [ ] Proper error handling
- [ ] Idempotent operations
- [ ] Variables documented
- [ ] Handlers included where needed
- [ ] Tests defined
- [ ] Comments explain complex logic
- [ ] Follows style guide