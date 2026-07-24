# Ansible Playbook: PB-2026-001

## Overview
This playbook configures the firewall on **web-prod-01** (RHEL 9.3) to support a new Java web application deployment.

## Request Details
- **Request ID:** PB-2026-001
- **Date:** 2026-06-20
- **Requested By:** Sarah Chen
- **Target Host:** web-prod-01 (192.168.10.50)
- **OS:** Red Hat Enterprise Linux 9.3

## What This Playbook Does

1. **Installs firewalld** if not already present
2. **Starts and enables firewalld** for automatic startup on reboot
3. **Opens the following ports:**
   - **8080/TCP** - HTTP for Java application
   - **8443/TCP** - HTTPS for Java application
   - **9090/TCP** - WildFly admin console (temporary, for initial setup)
4. **Makes all rules persistent** across server reboots
5. **Protects SSH** (port 22) - no modifications made
6. **Validates** that all required ports are properly configured

## Key Features

✅ **Idempotent** - Can be run multiple times without errors or duplicate rules  
✅ **Persistent** - All firewall rules survive server reboots  
✅ **Non-destructive** - Existing firewall rules for other services are preserved  
✅ **Immediate and permanent** - Rules are applied immediately and saved to persistent config  

## Usage

### 1. Update the inventory file
Edit `pb-2026-001-inventory.ini` if needed to match your environment:
```ini
[web_prod]
web_prod_01 ansible_host=192.168.10.50 ansible_user=root
```

### 2. Run the playbook
```bash
ansible-playbook -i pb-2026-001-inventory.ini pb-2026-001-playbook.yml
```

### 3. Verify the deployment
The playbook includes verification tasks that will confirm all ports are open.

## Playbook Structure

| Task | Purpose |
|------|---------|
| Ensure firewalld is installed | Install the firewall service |
| Ensure firewalld service is started and enabled | Start immediately and on reboot |
| Open port 8080/TCP | HTTP for Java app |
| Open port 8443/TCP | HTTPS for Java app |
| Open port 9090/TCP | WildFly admin console |
| Reload firewalld | Ensure persistence |
| Verify ports are open | Confirm successful configuration |
| Display summary | Show completion status |

## Requirements

- Ansible 2.9 or later
- Access to the target host (web-prod-01) with sudo/become privileges
- Python 3.x on the target host
- Network connectivity to the target host

## Notes

- Port 22 (SSH) is intentionally **not modified** per the constraints
- The WildFly admin console (port 9090) is marked as temporary for initial setup
- All firewall rules use both `permanent: yes` and `immediate: yes` to ensure persistence and instant application
- The playbook is safe to run multiple times

## Rollback (if needed)

To remove the added firewall rules:
```bash
firewall-cmd --remove-port=8080/tcp --permanent
firewall-cmd --remove-port=8443/tcp --permanent
firewall-cmd --remove-port=9090/tcp --permanent
firewall-cmd --reload
```

## Questions or Issues

Contact the automation team with any issues or questions about this playbook.
