---
name: ansible-spec-generator
description: Generate Ansible playbook specifications from requirements
---

# Ansible Playbook Specification Generator

Create detailed playbook specifications that serve as blueprints for playbook development.

## Responsibilities

- Interview users about their automation requirements
- Consolidate requirements into a structured specification
- Identify existing playbooks that meet requirements (or parts of them)
- Define playbook structure, roles, and tasks
- Specify variables, handlers, and error handling approach

## Specification Template

Use the template at `.agents/skills/ansible-spec-generator/templates/playbook-spec-template.yaml`.

## Procedure

1. **Gather Requirements**: Ask clarifying questions about:
   - What systems/services will be managed
   - What state should be achieved
   - Dependencies and prerequisites
   - Error handling and rollback needs
   - Testing requirements

2. **Check Existing Playbooks**: Search `knowledge-base/playbook-collection/` for similar patterns

3. **Create Specification**: Generate a spec document including:
   - Playbook name and purpose
   - Target hosts/groups
   - Required roles (new and existing)
   - Variables and defaults
   - Task flow and logic
   - Error handling strategy
   - Testing plan

4. **Validate**: Ensure the spec is complete and achievable

## Output Format

Provide the spec in both Markdown (for review) and YAML (for implementation).