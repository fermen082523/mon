from __future__ import annotations

from typing import Any

import requests

from src.config.settings import AppSettings


class SupabaseSync:
    def __init__(self, settings: AppSettings) -> None:
        self._base_url = settings.supabase_url.rstrip("/")
        self._api_key = settings.supabase_key
        self._orders_table = settings.supabase_orders_table
        self._audit_table = settings.supabase_audit_table

    @property
    def enabled(self) -> bool:
        return bool(self._base_url and self._api_key)

    def _headers(self, prefer: str) -> dict[str, str]:
        return {
            "apikey": self._api_key,
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Prefer": prefer,
        }

    def _post(self, table: str, payload: list[dict[str, Any]], upsert: bool) -> None:
        if not self.enabled or not payload:
            return

        prefer = "return=minimal"
        params: dict[str, str] = {}
        if upsert:
            prefer = "resolution=merge-duplicates,return=minimal"
            params["on_conflict"] = "local_id"

        response = requests.post(
            f"{self._base_url}/rest/v1/{table}",
            json=payload,
            headers=self._headers(prefer),
            params=params,
            timeout=20,
        )
        response.raise_for_status()

    def upsert_orders(self, payload: list[dict[str, Any]]) -> None:
        self._post(self._orders_table, payload, upsert=True)

    def insert_audits(self, payload: list[dict[str, Any]]) -> None:
        self._post(self._audit_table, payload, upsert=True)