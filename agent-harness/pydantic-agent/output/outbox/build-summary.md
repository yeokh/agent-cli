## PB-2026-002 — Create application service account and configure limited sudo access

**Input file**: pb-2026-002.txt
**Output file**: pb-2026-002.yml
**Target**: db-prod-01, db-prod-02, db-prod-03 (Red Hat Enterprise Linux 8.9)
**Tasks generated**: 12
**Modules used**: `ansible.builtin.group`, `ansible.builtin.user`, `ansible.builtin.file`, `ansible.posix.authorized_key`, `ansible.builtin.command`, `ansible.builtin.debug`, `community.general.sudoers`
**Assumptions made**:
  - Derived the inventory group name `appuser_sudo_hosts` from the playbook title "Create application service account and configure limited sudo access".
  - Assumed standard Linux directory permissions of `'0700'` (read, write, execute permissions for user only) to satisfy the constraint "not accessible to other users".
  - Used `validation: required` in the `community.general.sudoers` task to enforce syntax checking via `visudo` during the playbook execution, as required by the guidelines.
**Warnings**:
  - The playbook configures `sudo` privileges for the commands `/opt/app/bin/start.sh` and `/opt/app/bin/stop.sh`. Ensure that these scripts exist on the target servers and are secure against unauthorized modification or privilege escalation, as they will be run as root by `appuser` without a password prompt.
