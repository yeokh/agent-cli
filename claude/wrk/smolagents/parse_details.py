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
            print("Threat Severity:", data.get("threat_severity"))
            print("CVSS3 Score:", data.get("cvss3", {}).get("cvss3_base_score"))
            print("Statement:", data.get("statement"))
            print("Mitigation:", data.get("mitigation"))
            print("Details:", data.get("details"))
            
            # Print RHEL 7 relevant info
            print("RHEL 7 package states:")
            for p in data.get("package_state", []):
                if any(x in p.get("product_name", "") for x in ["Enterprise Linux 7", "RHEL 7"]):
                    print(f"  Pkg: {p.get('package_name')}, State: {p.get('state')}, Fix State: {p.get('fix_state')}")
            
            print("RHEL 7 affected releases:")
            for r in data.get("affected_release", []):
                if any(x in r.get("product_name", "") for x in ["Enterprise Linux 7", "RHEL 7"]):
                    print(f"  Pkg: {r.get('package')}, Advisory: {r.get('advisory')}, Release Date: {r.get('release_date')}, CPE: {r.get('cpe')}")
                    
    except Exception as e:
        print(f"Error {cve}: {e}")
