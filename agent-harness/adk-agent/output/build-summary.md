# Ansible Playbook Build Summary

Generated: 2026-06-20

---

## PB-2026-001 — Configure firewall for new Java web application

**Input file**: pb-2026-001.txt  
**Output file**: pb-2026-001.yml  
**Target**: web-prod-01 (Red Hat Enterprise Linux 9.3)  
**Tasks generated**: 10  
**Modules used**: ansible.builtin.dnf, ansible.builtin.systemd, ansible.posix.firewalld, ansible.builtin.command, ansible.builtin.debug  
**Assumptions made**:
  - Default SSH connection parameters applied (ansible user, StrictHostKeyChecking=no)
  - Firewalld package installation included as a safety check (may already be present on RHEL 9.3)
  - All ports configured in the default zone (no specific zone was requested)

**Warnings**:
  - None. All tasks are fully idempotent and safe to run multiple times.

---

## PB-2026-002 — Create application service account and configure limited sudo access

**Input file**: pb-2026-002.txt  
**Output file**: pb-2026-002.yml  
**Target**: db-prod-01, db-prod-02, db-prod-03 (Red Hat Enterprise Linux 8.9)  
**Tasks generated**: 13  
**Modules used**: ansible.builtin.group, ansible.builtin.user, ansible.builtin.file, ansible.posix.authorized_key, community.general.sudoers, ansible.builtin.getent, ansible.builtin.stat, ansible.builtin.command, ansible.builtin.debug  
**Assumptions made**:
  - Multi-host targeting requires an inventory group named `db_servers` containing the three database hosts
  - SSH public key in request was truncated ("AAAAB3NzaC1yc2EAAAADAQABAAABgQC7vX..."); the full key must be provided in the playbook vars before execution
  - Sudo rules created as separate files in /etc/sudoers.d/ (one per command) for clarity and validation
  - Default SSH connection parameters applied

**Warnings**:
  - The SSH public key variable `appuser_ssh_key` contains a truncated placeholder. Replace with the complete SSH public key before running.
  - The sudoers validation requires that visudo is available on the target system (standard on RHEL).

---

## PB-2026-003 — Create local service accounts and assign group memberships

**Input file**: pb-2026-003.txt  
**Output file**: pb-2026-003.yml  
**Target**: win-app-01 (Windows Server 2022 Datacenter)  
**Tasks generated**: 12  
**Modules used**: ansible.windows.win_user, ansible.windows.win_group_membership, ansible.windows.win_shell, ansible.builtin.debug  
**Assumptions made**:
  - WinRM connection using NTLM transport (no domain information provided, assuming workgroup or non-Kerberos auth)
  - Default WinRM port 5985 (HTTP) used; certificate validation disabled as is common in internal environments
  - Passwords referenced as Ansible Vault variables: `vault_svc_monitor_password` and `vault_svc_backup_password`
  - `update_password: on_create` ensures existing account passwords are never reset on subsequent runs

**Warnings**:
  - **Required before execution**: Create an Ansible Vault file containing `vault_svc_monitor_password` and `vault_svc_backup_password` variables.
  - The playbook will fail if these vault variables are not defined.
  - Ensure the ansible_svc user on the Windows target has local administrator privileges to create accounts and modify group memberships.

---

## PB-2026-004 — Install IIS and deploy placeholder corporate website

**Input file**: pb-2026-004.txt  
**Output file**: pb-2026-004.yml  
**Target**: win-web-01, win-web-02 (Windows Server 2019 Standard)  
**Tasks generated**: 18  
**Modules used**: ansible.windows.win_feature, ansible.windows.win_reboot, ansible.windows.win_service, ansible.windows.win_file, ansible.windows.win_copy, community.windows.win_iis_webapppool, community.windows.win_iis_website, ansible.windows.win_firewall_rule, ansible.windows.win_service_info, ansible.windows.win_shell, ansible.builtin.debug  
**Assumptions made**:
  - Multi-host targeting requires an inventory group named `web_servers` containing the two web server hosts
  - WinRM connection using NTLM transport (no domain information provided)
  - IIS application pool configured with no managed runtime (managedRuntimeVersion: '') for static content hosting
  - Default Web Site stopped (not removed) to free port 80 for the new CorpSite website
  - Placeholder HTML is minimal but valid HTML5 structure
  - HTTP test in validation uses localhost with Host header to confirm the site responds correctly

**Warnings**:
  - The playbook includes a conditional reboot task if IIS installation requires it. Ensure maintenance windows are appropriate.
  - Both servers must be behind the F5 load balancer as noted; this playbook does not configure load balancer settings.
  - SSL/HTTPS configuration is explicitly deferred to a follow-up request (PB-2026-005) as noted in the original request.
  - Ensure the ansible_svc user has local administrator privileges on both Windows targets.

---

## Summary Statistics

- **Total requests processed**: 4
- **Total playbooks generated**: 4
- **Linux playbooks**: 2 (PB-2026-001, PB-2026-002)
- **Windows playbooks**: 2 (PB-2026-003, PB-2026-004)
- **Multi-host playbooks**: 2 (PB-2026-002, PB-2026-004)
- **Vault variables required**: 2 playbooks (PB-2026-003, requiring 2 vault variables)

All playbooks follow idempotency best practices and include validation tasks to confirm expected outcomes.
