## PB-2026-002 — Create application service account and configure limited sudo access

**Input file**: pb-2026-002.txt
**Output file**: pb-2026-002.yml
**Target**: db-prod-01, db-prod-02, db-prod-03 (Red Hat Enterprise Linux 8.9)
**Tasks generated**: 15
**Modules used**: ansible.builtin.group, ansible.builtin.user, ansible.builtin.file, ansible.posix.authorized_key, community.general.sudoers, ansible.builtin.command, ansible.builtin.stat, ansible.builtin.debug
**Assumptions made**:
  - Inventory group name derived from the request title: create_application_service_account_and_configure_limited_sudo_access
  - SSH public key in the request was truncated ("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC7vX..."). The full key should be provided; playbook uses the string as given.
  - Using UID/GID 1500 as requested; if these IDs are already in use on the target systems the task will fail — ensure they are free or change the IDs.
  - Sudoers entry is created in /etc/sudoers.d/appuser_limited_sudo via community.general.sudoers and scoped to only the two specified commands.
  - Passwords are disabled for the local account by setting password: '!'. SSH key authentication is used; ensure SSH daemon allows key-based login for accounts with no password.
**Warnings**:
  - The provided SSH public key appears truncated. Verify and replace with the full public key before running.
  - Ensure the "community.general" collection is installed on the Control Node because the playbook uses community.general.sudoers. Install with: ansible-galaxy collection install community.general
  - If UID/GID 1500 already exist, user/group creation will fail or may produce unexpected results. Verify target systems do not have these IDs in use.
  - This playbook assumes the control user "ansible" can connect to targets and has privilege escalation rights.
