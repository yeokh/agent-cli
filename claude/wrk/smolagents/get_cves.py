import urllib.request
import json

cves = ["CVE-2019-3856", "CVE-2023-48795", "CVE-2026-46300", "CVE-2026-31431"]

for cve in cves:
    url = f"https://access.redhat.com/hydra/rest/securitydata/cve/{cve}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print(f"=== {cve} ===")
            print("Severity:", data.get("threat_severity"))
            print("CVSS3:", data.get("cvss3", {}).get("cvss3_base_score"))
            print("CVSS3 Vector:", data.get("cvss3", {}).get("cvss3_scoring_vector"))
            
            # Let's see package state for Red Hat Enterprise Linux 7
            package_state = data.get("package_state", [])
            rhel7_state = [p for p in package_state if "enterprise_linux:7" in p.get("product_name", "")]
            if rhel7_state:
                print("Package State for RHEL 7:")
                for p in rhel7_state:
                    print(f"  - {p.get('package_name')}: {p.get('state')}")
            
            affected_release = data.get("affected_release", [])
            rhel7_rel = [r for r in affected_release if "enterprise_linux:7" in r.get("product_name", "")]
            if rhel7_rel:
                print("Affected Releases for RHEL 7:")
                for r in rhel7_rel:
                    print(f"  - {r.get('package')}: {r.get('advisory')} (Release Date: {r.get('release_date')})")
    except Exception as e:
        print(f"Error {cve}: {e}")
