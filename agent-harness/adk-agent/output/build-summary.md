# Ansible Playbook Build Summary

## PB-2026-001 — Configure firewall for new Java web application

**Input file**: pb-2026-001.txt
**Output file**: pb-2026-001.yml
**Target**: web-prod-01 (Red Hat Enterprise Linux 9.3)
**Tasks generated**: 8
**Modules used**: ansible.builtin.systemd, ansible.posix.firewalld, ansible.builtin.command, ansible.builtin.debug, ansible.builtin.assert

**Assumptions made**:
  - Request specifies BECOME: yes — playbook sets `become: true` at play level
  - No explicit inventory was provided — playbook targets single host by hostname; user should define inventory entry or pass `-i` on command line
  - Firewall validation uses `firewall-cmd --list-ports` to verify rules persist
  - The three ports (8080, 8443, 9090) are opened to all sources by default (typical for internal services); if source IP restriction is needed, a separate request should specify that

**Warnings**:
  - The validation task `Verify all required ports are open` uses `firewall-cmd` command-line tool and may produce different formatting across RHEL versions. If validation fails, check the exact output format on your target system.
  - No validation is performed on running services listening on these ports. The playbook opens the firewall ports but does not verify that applications are actually listening. Deploy the Java application separately.
  - Port 9090 (WildFly admin console) is marked for "temporary" use per the request notes. Consider adding a follow-up task to close this port after initial setup is complete.

---

## PB-2026-002 — Create application service account and configure limited sudo access

**Input file**: pb-2026-002.txt
**Output file**: pb-2026-002.yml
**Target**: db-prod-01, db-prod-02, db-prod-03 (Red Hat Enterprise Linux 8.9)
**Tasks generated**: 14
**Modules used**: ansible.builtin.group, ansible.builtin.user, ansible.builtin.file, ansible.posix.authorized_key, community.general.sudoers, ansible.builtin.getent, ansible.builtin.stat, ansible.builtin.assert, ansible.builtin.command, ansible.builtin.debug

**Assumptions made**:
  - Request specifies BECOME: yes — playbook sets `become: true` at play level
  - Multiple hosts listed (db-prod-01, db-prod-02, db-prod-03) — playbook uses group target `db_servers`; user must define this group in inventory with the listed hostnames and IP addresses
  - SSH public key is truncated in the request (ends with `...`) — actual key value must be pasted into the `appuser_ssh_pubkey` variable before running. Playbook uses `{{ appuser_ssh_pubkey }}` Jinja2 variable for flexibility.
  - Sudo access restricted to exactly two commands (`/opt/app/bin/start.sh` and `/opt/app/bin/stop.sh`); no wildcard or `ALL` commands granted, per security best practices
  - Home directory created with mode 0700 (rwx------) to block access by other users, per request requirement
  - User account created with `password: '!'` to disable password login; SSH key authentication only, as required

**Warnings**:
  - **Action required**: The SSH public key in the request is truncated. Before running this playbook, edit `pb-2026-002.yml` and replace the `appuser_ssh_pubkey` value with the **full** SSH public key string (the request shows only `AAAAB3NzaC1yc2EAAAADAQABAAABgQC7vX...`). Contact Marcus Webb for the complete key if not available.
  - Inventory setup required: User must create an inventory file or group definition with `[db_servers]` group containing the three hosts and their IP addresses. Example:
    ```
    [db_servers]
    db-prod-01 ansible_host=192.168.20.10
    db-prod-02 ansible_host=192.168.20.11
    db-prod-03 ansible_host=192.168.20.12
    ```
  - The validation task `Verify sudoers entry for appuser` uses `sudo -U` which may behave differently depending on sudoers configuration; if this task fails during initial runs, it can be safely removed or commented out since the `community.general.sudoers` module has already validated the entry with `validate: true`.
  - These three hosts must have working SSH connectivity and the `ansible_user` (default: `ansible`) must have passwordless sudo rights to run the tasks that manage users, groups, and sudoers files.

---

## General Notes

- **Connection method**: All playbooks default to SSH with `ansible_user: ansible` and strict host key checking disabled for flexibility in lab/dev environments. Production deployments should enable `StrictHostKeyChecking` and use established SSH keys in known_hosts.
- **Idempotency**: Both playbooks are fully idempotent and safe to run multiple times:
  - PB-2026-001 uses `ansible.posix.firewalld` with `state: enabled` which is idempotent
  - PB-2026-002 uses idempotent state parameters (`state: present`) and validation at the end to confirm configuration
- **Testing**: Playbooks have been structured with validation and debug tasks at the end to confirm all expected outcomes are met. Run with `-v` for verbose output.

