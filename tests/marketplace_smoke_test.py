
#!/usr/bin/env python3
"""Read-only smoke tests for a running FastAPI marketplace API.

Only performs GET requests plus POST /login. It does not create, update,
or delete marketplace data. Uses Python's standard library only.
"""
from __future__ import annotations

import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

BASE_URL = os.getenv("MARKETPLACE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT_SECONDS = 15


@dataclass
class Response:
    status: int
    body: Any
    raw: str


def request(method: str, path: str, *, payload: Any = None, token: str | None = None) -> Response:
    url = BASE_URL + path
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Could not reach {url}: {exc}") from exc

    try:
        body = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        body = None
    return Response(status=status, body=body, raw=raw)


results: list[tuple[str, str, str]] = []


def record(status: str, label: str, detail: str = "") -> None:
    results.append((status, label, detail))
    icon = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP"}.get(status, status)
    suffix = f" — {detail}" if detail else ""
    print(f"[{icon}] {label}{suffix}")


def login_for_token() -> str | None:
    email = os.getenv("MARKETPLACE_TEST_EMAIL") or input("Existing test-account email: ").strip()
    password = os.getenv("MARKETPLACE_TEST_PASSWORD") or getpass.getpass("Password (input hidden): ")
    if not email or not password:
        record("FAIL", "POST /login", "Email/password were not provided")
        return None
    try:
        response = request("POST", "/login", payload={"email": email, "password": password})
    except RuntimeError as exc:
        record("FAIL", "POST /login", str(exc))
        return None
    if response.status != 200:
        # Intentionally do not print credentials or full response details.
        detail = f"HTTP {response.status}; check that the supplied test-account credentials are correct"
        record("FAIL", "POST /login", detail)
        return None
    token = response.body.get("access_token") if isinstance(response.body, dict) else None
    if not isinstance(token, str) or not token:
        record("FAIL", "POST /login", "HTTP 200 but response did not contain access_token")
        return None
    record("PASS", "POST /login", "Received an access token (not displayed)")
    return token


def main() -> int:
    print(f"Marketplace async API smoke test: {BASE_URL}")
    print("Safety: read-only GET requests plus POST /login; no order/cart/product mutations.\n")

    # Basic application and database checks.
    for path, label in [("/", "GET /"), ("/db-test", "GET /db-test"), ("/openapi.json", "GET /openapi.json")]:
        try:
            response = request("GET", path)
        except RuntimeError as exc:
            record("FAIL", label, str(exc))
            print("\nThe API is unreachable. Ensure uvicorn is running in the other terminal.")
            return summarize()
        if response.status != 200:
            record("FAIL", label, f"HTTP {response.status}")
            continue
        if path == "/db-test":
            if isinstance(response.body, dict) and response.body.get("database") and response.body.get("schema"):
                record("PASS", label, f"database={response.body['database']}, schema={response.body['schema']}")
            else:
                record("FAIL", label, "Expected JSON fields 'database' and 'schema'")
        elif path == "/openapi.json":
            if isinstance(response.body, dict) and isinstance(response.body.get("paths"), dict):
                record("PASS", label, "OpenAPI document loaded")
                openapi = response.body
            else:
                record("FAIL", label, "Response is not a valid OpenAPI document")
                openapi = {}
        else:
            record("PASS", label, "HTTP 200")

    if not locals().get("openapi"):
        print("\nCould not discover endpoints from OpenAPI; stopping route discovery.")
        return summarize()

    token = login_for_token()
    if token:
        try:
            profile = request("GET", "/customers/me", token=token)
            if profile.status == 200 and isinstance(profile.body, dict):
                expected = {"id", "name", "email", "phone", "role"}
                missing = sorted(expected - set(profile.body))
                if not missing:
                    record("PASS", "GET /customers/me", f"authenticated profile returned role={profile.body.get('role')!s}")
                else:
                    record("FAIL", "GET /customers/me", f"Missing fields: {', '.join(missing)}")
            else:
                record("FAIL", "GET /customers/me", f"HTTP {profile.status}; authentication/profile check failed")
        except RuntimeError as exc:
            record("FAIL", "GET /customers/me", str(exc))

    # Discover safe GET operations with no path parameters and no required query parameters.
    candidates: list[tuple[str, bool]] = []
    explicit = {"/", "/db-test", "/openapi.json", "/customers/me"}
    for path, path_item in openapi.get("paths", {}).items():
        if path in explicit or "{" in path or "}" in path:
            continue
        operation = path_item.get("get") if isinstance(path_item, dict) else None
        if not isinstance(operation, dict):
            continue
        parameters = operation.get("parameters", []) or []
        required_query = [
            p.get("name", "?") for p in parameters
            if p.get("in") == "query" and p.get("required") is True
        ]
        if required_query:
            record("SKIP", f"GET {path}", f"required query parameters: {', '.join(required_query)}")
            continue
        operation_security = operation.get("security", openapi.get("security", []))
        needs_auth = bool(operation_security)
        candidates.append((path, needs_auth))

    seen: set[str] = set()
    for path, needs_auth in candidates:
        if path in seen:
            continue
        seen.add(path)
        label = f"GET {path}"
        if needs_auth and not token:
            record("SKIP", label, "authentication token unavailable")
            continue
        try:
            response = request("GET", path, token=token)
        except RuntimeError as exc:
            record("FAIL", label, str(exc))
            continue

        if 200 <= response.status < 300:
            if not isinstance(response.body, (dict, list)) and response.raw:
                record("FAIL", label, "Expected a JSON response")
            elif path.rstrip("/") == "/products" and isinstance(response.body, dict):
                missing = {"items", "limit", "offset", "has_next"} - set(response.body)
                if missing:
                    record("FAIL", label, f"Product list response missing: {', '.join(sorted(missing))}")
                else:
                    record("PASS", label, f"Product listing schema valid; {len(response.body['items'])} item(s) returned")
            else:
                record("PASS", label, f"HTTP {response.status}")
        elif response.status == 403:
            record("SKIP", label, "this account lacks the required role/permission")
        else:
            record("FAIL", label, f"HTTP {response.status}")

    print("\nNote: endpoints with path IDs (for example /order/{order_id}), required query parameters,")
    print("and write operations are not exercised by this safe smoke test.")
    return summarize()


def summarize() -> int:
    passed = sum(1 for status, _, _ in results if status == "PASS")
    failed = sum(1 for status, _, _ in results if status == "FAIL")
    skipped = sum(1 for status, _, _ in results if status == "SKIP")
    print("\n=============== SUMMARY ===============")
    print(f"PASS: {passed}   FAIL: {failed}   SKIP: {skipped}")
    if failed:
        print("Result: ATTENTION REQUIRED — review the FAIL lines above.")
        return 1
    print("Result: smoke checks completed without reported failures.")
    print("This is not a substitute for full integration tests or workflow tests.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(130)
