# Red Hat Product Lifecycle Status Report

**Organization:** Example Corp  
**Report Date:** May 25, 2026  
**Report Scope:** Current Infrastructure Inventory Analysis  

---

## Executive Summary

This report provides a comprehensive analysis of the Red Hat product lifecycle status across the organization's infrastructure. The analysis reveals **CRITICAL RISKS** requiring immediate attention:

- **5 Systems** are already **END-OF-LIFE (EOL)** and receiving **NO SECURITY SUPPORT**
- **2 Systems** are in **Maintenance Support** phase with limited support windows
- **3 Systems** are in **Full Support** but one is approaching transition in 2025

### Critical Findings
1. **RHEL 7.x environments** (web-servers, storage-system) are **completely unsupported** since June 30, 2024
2. **OpenShift 4.10 & 4.12** are both EOL with no available updates
3. **Ansible Automation Platform 2.1** reached EOL October 1, 2023
4. **RHEL 8.4** transitioned to Maintenance Support; must upgrade within 3.5 years
5. **Satellite 6.11** approaches EOL (July 29, 2025) - approximately 14 months remaining

---

## Detailed System Analysis

### 🔴 CRITICAL RISK - END OF LIFE SYSTEMS (Immediate Action Required)

#### 1. Web Servers (RHEL 7.9)

| Property | Value |
|----------|-------|
| **Product** | Red Hat Enterprise Linux |
| **Version** | 7.9 |
| **System Count** | 15 servers |
| **Environment** | Production |
| **Criticality** | High |
| **Lifecycle Phase** | ❌ END OF LIFE |
| **GA Date** | June 10, 2014 |
| **Full Support End** | August 6, 2019 |
| **Maintenance Support End** | June 30, 2024 |
| **Days Since EOL** | 694 days (as of May 25, 2026) |
| **Risk Score** | 100/100 - CRITICAL |
| **Support Status** | ❌ No security patches available |

**Impact Assessment:**
- Running 15 production web servers with **ZERO security updates** since June 2024
- All known CVEs on RHEL 7.9 remain unfixed
- No compliance with PCI-DSS or SOC2 requirements
- Vulnerability window: 694 days unpatched
- Estimated exploitation probability: VERY HIGH

**Recommended Action:**
- **EMERGENCY UPGRADE REQUIRED** - Migrate immediately to RHEL 8.9 or 9.x
- Estimated effort: 40-60 hours for testing + migration
- Downtime: 2-4 hours per server (20 servers × 3 hours = 60 hours total)
- Target completion: Within 30 days

**Next Version:** RHEL 8.9 (Latest RHEL 8 - Full Support until May 2025) or RHEL 9.3+ (Full Support until November 2025)

---

#### 2. Container Platform - Production (OCP 4.10)

| Property | Value |
|----------|-------|
| **Product** | OpenShift Container Platform |
| **Version** | 4.10 |
| **System Count** | 3 clusters |
| **Environment** | Production |
| **Criticality** | Critical |
| **Lifecycle Phase** | ❌ END OF LIFE |
| **GA Date** | January 25, 2022 |
| **Full Support End** | January 25, 2023 |
| **Maintenance Support End** | July 25, 2023 |
| **Days Since EOL** | 1,035 days (as of May 25, 2026) |
| **Risk Score** | 100/100 - CRITICAL |
| **Support Status** | ❌ No security patches available |

**Impact Assessment:**
- 3 production OCP clusters running on completely unsupported version
- 18-month lifecycle expired; 2.8+ years without security updates
- Container workloads vulnerable to known exploits
- Unable to obtain support from Red Hat

**Recommended Action:**
- **EMERGENCY UPGRADE REQUIRED** - Immediate cluster upgrade to OCP 4.14 (EUS) or 4.15
- Estimated effort: 80-120 hours for planning, testing, migration
- Downtime: Rolling updates with controlled downtime
- Target completion: Within 60 days

**Next Version:** OpenShift 4.14 (EUS - 48 months support) or 4.15 (standard 18-month support)

---

#### 3. Container Platform - Development (OCP 4.12)

| Property | Value |
|----------|-------|
| **Product** | OpenShift Container Platform |
| **Version** | 4.12 |
| **System Count** | 1 cluster |
| **Environment** | Development |
| **Criticality** | Medium |
| **Lifecycle Phase** | ❌ END OF LIFE |
| **GA Date** | September 27, 2022 |
| **Full Support End** | October 27, 2023 |
| **Maintenance Support End** | March 27, 2024 |
| **Days Since EOL** | 789 days (as of May 25, 2026) |
| **Risk Score** | 100/100 - CRITICAL |
| **Support Status** | ❌ No security patches available (EUS option available) |

