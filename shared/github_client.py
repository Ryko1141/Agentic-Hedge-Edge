"""
Hedge Edge — GitHub Client
━━━━━━━━━━━━━━━━━━━━━━━━━━
GitHub REST API — repos, issues, PRs, releases.
Docs: https://docs.github.com/en/rest

Usage:
    from shared.github_client import list_repos, create_issue, create_release
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ws_root, ".env"))

BASE_URL = "https://api.github.com"


def _headers() -> dict:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN must be set in .env")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_user() -> dict:
    """Get authenticated user info."""
    r = requests.get(f"{BASE_URL}/user", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def list_repos(per_page: int = 30) -> list[dict]:
    """List repos for authenticated user."""
    r = requests.get(
        f"{BASE_URL}/user/repos",
        headers=_headers(),
        params={"per_page": per_page, "sort": "updated"},
        timeout=10,
    )
    r.raise_for_status()
    return [
        {
            "name": repo["full_name"],
            "private": repo["private"],
            "url": repo["html_url"],
            "updated": repo["updated_at"],
        }
        for repo in r.json()
    ]


def list_issues(owner: str, repo: str, state: str = "open") -> list[dict]:
    """List issues for a repo."""
    r = requests.get(
        f"{BASE_URL}/repos/{owner}/{repo}/issues",
        headers=_headers(),
        params={"state": state, "per_page": 50},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def create_issue(owner: str, repo: str, title: str, body: str = "",
                 labels: list[str] = None) -> dict:
    """Create a new issue."""
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    r = requests.post(
        f"{BASE_URL}/repos/{owner}/{repo}/issues",
        headers=_headers(),
        json=payload,
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def list_releases(owner: str, repo: str) -> list[dict]:
    """List releases for a repo."""
    r = requests.get(
        f"{BASE_URL}/repos/{owner}/{repo}/releases",
        headers=_headers(),
        params={"per_page": 10},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def create_release(owner: str, repo: str, tag: str, name: str,
                   body: str = "", draft: bool = False, prerelease: bool = False) -> dict:
    """Create a new release."""
    r = requests.post(
        f"{BASE_URL}/repos/{owner}/{repo}/releases",
        headers=_headers(),
        json={
            "tag_name": tag,
            "name": name,
            "body": body,
            "draft": draft,
            "prerelease": prerelease,
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def list_pull_requests(owner: str, repo: str, state: str = "open") -> list[dict]:
    """List pull requests."""
    r = requests.get(
        f"{BASE_URL}/repos/{owner}/{repo}/pulls",
        headers=_headers(),
        params={"state": state, "per_page": 30},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def get_repo_stats(owner: str, repo: str) -> dict:
    """Get repo overview stats."""
    r = requests.get(f"{BASE_URL}/repos/{owner}/{repo}", headers=_headers(), timeout=10)
    r.raise_for_status()
    data = r.json()
    return {
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "open_issues": data["open_issues_count"],
        "language": data["language"],
        "updated": data["updated_at"],
    }
