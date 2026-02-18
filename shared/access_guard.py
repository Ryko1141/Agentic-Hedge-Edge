"""
Hedge Edge — Access Control Enforcement
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Guards that enforce agent permissions before API calls and Notion writes.
Wraps shared clients so agents cannot access resources outside their scope.

Usage:
    from shared.access_guard import guarded_add_row, guarded_query_db, require_api

    # In a Sales Agent script:
    guarded_add_row("sales", "leads_crm", {"Email": "x@y.com", "Source": "Discord"})  # ✅
    guarded_add_row("sales", "expense_log", {"Amount": 100})  # ❌ AccessDenied

    # Decorator for whole functions:
    @require_api("sales", "creem", "read")
    def lookup_customer(email):
        ...
"""

import os
import sys
import json
import functools
from datetime import datetime
from typing import Any, Callable, Optional

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ──────────────────────────────────────────────
# Exceptions
# ──────────────────────────────────────────────

class AccessDenied(PermissionError):
    """Raised when an agent tries to access a resource it doesn't have permission for."""
    def __init__(self, agent: str, resource: str, operation: str, detail: str = ""):
        self.agent = agent
        self.resource = resource
        self.operation = operation
        msg = f"ACCESS DENIED: agent '{agent}' cannot '{operation}' on '{resource}'"
        if detail:
            msg += f" — {detail}"
        super().__init__(msg)


# ──────────────────────────────────────────────
# Audit Log
# ──────────────────────────────────────────────

_AUDIT_LOG_PATH = os.path.join(_ws_root, ".audit_log.jsonl")