**Note:** While 4.12 is an EUS-eligible release, the standard support has ended. EUS extended support could have provided 48 months total support if purchased, but that opportunity has passed.

**Impact Assessment:**
- Even in development, running on unsupported platform increases risk
- Cannot reliably test new applications
- Development parity with production is now impossible

**Recommended Action:**
- **HIGH PRIORITY UPGRADE** - Upgrade to OCP 4.14 (EUS) or 4.15
- Estimated effort: 20-30 hours
- Target completion: Within 30 days

---

#### 4. Automation Platform (AAP 2.1)

| Property | Value |
|----------|-------|
| **Product** | Red Hat Ansible Automation Platform |
| **Version** | 2.1 |
| **System Count** | 1 server |
| **Environment** | Production |
| **Criticality** | High |
| **Lifecycle Phase** | ❌ END OF LIFE |
| **GA Date** | October 1, 2021 |
| **Full Support End** | October 1, 2022 |
| **Maintenance Support End** | October 1, 2023 |
| **Days Since EOL** | 967 days (as of May 25, 2026) |
| **Risk Score** | 100/100 - CRITICAL |
| **Support Status** | ❌ No security patches available |

**Impact Assessment:**
- Automation platform managing critical infrastructure has ZERO security coverage
- Risk of credential compromise through known vulnerabilities
- Cannot receive security advisories or patches

**Recommended Action:**
- **EMERGENCY UPGRADE REQUIRED** - Upgrade to AAP 2.4 or 2.5
- Estimated effort: 30-40 hours for planning, testing, migration
- Downtime: 1-2 hours (typically performs in-place upgrade)
- Target completion: Within 14 days

**Next Version:** Ansible Automation Platform 2.4+ (GA in 2024, 18-month lifecycle)

---

#### 5. Storage System (RHEL 7.6)

| Property | Value |
|----------|-------|
| **Product** | Red Hat Enterprise Linux |
| **Version** | 7.6 |
| **System Count** | 2 servers |
| **Environment** | Production |
| **Criticality** | Critical |
| **Lifecycle Phase** | ❌ END OF LIFE |
| **GA Date** | May 16, 2019 |
| **Full Support End** | August 6, 2019 |
| **Maintenance Support End** | June 30, 2024 |
| **Days Since EOL** | 694 days (as of May 25, 2026) |
| **Risk Score** | 100/100 - CRITICAL |
| **Support Status** | ❌ No security patches available |

**Impact Assessment:**
- NFS storage backend supporting all production infrastructure is unpatched
- Any compromise could affect organization-wide data availability
- File system vulnerabilities remain unfixed
- Does not comply with security policies

**Recommended Action:**
- **EMERGENCY UPGRADE REQUIRED** - Migrate to RHEL 8.9 or RHEL 9.x
- Estimated effort: 50-70 hours (includes backup/verification)
- Downtime: 3-6 hours (with data migration)
- Target completion: Within 30 days

**Next Version:** RHEL 8.9 (Latest RHEL 8) or RHEL 9.3+ (Latest RHEL 9)

---

### 🟡 HIGH RISK - MAINTENANCE SUPPORT PHASE (Near-Term Action Required)

#### 6. Database Cluster (RHEL 8.4)

| Property | Value |
|----------|-------|
| **Product** | Red Hat Enterprise Linux |
| **Version** | 8.4 |
| **System Count** | 4 servers |
| **Environment** | Production |
| **Criticality** | Critical |
| **Lifecycle Phase** | 🟡 MAINTENANCE SUPPORT |
| **GA Date** | May 18, 2021 |
| **Full Support End** | May 31, 2024 ✓ (Already passed) |
| **Maintenance Support End** | May 31, 2029 |
| **Days Until EOL** | 1,102 days (~3 years) |
| **Risk Score** | 90/100 - HIGH |
| **Current Support** | 🟡 Critical/Important CVEs only |

**Impact Assessment:**
- Recently transitioned from Full Support to Maintenance Support (May 31, 2024)
- Will receive security patches but NO new features or minor versions
- 3 years remaining in Maintenance Support phase
- Risk increases over time as database software dependencies age

