import urllib.request
import json

advisory = "RHSA-2019:0679"
url = f"https://access.redhat.com/hydra/rest/securitydata/errata/{advisory}.json"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("Keys:", list(data.keys()))
        print("Solution:", data.get("solution"))
        print("Synopsis:", data.get("synopsis"))
        print("Topic:", data.get("topic"))
        print("Description:", data.get("description"))
except Exception as e:
    print("Error:", e)
