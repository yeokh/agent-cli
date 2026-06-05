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
            print("Full Keys:", list(data.keys()))
            if "package_state" in data:
                print("package_state len:", len(data["package_state"]))
                for p in data["package_state"]:
                    if "7" in p.get("product_name", ""):
                        print("  pkg_state:", p)
            if "affected_release" in data:
                print("affected_release len:", len(data["affected_release"]))
                for r in data["affected_release"]:
                    if "7" in r.get("product_name", ""):
                        print("  aff_rel:", r)
    except Exception as e:
        print(f"Error {cve}: {e}")