**Support Window:**
- Receives: Critical and Important CVE patches only
- Does NOT receive: Feature updates, hardware enablement, minor releases
- Does NOT receive: Urgent bug fixes outside security scope

**Recommended Action:**
- **HIGH PRIORITY** - Plan upgrade to RHEL 8.9 or RHEL 9.x within 12 months
- Estimated effort: 40-60 hours for planning, testing, migration
- Downtime: 2-4 hours (with database failover coordination)
- Target completion: Q4 2026 or Q1 2027

**Next Version:** RHEL 8.9 (Latest RHEL 8 - Full Support until May 2025 → extends to May 2030 in Maintenance) or RHEL 9.3+ (Full Support until November 2025)

---

#### 7. Satellite Server (Satellite 6.11)

| Property | Value |
|----------|-------|
| **Product** | Red Hat Satellite |
| **Version** | 6.11 |
| **System Count** | 1 server |
| **Environment** | Production |
| **Criticality** | High |
| **Lifecycle Phase** | 🟡 MAINTENANCE SUPPORT (Post-Full Support) |
| **GA Date** | July 29, 2021 |
| **Full Support End** | July 29, 2023 ✓ (Already passed) |
| **Maintenance Support End** | July 29, 2025 ⚠️ APPROACHING |
| **Days Until EOL** | ~300 days (10 months remaining) |
| **Risk Score** | 95/100 - HIGH |
| **Current Support** | 🟡 Critical/Important CVEs only (LIMITED WINDOW) |

**Impact Assessment:**
- Only ~10 months remaining in Maintenance Support phase
- After July 2025, NO security patches available
- This is the patch management server for the organization
- Patch management itself becomes unsupported after EOL

**Recommended Action:**
- **HIGH PRIORITY** - Upgrade to Satellite 6.13+ BEFORE July 29, 2025
- Estimated effort: 50-80 hours for planning, testing, migration
- Downtime: 4-8 hours
- **Target completion: Q2-Q3 2025** (before EOL deadline)

**Next Version:** Red Hat Satellite 6.13 or later (verify current lifecycle at time of upgrade)

---

### 🟢 MEDIUM RISK - FULL SUPPORT PHASE (Monitor & Plan)

#### 8. IAM Servers (RHEL 8.5)

| Property | Value |
|----------|-------|
| **Product** | Red Hat Enterprise Linux |
| **Version** | 8.5 |
| **System Count** | 2 servers |
| **Environment** | Production |
| **Criticality** | Critical |
| **Lifecycle Phase** | 🟢 FULL SUPPORT |
| **GA Date** | November 9, 2021 |
| **Full Support End** | November 30, 2024 ⚠️ (6 months away) |
| **Maintenance Support End** | November 30, 2029 |
| **Days Until Full Support End** | ~175 days (~6 months) |
| **Days Until EOL** | ~1,285 days (~3.5 years) |
| **Risk Score** | 35/100 - LOW |
| **Current Support** | 🟢 Full: Critical/Important/Moderate CVEs + Urgent Bugs + Hardware Enablement |

**Impact Assessment:**
- Currently in Full Support with all security coverage
- Will transition to Maintenance Support in 6 months (November 2024)
- Still has 3.5 years before complete EOL
- Time to plan upgrade is NOW before Full Support ends

**Recommended Action:**
- **MEDIUM PRIORITY** - Plan upgrade to RHEL 9.x before November 30, 2024
- Estimated effort: 30-40 hours
- Downtime: 1-2 hours
- Target completion: Q4 2024

**Next Version:** RHEL 9.3+ (Full Support extends through November 2025, then Maintenance Support through 2032)

---

#### 9. Application Servers (RHEL 8.6)

| Property | Value |
|----------|-------|
| **Product** | Red Hat Enterprise Linux |
| **Version** | 8.6 |
| **System Count** | 24 servers |
| **Environment** | Production |
| **Criticality** | High |
| **Lifecycle Phase** | 🟢 FULL SUPPORT |
| **GA Date** | May 10, 2022 |
| **Full Support End** | May 31, 2025 ⚠️ (~1 year away) |
| **Maintenance Support End** | May 31, 2030 |
| **Days Until Full Support End** | ~401 days (~13 months) |
| **Days Until EOL** | ~1,467 days (~4 years) |
| **Risk Score** | 30/100 - LOW |
| **Current Support** | 🟢 Full: All security categories + urgent bugs + hardware updates |

