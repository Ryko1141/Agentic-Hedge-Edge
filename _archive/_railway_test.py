import requests, json, os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("RAILWAY_TOKEN")
url = "https://backboard.railway.app/graphql/v2"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

PID = "f2ec91a1-49d0-4acd-8374-37d737785fcd"
SID = "efe8e881-564f-46b1-9fb0-deac7dc5deb6"
EID = "4601f9f7-3520-4cd5-90f4-e73bf050b292"

# 1. Deployments
q1 = """query {
  deployments(input: {
    projectId: "%s"
    serviceId: "%s"
    environmentId: "%s"
  }) {
    edges {
      node {
        id
        status
        createdAt
        staticUrl
      }
    }
  }
}""" % (PID, SID, EID)

r1 = requests.post(url, headers=headers, json={"query": q1}, timeout=10)
print("=== DEPLOYMENTS ===")
print(json.dumps(r1.json(), indent=2))

# 2. Variables (env var names only)
q2 = """query {
  variables(
    projectId: "%s"
    serviceId: "%s"
    environmentId: "%s"
  )
}""" % (PID, SID, EID)

r2 = requests.post(url, headers=headers, json={"query": q2}, timeout=10)
data2 = r2.json()
print("\n=== VARIABLES ===")
if "data" in data2 and data2["data"] and "variables" in data2["data"]:
    keys = list(data2["data"]["variables"].keys())
    print(f"Found {len(keys)} variables: {keys}")
else:
    print(json.dumps(data2, indent=2))

# 3. Service domains
q3 = """query {
  serviceDomains(
    projectId: "%s"
    serviceId: "%s"
    environmentId: "%s"
  ) {
    serviceDomains {
      domain
      id
    }
    customDomains {
      domain
      id
      status { dnsRecords { hostlabel type requiredValue } }
    }
  }
}""" % (PID, SID, EID)

r3 = requests.post(url, headers=headers, json={"query": q3}, timeout=10)
print("\n=== DOMAINS ===")
print(json.dumps(r3.json(), indent=2))
