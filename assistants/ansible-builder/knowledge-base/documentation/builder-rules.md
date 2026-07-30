## Ansible Builder Assistant Rules

### Naming Conventions
- Playbooks: Use the format '[category]-[function]-playbook.yml'
  e.g., network-configuration-playbook.yml
- Roles: Should be named after the primary function, e.g., 'webserver', 'database'.
- Variables: In lowercase with underscores, e.g., 'db_host', 'api_endpoint'.

### Expected Outcomes
- Efficient navigation of Ansible collections and roles
- Clear explanations and guidance on existing playbooks
- Well-structured playbook specifications from user inputs
- High-quality, production-ready playbooks
- Thoroughly reviewed playbooks focusing on security and performance

### Workflows
1. **Playbook Advisor Workflow**
   - Load playbook from 'knowledge-base/playbook-collection'
   - Explain structure and purpose
   - Advise on best practices

2. **Spec Generator Workflow**
   - Collect requirements
   - Map to existing playbooks (if applicable)
   - Create and review specification in YAML

3. **Playbook Writer Workflow**
   - Draft playbook from specification
   - Use role templates and style guides
   - Validate syntax and structure

4. **Reviewer Workflow**
   - Lint and analyze playbook
   - Perform security checks and optimizations
   - Provide comprehensive feedback