**Impact Assessment:**
- Largest fleet (24 servers) in Full Support phase
- Full Support ends May 31, 2025 - approximately 13 months
- Transition to Maintenance Support will occur Q2 2025
- Has 4 years before complete EOL, but should plan now

**Recommended Action:**
- **MEDIUM PRIORITY** - Plan upgrade to RHEL 8.9 or RHEL 9.x before May 31, 2025
- Estimated effort: 60-100 hours for planning and staggered upgrades
- Downtime: 1-2 hours per server × 24 servers (spread over weeks/months)
- Target completion: Q1-Q2 2025

**Next Version:** RHEL 8.9 (Full Support until May 2025, then Maintenance Support through May 2030) or RHEL 9.3+ (Full Support through November 2025)

---

#### 10. Monitoring Stack (RHEL 9.1)

| Property | Value |
|----------|-------|
| **Product** | Red Hat Enterprise Linux |
| **Version** | 9.1 |
| **System Count** | 3 servers |
| **Environment** | Production |
| **Criticality** | High |
| **Lifecycle Phase** | 🟢 FULL SUPPORT |
| **GA Date** | November 15, 2022 |
| **Full Support End** | November 30, 2025 ⚠️ (~1.5 years away) |
| **Maintenance Support End** | May 31, 2032 |
| **Days Until Full Support End** | ~553 days (~18 months) |
| **Days Until EOL** | ~2,198 days (~6 years) |
| **Risk Score** | 30/100 - LOW |
| **Current Support** | 🟢 Full: All security categories + new features + hardware enablement |

**Impact Assessment:**
- Healthy RHEL 9 deployment with longest lifecycle (10 years total)
- Still has 1.5 years in Full Support
- Longest time before upgrade needed (6+ years)
- Best positioned of all systems for long-term support

**Recommended Action:**
- **LOW PRIORITY** - No immediate action needed
- Begin planning upgrade to RHEL 9.4+ in 12-18 months
- Estimated effort: 20-30 hours
- Target completion: Q4 2026 or 2027

---

## Lifecycle Support Summary Table

| System | Product | Version | Phase | EOL Date | Days to EOL | Priority |
|--------|---------|---------|-------|----------|------------|----------|
| web-servers | RHEL | 7.9 | 🔴 EOL | 2024-06-30 | -694 | 🔴 CRITICAL |
| container-platform-prod | OCP | 4.10 | 🔴 EOL | 2023-07-25 | -1035 | 🔴 CRITICAL |
| container-platform-dev | OCP | 4.12 | 🔴 EOL | 2024-03-27 | -789 | 🔴 CRITICAL |
| automation-platform | AAP | 2.1 | 🔴 EOL | 2023-10-01 | -967 | 🔴 CRITICAL |
| storage-system | RHEL | 7.6 | 🔴 EOL | 2024-06-30 | -694 | 🔴 CRITICAL |
| satellite-server | Satellite | 6.11 | 🟡 Maint. | 2025-07-29 | ~300 | 🟡 HIGH |
| database-cluster | RHEL | 8.4 | 🟡 Maint. | 2029-05-31 | 1102 | 🟡 HIGH |
| iam-servers | RHEL | 8.5 | 🟢 Full | 2029-11-30 | 1285 | 🟢 MEDIUM |
| app-servers | RHEL | 8.6 | 🟢 Full | 2030-05-31 | 1467 | 🟢 MEDIUM |
| monitoring-stack | RHEL | 9.1 | 🟢 Full | 2032-05-31 | 2198 | 🟢 LOW |

---

## Compliance & Security Impact

### PCI-DSS Compliance
- **STATUS: NON-COMPLIANT** on systems running RHEL 7.x and unsupported products
- **Requirement 6.2**: "Ensure all system components and software are kept up to date"
- **Current Violation**: 5 systems with ZERO security updates

### SOC2 Compliance
- **STATUS: AT RISK** - Requires documented security patch management
- **Control A.13.1**: "Apply patches and updates to critical components"
- **Current Issue**: Cannot demonstrate compliance for EOL systems

### Audit Finding Risk
- Critical audit finding if discovered during SOC2/PCI assessment
- Evidence of EOL systems in production environment
- No evidence of security patch management for major systems

---

## Business Impact Summary

