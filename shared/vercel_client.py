"""
Hedge Edge — Vercel Client
━━━━━━━━━━━━━━━━━━━━━━━━━━
Vercel REST API — deployments, domains, analytics.
Docs: https://vercel.com/docs/rest-api

Usage:
    from shared.vercel_client import list_deployments, get_project, list_domains
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ws_root, ".env"))

BASE_URL = "https://api.vercel.com"


def _headers() -> dict:
    token = os.getenv("VERCEL_TOKEN")
    if not token:
        raise RuntimeError("VERCEL_TOKEN must be set in .env")
    return {"Authorization": f"Bearer {token}"}


def list_projects() -> list[dict]:
    """List all Vercel projects."""
    r = requests.get(f"{BASE_URL}/v9/projects", headers=_headers(), timeout=10)
    r.raise_for_status()
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "framework": p.get("framework"),
            "url": f"https://{p['targets']['production']['url']}" if p.get("targets", {}).get("production") else None,
            "updated": p.get("updatedAt"),
        }
        for p in r.json().get("projects", [])
    ]


def get_project(project_id: str) -> dict:
    """Get a specific project."""
    r = requests.get(f"{BASE_URL}/v9/projects/{project_id}", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def list_deployments(project_id: Optional[str] = None, limit: int = 10) -> list[dict]:
    """List recent deployments."""
    params = {"limit": limit}
    if project_id:
        params["projectId"] = project_id
    r = requests.get(f"{BASE_URL}/v6/deployments", headers=_headers(), params=params, timeout=10)
    r.raise_for_status()
    return [
        {
            "id": d["uid"],
            "url": d.get("url"),
            "state": d.get("state"),
            "created": d.get("created"),
            "target": d.get("target"),
        }
        for d in r.json().get("deployments", [])
    ]


def list_domains() -> list[dict]:
    """List all domains."""
    r = requests.get(f"{BASE_URL}/v5/domains", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json().get("domains", [])


def trigger_redeploy(deployment_id: str) -> dict:
    """Trigger a redeployment."""
    r = requests.post(
        f"{BASE_URL}/v13/deployments",
        headers={**_headers(), "Content-Type": "application/json"},
        json={"deploymentId": deployment_id},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()
