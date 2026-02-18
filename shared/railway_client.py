"""
Hedge Edge — Railway Client
━━━━━━━━━━━━━━━━━━━━━━━━━━━
GraphQL client for Railway deployment management.

Capabilities:
    • List services, environments, deployments
    • Read / update environment variables
    • Trigger redeployments, rollbacks
    • Query deployment logs and build status

Auth: Project-scoped token (RAILWAY_TOKEN).
API:  https://docs.railway.app/reference/public-api

Usage:
    from shared.railway_client import (
        list_services, list_deployments, get_variables,
        trigger_redeploy, get_deployment_logs,
    )
"""

import os, requests, json
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────
RAILWAY_URL = "https://backboard.railway.app/graphql/v2"
TOKEN       = os.getenv("RAILWAY_TOKEN", "")
PROJECT_ID  = os.getenv("RAILWAY_PROJECT_ID", "f2ec91a1-49d0-4acd-8374-37d737785fcd")
ENV_ID      = os.getenv("RAILWAY_ENVIRONMENT_ID", "4601f9f7-3520-4cd5-90f4-e73bf050b292")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type":  "application/json",
}


def _gql(query: str, variables: dict | None = None) -> dict:
    """Execute a Railway GraphQL query/mutation and return the data payload."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    r = requests.post(RAILWAY_URL, headers=HEADERS, json=payload, timeout=15)
    r.raise_for_status()
    body = r.json()
    if "errors" in body:
        raise RuntimeError(f"Railway API error: {json.dumps(body['errors'], indent=2)}")
    return body.get("data", {})


# ── Project ───────────────────────────────────────────

def get_project() -> dict:
    """Return project metadata (name, id, environments, services)."""
    q = """
    query($id: String!) {
      project(id: $id) {
        id name description createdAt updatedAt
        environments { edges { node { name id } } }
        services     { edges { node { name id } } }
      }
    }
    """
    return _gql(q, {"id": PROJECT_ID})["project"]


# ── Services ──────────────────────────────────────────

def list_services() -> list[dict]:
    """List all services in the project."""
    project = get_project()
    return [e["node"] for e in project["services"]["edges"]]


def list_environments() -> list[dict]:
    """List all environments in the project."""
    project = get_project()
    return [e["node"] for e in project["environments"]["edges"]]


# ── Deployments ───────────────────────────────────────

def list_deployments(
    service_id: str,
    environment_id: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    List recent deployments for a service.

    Returns list of dicts with: id, status, createdAt, staticUrl.
    """
    q = """
    query($input: DeploymentListInput!) {
      deployments(input: $input, first: %d) {
        edges {
          node {
            id status createdAt staticUrl
          }
        }
      }
    }
    """ % limit
    data = _gql(q, {"input": {
        "projectId":     PROJECT_ID,
        "serviceId":     service_id,
        "environmentId": environment_id or ENV_ID,
    }})
    return [e["node"] for e in data["deployments"]["edges"]]


def get_latest_deployment(service_id: str) -> dict | None:
    """Return the most recent deployment for a service, or None."""
    deploys = list_deployments(service_id, limit=1)
    return deploys[0] if deploys else None


def trigger_redeploy(
    service_id: str,
    environment_id: str | None = None,
) -> dict:
    """
    Trigger a redeployment of the latest deployment for a service.

    Returns the new deployment dict (id, status).
    """
    q = """
    mutation($input: ServiceInstanceRedeployInput!) {
      serviceInstanceRedeploy(input: $input)
    }
    """
    return _gql(q, {"input": {
        "serviceId":     service_id,
        "environmentId": environment_id or ENV_ID,
    }})


def restart_deployment(deployment_id: str) -> dict:
    """Restart a specific deployment."""
    q = """
    mutation($id: String!) {
      deploymentRestart(id: $id)
    }
    """
    return _gql(q, {"id": deployment_id})


def remove_deployment(deployment_id: str) -> bool:
    """Remove (take down) a deployment. Returns True on success."""
    q = """
    mutation($id: String!) {
      deploymentRemove(id: $id)
    }
    """
    _gql(q, {"id": deployment_id})
    return True


# ── Environment Variables ─────────────────────────────

def get_variables(
    service_id: str,
    environment_id: str | None = None,
) -> dict:
    """
    Return all environment variables for a service as a dict.

    WARNING: Values may contain secrets — handle with care.
    """
    q = """
    query($pid: String!, $sid: String!, $eid: String!) {
      variables(projectId: $pid, serviceId: $sid, environmentId: $eid)
    }
    """
    return _gql(q, {
        "pid": PROJECT_ID,
        "sid": service_id,
        "eid": environment_id or ENV_ID,
    })["variables"]


def upsert_variable(
    service_id: str,
    name: str,
    value: str,
    environment_id: str | None = None,
) -> bool:
    """Create or update an environment variable on a service."""
    q = """
    mutation($input: VariableCollectionUpsertInput!) {
      variableCollectionUpsert(input: $input)
    }
    """
    _gql(q, {"input": {
        "projectId":     PROJECT_ID,
        "serviceId":     service_id,
        "environmentId": environment_id or ENV_ID,
        "variables":     {name: value},
    }})
    return True


def delete_variable(
    service_id: str,
    name: str,
    environment_id: str | None = None,
) -> bool:
    """Delete an environment variable from a service."""
    q = """
    mutation($input: VariableDeleteInput!) {
      variableDelete(input: $input)
    }
    """
    _gql(q, {"input": {
        "projectId":     PROJECT_ID,
        "serviceId":     service_id,
        "environmentId": environment_id or ENV_ID,
        "name":          name,
    }})
    return True


# ── Deployment Logs ───────────────────────────────────

def get_deployment_logs(deployment_id: str, limit: int = 100) -> list[dict]:
    """
    Fetch build/deploy logs for a specific deployment.

    Returns list of log entries (message, timestamp, severity).
    """
    q = """
    query($id: String!, $limit: Int!) {
      deploymentLogs(deploymentId: $id, limit: $limit) {
        message timestamp severity
      }
    }
    """
    return _gql(q, {"id": deployment_id, "limit": limit}).get("deploymentLogs", [])


# ── Quick-Info Helper ─────────────────────────────────

def get_status_summary() -> dict:
    """
    Return a quick overview: project name, services, and latest deployment status.
    Useful for dashboards and health checks.
    """
    project  = get_project()
    services = [e["node"] for e in project["services"]["edges"]]
    summary  = {
        "project":      project["name"],
        "environments": [e["node"]["name"] for e in project["environments"]["edges"]],
        "services":     [],
    }
    for svc in services:
        latest = get_latest_deployment(svc["id"])
        summary["services"].append({
            "name":   svc["name"],
            "id":     svc["id"],
            "latest": latest["status"] if latest else "NO_DEPLOYMENTS",
            "url":    latest.get("staticUrl", "") if latest else "",
        })
    return summary
