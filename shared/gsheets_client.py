"""
Hedge Edge — Google Sheets Client (OAuth2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Google Sheets API v4 — read, write, append, create spreadsheets.
Docs: https://developers.google.com/sheets/api/reference/rest

Usage:
    from shared.gsheets_client import read_range, append_rows, write_range
"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv

_ws_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_ws_root, ".env"))

BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"


def _get_access_token() -> str:
    """Get a fresh access token using the refresh token."""
    client_id = os.getenv("GOOGLE_SHEETS_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_SHEETS_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_SHEETS_REFRESH_TOKEN")
    if not all([client_id, client_secret, refresh_token]):
        raise RuntimeError("Google Sheets OAuth credentials must be set in .env")

    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
    }


def read_range(spreadsheet_id: str, range_name: str) -> list[list]:
    """
    Read values from a sheet range.
    
    Args:
        spreadsheet_id: The spreadsheet ID from URL
        range_name: e.g., 'Sheet1!A1:D10'
    
    Returns:
        2D list of cell values
    """
    r = requests.get(
        f"{BASE_URL}/{spreadsheet_id}/values/{range_name}",
        headers=_headers(),
        timeout=10,
    )
    r.raise_for_status()
    return r.json().get("values", [])


def write_range(spreadsheet_id: str, range_name: str, values: list[list]) -> dict:
    """
    Write values to a sheet range (overwrites).
    
    Args:
        spreadsheet_id: Spreadsheet ID
        range_name: Target range, e.g., 'Sheet1!A1'
        values: 2D list of values
    """
    r = requests.put(
        f"{BASE_URL}/{spreadsheet_id}/values/{range_name}",
        headers=_headers(),
        params={"valueInputOption": "USER_ENTERED"},
        json={"values": values},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def append_rows(spreadsheet_id: str, range_name: str, values: list[list]) -> dict:
    """
    Append rows to a sheet (adds after last row with data).
    
    Args:
        spreadsheet_id: Spreadsheet ID
        range_name: Target sheet/range, e.g., 'Sheet1!A:D'
        values: 2D list of row values
    """
    r = requests.post(
        f"{BASE_URL}/{spreadsheet_id}/values/{range_name}:append",
        headers=_headers(),
        params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
        json={"values": values},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def create_spreadsheet(title: str, sheets: list[str] = None) -> dict:
    """
    Create a new spreadsheet.
    
    Args:
        title: Spreadsheet title
        sheets: Optional list of sheet names
    """
    payload = {"properties": {"title": title}}
    if sheets:
        payload["sheets"] = [
            {"properties": {"title": name}} for name in sheets
        ]
    r = requests.post(BASE_URL, headers=_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return {
        "id": r.json()["spreadsheetId"],
        "url": r.json()["spreadsheetUrl"],
    }


def get_spreadsheet_info(spreadsheet_id: str) -> dict:
    """Get spreadsheet metadata (title, sheets, etc.)."""
    r = requests.get(
        f"{BASE_URL}/{spreadsheet_id}",
        headers=_headers(),
        params={"fields": "properties,sheets.properties"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    return {
        "title": data["properties"]["title"],
        "sheets": [s["properties"]["title"] for s in data.get("sheets", [])],
    }