### Immediate Risks (Next 30 Days)
- **Data Breach Probability**: VERY HIGH on 24 affected systems (web, storage, database infrastructure)
- **Compliance Violation**: Already non-compliant with PCI-DSS, SOC2 requirements
- **Operational Continuity**: Storage infrastructure (NFS) compromise would impact ALL systems

### 30-90 Day Risks
- Satellite EOL (July 2025) will prevent patch management for entire infrastructure
- No security updates after that date for any system
- Exponential increase in vulnerability window

### 6-12 Month Risks
- All systems transition to EOL or Maintenance Support
- Extended support periods shrink year-over-year
- Upgrade debt compounds with each passing month

---

## Cost & Effort Estimation

### By Priority Level

| Priority | Systems | Est. Hours | Est. Cost* | Risk if Not Done | Timeline |
|----------|---------|-----------|-----------|-----------------|----------|
| 🔴 CRITICAL | 5 systems | 220-300 | $11K-15K | Data breach, compliance violation | Now-30 days |
| 🟡 HIGH | 2 systems | 80-120 | $4K-6K | Loss of patch management capability | 14-60 days |
| 🟢 MEDIUM | 2 systems | 60-100 | $3K-5K | Support coverage gap | 90-180 days |
| 🟢 LOW | 1 system | 20-30 | $1K-2K | Diminishing support | 6-12 months |
| **TOTAL** | **10 systems** | **380-550** | **$19K-28K** | **Complete loss of support** | **Phased by Q4 2026** |

*Cost estimation assumes $50/hour blended IT labor rate

---

## Red Hat Product Lifecycle Reference

### RHEL Lifecycle (10-year standard)
- **Full Support** (~5 years): Critical, Important, Moderate CVEs + bug fixes + hardware enablement + minor releases
- **Maintenance Support** (~5 years): Critical, Important CVEs only, urgent bugs
- **Extended Life Support (ELS)**: Optional add-on for post-EOL systems (RHEL 6/7 only)

### OpenShift Lifecycle (18 months per minor release)
- **Full Support** (6 months or 90 days after next release): Critical/Important CVEs + urgent bugs
- **Maintenance Support** (12 months): Critical/Important CVEs only
- **EUS (Extended Update Support)**: Even numbered releases (4.12, 4.14, 4.16...) get 48-month total support

### Ansible Automation Platform Lifecycle (18 months standard)
- **Full Support** (~12 months): All updates and security fixes
- **Maintenance Support** (~6 months): Critical security fixes only

### Red Hat Satellite Lifecycle (Varies by version)
- **Satellite 6.x**: ~4 years per release line
- Recommendation: Stay within 2 releases of current

---

## Recommendations & Next Steps

### Immediate (This Month)
1. ✅ **DECLARE EMERGENCY STATUS** - These systems are in production without security support
2. ✅ **ISOLATE EOL SYSTEMS** - Implement network segmentation for RHEL 7.x systems
3. ✅ **ACTIVATE INCIDENT RESPONSE** - Treat as security incident if not already
4. ✅ **NOTIFY STAKEHOLDERS** - Inform business owners of compliance risk
5. ✅ **ESTABLISH UPGRADE TASK FORCE** - Assign dedicated resources for upgrades

### 30 Days
- Complete RHEL 7.x migration to RHEL 8.9 or 9.x (5 systems, 45 servers total)
- Complete AAP 2.1 upgrade to AAP 2.4+
- Prepare OpenShift upgrade plan for 4.10 and 4.12 clusters

### 60 Days
- Complete OpenShift upgrades to 4.14 (EUS) or 4.15
- Complete Satellite 6.11 upgrade to 6.13+
- Begin RHEL 8.4 migration plan

### 90 Days
- All critical and high-priority systems upgraded
- All systems in Full or Maintenance Support phase
- Compliance restored

### 6-12 Months
- Complete RHEL 8.x to RHEL 9.x migrations
- Establish ongoing lifecycle tracking and automation
- Implement quarterly update schedule

---

## Appendix: Product Lifecycle Data Sources

- Red Hat RHEL Lifecycle: https://access.redhat.com/product-life-cycles/?product=Red%20Hat%20Enterprise%20Linux
- OpenShift Lifecycle: https://access.redhat.com/support/policy/updates/openshift
- AAP Lifecycle: https://access.redhat.com/support/policy/updates/ansible-automation-platform
- Satellite Lifecycle: https://access.redhat.com/support/policy/updates/satellite

---

*Report Generated: May 25, 2026*  
*Classification: Internal Use - Infrastructure Planning*
