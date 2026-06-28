# Ansible Playbook Build Summary

## PB-2026-002 — Create application service account and configure limited sudo access

**Input file**: pb-2026-002.txt  
**Output file**: pb-2026-002.yml  
**Target**: db-prod-01, db-prod-02, db-prod-03 (Red Hat Enterprise Linux 8.9)  
**Tasks generated**: 12  
**Modules used**: ansible.builtin.group, ansible.builtin.user, ansible.builtin.file, ansible.posix.authorized_key, community.general.sudoers, ansible.builtin.command, ansible.builtin.shell, ansible.builtin.debug

**Assumptions made**:
  - Assumes a group `db_servers` exists in inventory mapping the three hostnames to their respective IP addresses
  - SSH public key provided in the request is treated as literal and passed directly to the `authorized_key` module
  - The SSH key shown in the request (`AAAAB3NzaC1y...`) is assumed to be a valid (though abbreviated) RSA public key; in production, the full key must be provided
  - Uses `become: true` with `become_method: sudo` as specified in the BECOME field
  - Uses `ansible_user: ansible` as the default SSH user connecting from the Ansible controller
  - Sets the home directory explicitly to `/opt/appuser` and ensures it is created by the user task
  - Sudoers entry uses `nopasswd: true` to allow passwordless execution of the specified commands
  - Validation tasks use `changed_when: false` to report as unchanged and not trigger subsequent tasks unnecessarily

**Warnings**:
  - The SSH public key in the request appears to be truncated (`AAAAB3NzaC1yc2E...`). **Before running this playbook, replace the key value with the full, complete SSH public key** for `appuser@controller`.
  - The `sudo -l -U appuser` command in the final validation task requires the playbook to be run with `become: true`, so it will succeed. However, you should manually verify on one target host that the sudoers entry is correctly configured by logging in as `appuser` and running `sudo -l`.
  - Idempotency: The playbook is fully idempotent and safe to run multiple times. User, group, and sudoers entries will not be duplicated if re-run.

---

## PB-2026-004 — Install IIS and deploy placeholder corporate website

**Input file**: pb-2026-004.txt  
**Output file**: pb-2026-004.yml  
**Target**: win-web-01, win-web-02 (Windows Server 2019 Standard)  
**Tasks generated**: 16  
**Modules used**: ansible.windows.win_feature, ansible.windows.win_reboot, ansible.windows.win_service, ansible.windows.win_file, ansible.windows.win_copy, community.windows.win_iis_webapppool, community.windows.win_iis_website, ansible.windows.win_firewall_rule, ansible.windows.win_service_info, ansible.windows.win_stat, ansible.builtin.debug

**Assumptions made**:
  - Assumes a group `web_servers` exists in inventory mapping the two hostnames to their respective IP addresses
  - Uses `ansible_winrm_transport: ntlm` as the default (appropriate for workgroup or non-Kerberos environments). If hosts are domain-joined and Kerberos is available, change this to `kerberos`.
  - The placeholder HTML is inline in the playbook (using `win_copy` with `content` parameter) rather than requiring a template file
  - Application pool `CorpSitePool` is created with managed runtime version "" (no .NET code) and integrated pipeline mode, as specified
  - The default IIS website is stopped to avoid port 80 conflicts; this is safe and idempotent
  - IIS features are installed all at once in a single task; if the installation requires a reboot, the playbook will detect it via `iis_install.reboot_required` and reboot the host
  - The firewall rule uses `direction: in`, `action: allow`, and `protocol: tcp` with `local_port: 80`

**Warnings**:
  - The firewall rule is applied at the local policy level. If hosts are managed by Group Policy, ensure that no GPO conflicts with this rule.
  - If IIS installation triggers a reboot, the playbook will automatically reboot the server. Be aware of any maintenance windows or load balancer configurations (the request mentions an F5 load balancer).
  - The placeholder `index.html` file is simple HTML. If you need to customize the page content (e.g., add company branding, logos, or additional text), update the `win_copy` task's `content` parameter before running.
  - Idempotency: The playbook is fully idempotent. Running it multiple times will not create duplicate IIS websites, application pools, or firewall rules because all tasks use `state: present` or `state: started` with appropriate guards.
  - The binding configuration in the `win_iis_website` task specifies both the `bindings:` parameter and legacy `port` and `host_header` parameters for compatibility; the `bindings:` list is the primary configuration.

---

## Summary Statistics

**Total requests processed**: 2  
**Total playbooks generated**: 2  
**Total tasks across all playbooks**: 28  
**Linux playbooks**: 1  
**Windows playbooks**: 1  
**Multi-host plays**: 2 (both requests target multiple hosts)  

---

## Next Steps

1. **PB-2026-002 (Linux)**:
   - Ensure the `db_servers` inventory group is defined with the three hostname and IP mappings
   - Replace the truncated SSH public key with the full, complete key
   - Review the sudoers entry to confirm the exact paths and command syntax match your environment
   - Run the playbook with `ansible-playbook -i inventory pb-2026-002.yml`

2. **PB-2026-004 (Windows)**:
   - Ensure the `web_servers` inventory group is defined with the two hostname and IP mappings
   - Confirm WinRM connectivity to both hosts (port 5985 for HTTP or 5986 for HTTPS)
   - If hosts are domain-joined, update the playbook to use `ansible_winrm_transport: kerberos` and set the user to `DOMAIN\ansible_svc`
   - Consider the load balancer implications before reboot during IIS installation
   - Run the playbook with `ansible-playbook -i inventory pb-2026-004.yml`

3. **General**:
   - Both playbooks include validation tasks at the end to confirm the expected outcomes
   - Both playbooks are fully idempotent and safe to run multiple times
   - All hosts should be reachable and have SSH/WinRM connectivity from the Ansible controller