def _audit(agent: str, resource: str, operation: str, allowed: bool, detail: str = ""):
    """Append an entry to the audit log (JSONL file)."""
    entry = {
        "ts": datetime.now(tz=__import__('datetime').timezone.utc).isoformat(),
        "agent": agent,
        "resource": resource,
        "operation": operation,
        "allowed": allowed,
    }
    if detail:
        entry["detail"] = detail
    try:
        with open(_AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass  # Never crash on audit failure


# ──────────────────────────────────────────────
# Notion Database Access Guards
# ──────────────────────────────────────────────

def _check_db_access(agent: str, db_key: str, operation: str) -> None:
    """
    Check if agent can perform operation on a Notion database.
    Uses AGENT_ACCESS from notion_client.py.
    """
    from shared.notion_client import AGENT_ACCESS

    agent_perms = AGENT_ACCESS.get(agent)
    if agent_perms is None:
        _audit(agent, f"notion/{db_key}", operation, False, "unknown agent")
        raise AccessDenied(agent, f"notion/{db_key}", operation, "unknown agent")

    if operation == "write":
        allowed_dbs = agent_perms.get("write", [])
    elif operation == "read":
        allowed_dbs = agent_perms.get("read", []) + agent_perms.get("write", [])
    else:
        allowed_dbs = []

    if db_key not in allowed_dbs:
        _audit(agent, f"notion/{db_key}", operation, False)
        raise AccessDenied(agent, f"notion/{db_key}", operation)

    _audit(agent, f"notion/{db_key}", operation, True)


def guarded_add_row(agent: str, db_key: str, properties: dict[str, Any]) -> dict:
    """
    Add a row to a Notion database — only if the agent has write access.

    Args:
        agent: Agent key (e.g., 'finance', 'sales')
        db_key: DATABASES key (e.g., 'leads_crm')
        properties: Property dict passed to add_row()

    Raises:
        AccessDenied: If the agent doesn't have write access to this database.
    """
    _check_db_access(agent, db_key, "write")
    from shared.notion_client import add_row
    return add_row(db_key, properties)


def guarded_query_db(
    agent: str,
    db_key: str,
    filter: Optional[dict] = None,
    sorts: Optional[list[dict]] = None,
    page_size: int = 100,
) -> list[dict]:
    """
    Query a Notion database — only if the agent has read access.

    Args:
        agent: Agent key
        db_key: DATABASES key

    Raises:
        AccessDenied: If the agent doesn't have read access to this database.
    """
    _check_db_access(agent, db_key, "read")
    from shared.notion_client import query_db
    return query_db(db_key, filter=filter, sorts=sorts, page_size=page_size)


def guarded_update_row(
    agent: str,
    page_id: str,
    db_key: str,
    properties: dict[str, Any],
) -> dict:
    """
    Update a row in a Notion database — only if the agent has write access.
    """
    _check_db_access(agent, db_key, "write")
    from shared.notion_client import update_row
    return update_row(page_id, db_key, properties)


# ──────────────────────────────────────────────
# API Access Guard (Decorator)
# ──────────────────────────────────────────────

def require_api(agent: str, api: str, operation: str = "read") -> Callable:
    """
    Decorator: ensures the agent has permission to call this API.

    Usage:
        @require_api("sales", "creem", "read")
        def get_customer_info(email):
            return creem_client.get_customer(email)
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            from shared.api_registry import can_access
            if not can_access(agent, api, operation):
                _audit(agent, f"api/{api}", operation, False)
                raise AccessDenied(agent, f"api/{api}", operation)
            _audit(agent, f"api/{api}", operation, True)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def check_api_access(agent: str, api: str, operation: str = "read") -> None:
    """
    Imperative guard: raise AccessDenied if the agent can't access the API.

    Usage:
        check_api_access("marketing", "resend", "write")
        # ... proceed to use resend_client ...
    """
    from shared.api_registry import can_access
    if not can_access(agent, api, operation):
        _audit(agent, f"api/{api}", operation, False)
        raise AccessDenied(agent, f"api/{api}", operation)
    _audit(agent, f"api/{api}", operation, True)


# ──────────────────────────────────────────────
# Convenience: agent context manager
# ──────────────────────────────────────────────

class AgentSession:
    """
    Context manager that binds an agent identity for access checks.

    Usage:
        with AgentSession("sales") as sess:
            sess.add_row("leads_crm", {"Email": "a@b.com"})
            sess.query_db("leads_crm")
            sess.check_api("resend", "write")
    """

    def __init__(self, agent: str):
        self.agent = agent

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def add_row(self, db_key: str, properties: dict[str, Any]) -> dict:
        return guarded_add_row(self.agent, db_key, properties)

    def query_db(self, db_key: str, **kwargs) -> list[dict]:
        return guarded_query_db(self.agent, db_key, **kwargs)

    def update_row(self, page_id: str, db_key: str, properties: dict[str, Any]) -> dict:
        return guarded_update_row(self.agent, page_id, db_key, properties)

    def check_api(self, api: str, operation: str = "read") -> None:
        check_api_access(self.agent, api, operation)


# ──────────────────────────────────────────────
# CLI: view audit log / test access
# ──────────────────────────────────────────────

def _cli():
    import argparse
    parser = argparse.ArgumentParser(description="Hedge Edge Access Control")
    sub = parser.add_subparsers(dest="cmd")

    # Test access
    test_p = sub.add_parser("test", help="Test access: test <agent> <resource> <op>")
    test_p.add_argument("agent")
    test_p.add_argument("resource", help="api/<name> or notion/<db_key>")
    test_p.add_argument("operation", choices=["read", "write", "full"], default="read", nargs="?")

    # View audit log
    sub.add_parser("audit", help="Print recent audit log entries")

    # Matrix
    sub.add_parser("matrix", help="Print the full access matrix")

    args = parser.parse_args()

    if args.cmd == "test":
        res = args.resource
        try:
            if res.startswith("api/"):
                check_api_access(args.agent, res.split("/", 1)[1], args.operation)
            elif res.startswith("notion/"):
                _check_db_access(args.agent, res.split("/", 1)[1], args.operation)
            else:
                print(f"Resource must start with 'api/' or 'notion/'")
                sys.exit(1)
            print(f"  ✅  {args.agent} → {res} ({args.operation}) ALLOWED")
        except AccessDenied as e:
            print(f"  ❌  {e}")
            sys.exit(1)

    elif args.cmd == "audit":
        if not os.path.exists(_AUDIT_LOG_PATH):
            print("No audit log yet.")
            return
        with open(_AUDIT_LOG_PATH, encoding="utf-8") as f:
            lines = f.readlines()
        # Show last 20
        for line in lines[-20:]:
            entry = json.loads(line)
            icon = "✅" if entry["allowed"] else "❌"
            print(f"  {icon} [{entry['ts'][:19]}] {entry['agent']} → {entry['resource']} ({entry['operation']})")

    elif args.cmd == "matrix":
        from shared.api_registry import API_ACCESS
        from shared.notion_client import AGENT_ACCESS
        print("\n=== API Access Matrix ===")
        for api, agents in sorted(API_ACCESS.items()):
            agent_str = ", ".join(f"{a}({p})" for a, p in sorted(agents.items()))
            print(f"  {api}: {agent_str}")
        print("\n=== Notion Database Access ===")
        for agent, perms in sorted(AGENT_ACCESS.items()):
            w = ", ".join(perms.get("write", []))
            r = ", ".join(perms.get("read", []))
            print(f"  {agent}:")
            print(f"    write: {w}")
            print(f"    read:  {r}")

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
