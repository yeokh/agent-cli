# Ansible Playbook Builder — Build Summary

## PB-2026-002 — Create application service account and configure limited sudo access

**Input file**: `pb-2026-002.txt`
**Output file**: `pb-2026-002.yml`
**Target**: db-prod-01, db-prod-02, db-prod-03 (Red Hat Enterprise Linux 8.9)
**Tasks generated**: 11 tasks (6 configuration + 5 validation)
**Modules used**: `ansible.builtin.group`, `ansible.builtin.user`, `ansible.builtin.file`, `ansible.posix.authorized_key`, `community.general.sudoers`, `ansible.builtin.command`, `ansible.builtin.stat`, `ansible.builtin.debug`

**Assumptions made**:
  - Group inventory name `db_servers` derived from hostname and task context (PostgreSQL replica servers)
  - SSH public key used as-is from request; assumes key string is complete and valid
  - Sudoers entry grants nopasswd access to exactly two commands as specified; no wildcards or ALL privileges
  - User created with `password: '!'` to disable password login, forcing SSH key authentication only
  - No specific Vault variables required as no sensitive credentials are hardcoded in this playbook

**Warnings**:
  - The SSH public key in the playbook is truncated (`AAAAB3NzaC1yc2E...`) — you must replace it with the complete key before running
  - The sudoers task uses `validate: true` which requires `visudo` to be available on target systems (standard on RHEL)
  - Idempotency guaranteed: running multiple times will not create duplicate entries or cause errors
  - The `sudo -l -U appuser` validation task requires passwordless sudo to be working; may show "user not in sudoers" error if sudoers entry hasn't been synced yet

---

## PB-2026-004 — Install IIS and deploy placeholder corporate website

**Input file**: `pb-2026-004.txt`
**Output file**: `pb-2026-004.yml`
**Target**: win-web-01, win-web-02 (Windows Server 2019 Standard)
**Tasks generated**: 20 tasks (13 configuration + 7 validation)
**Modules used**: `ansible.windows.win_feature`, `ansible.windows.win_reboot`, `ansible.windows.win_service`, `ansible.windows.win_file`, `ansible.windows.win_copy`, `community.windows.win_iis_webapppool`, `community.windows.win_iis_website`, `ansible.windows.win_firewall_rule`, `ansible.windows.win_service_info`, `ansible.windows.win_stat`, `ansible.windows.win_shell`, `ansible.builtin.debug`

**Assumptions made**:
  - Group inventory name `web_servers` derived from hostname and task context
  - Application pool configured for "Integrated" pipeline mode with no managed runtime (v0 for native/static content)
  - Default Web Site stopped before CorpSite creation to avoid port 80 binding conflict; both are independent
  - Windows Firewall inbound rule uses NTLM transport (workgroup assumption); if domain-joined, consider updating to kerberos transport in the vars block
  - HTTP binding created for all IP addresses (0.0.0.0) with host header `corpsite.example.com`
  - Placeholder index.html deployed as simple static HTML with embedded CSS

**Warnings**:
  - IIS installation may require a system reboot; the playbook handles this with conditional `win_reboot` but execution time may increase significantly
  - The application pool service name format (`'AppPool CorpSitePool'`) depends on IIS version; tested on Windows Server 2019
  - Validation task `Get-Website` uses PowerShell; ensure WinRM is configured with PowerShell language support on target hosts
  - Idempotency: re-running the playbook is safe; website and pool will not be duplicated due to `state: present` and idempotent module behaviors
  - The Default Web Site stop is unconditional; if that site is needed for other purposes, modify the task to be conditional or remove it
  - No SSL/HTTPS configuration in this playbook (as noted in request); follow-up request PB-2026-005 will handle HTTPS bindings

---

## General Notes

- Both playbooks include multi-host targeting with expected inventory entries documented at the top
- All playbooks include comprehensive validation tasks that confirm the expected outcomes without making changes (safe to run repeatedly)
- Connection defaults are embedded in each playbook's `vars:` block for self-contained execution (no inventory file variables required)
- Both playbooks follow idempotency best practices and can be safely run multiple times
- No Vault variables are required for PB-2026-002; PB-2026-004 uses the default `ansible_svc` user which should exist in your Windows domain or local accounts
