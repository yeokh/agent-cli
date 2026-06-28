# Ansible Playbook Build Summary

## PB-2026-002 — Create application service account and configure limited sudo access

**Input file**: pb-2026-002.txt
**Output file**: pb-2026-002.yml
**Target**: db-prod-01, db-prod-02, db-prod-03 (Red Hat Enterprise Linux 8.9)
**Tasks generated**: 16 tasks (4 configuration + 12 validation/verification)
**Modules used**: ansible.builtin.group, ansible.builtin.user, ansible.builtin.file, ansible.posix.authorized_key, community.general.sudoers, ansible.builtin.getent, ansible.builtin.debug, ansible.builtin.stat, ansible.builtin.assert, ansible.builtin.shell

**Assumptions made**:
  - **Multi-host group name**: Request specifies three hostname entries but no group name. Assumed group name is `db_servers` for inventory configuration. Playbook includes expected inventory block at top for reference.
  - **Connection defaults**: Applied standard SSH connection settings with `ansible_user: ansible` and `become: true` for root privilege escalation via sudo.
  - **SSH key truncation**: The SSH public key in the request is truncated (`...`). Full key must be provided in the `app_ssh_public_key` variable before execution.
  - **Idempotency approach**: Used Ansible module defaults (state: present) to ensure all tasks are idempotent. sudoers entries use community.general.sudoers with validate: true for safety.

**Warnings**:
  - **SSH public key incomplete**: The SSH public key provided in the request appears truncated. Before running, replace the full key value in the `app_ssh_public_key` variable with the complete SSH public key string.
  - **Sudoers file validation**: The playbook uses `community.general.sudoers` which is the safest method, but requires the `python3-apt` or similar packages on the target. Ensure your target systems have the prerequisites for community modules.
  - **Manual inventory required**: Playbook assumes inventory entry under `[db_servers]` group. Configure ansible inventory file with the three hosts and their IPs before execution.
  - **Pre-execution checklist**:
    1. Add the three hosts to inventory under `[db_servers]` group
    2. Replace the truncated SSH public key with the complete key
    3. Ensure ansible user has passwordless sudo or BECOME password is configured
    4. Test SSH connectivity to all three hosts before running playbook

**Features implemented**:
  - ✓ Creates system group `appgroup` with GID 1500
  - ✓ Creates system user `appuser` with UID 1500, home `/opt/appuser`, shell `/bin/bash`, no login password
  - ✓ Sets home directory permissions to 700 (rwx------)
  - ✓ Deploys SSH public key using ansible.posix.authorized_key (safe, idempotent)
  - ✓ Configures sudo access for both `/opt/app/bin/start.sh` and `/opt/app/bin/stop.sh` with NOPASSWD
  - ✓ Each sudoers command in separate entry for clarity and maintainability
  - ✓ Comprehensive validation tasks verify all outcomes
  - ✓ Full idempotency - safe to run multiple times
  - ✓ Targets all three hosts with identical configuration
