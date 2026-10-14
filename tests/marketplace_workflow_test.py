#!/usr/bin/env python3
"""Interactive end-to-end workflow test for the FastAPI marketplace.

Uses Python's standard library only. Before making changes, it logs in all four
roles, checks their profiles, lists the seller's in-stock products and delivery
postal codes, then asks for explicit confirmation. If confirmed, it creates a
BUY-NOW test order, advances the seller item through confirmed/shipped, assigns
an agent, and advances delivery through picked_up/out_for_delivery/delivered.

WARNING: This creates a persistent order and decreases stock by one. It uses a
clearly marked TEST / DO NOT SHIP address, but it does not delete the order.
Run only against a development/test database.
"""
from __future__ import annotations

import getpass
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

BASE_URL = os.getenv("MARKETPLACE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT_SECONDS = 20
EXPECTED_ROLES = {
    "customer": "customer",
    "seller": "seller",
    "admin": "admin",
    "delivery agent": "delivery_agent",
}
DEFAULT_EMAILS = {
    "customer": "user@exampl.com",
    "seller": "seller1@example.com",
    "admin": "admin@test.com",
    "delivery agent": "deliveryagent@test.com",
}


@dataclass
class Response:
    status: int
    body: Any
    raw: str


class WorkflowError(RuntimeError):
    pass


def request(method: str, path: str, *, payload: Any = None, token: str | None = None) -> Response:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            code = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        code = exc.code
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise WorkflowError(f"Could not reach {BASE_URL + path}: {exc}") from exc
    try:
        body = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        body = None
    return Response(code, body, raw)


def print_result(ok: bool, label: str, detail: str = "") -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {label}" + (f" — {detail}" if detail else ""))


def expect(response: Response, accepted: set[int], label: str) -> Response:
    if response.status not in accepted:
        detail = ""
        if isinstance(response.body, dict):
            detail = str(response.body.get("detail") or response.body.get("message") or "")
        if not detail:
            detail = response.raw[:250]
        print_result(False, label, f"HTTP {response.status}" + (f": {detail}" if detail else ""))
        raise WorkflowError(f"Stopped at {label}. No further workflow steps were run.")
    print_result(True, label, f"HTTP {response.status}")
    return response


def login(role_label: str, expected_role: str) -> tuple[str, dict[str, Any]]:
    default = DEFAULT_EMAILS[role_label]
    email = input(f"{role_label.title()} email [{default}]: ").strip() or default
    password = getpass.getpass(f"{role_label.title()} password (input hidden): ")
    if not email or not password:
        raise WorkflowError(f"Email/password missing for {role_label}.")
    response = request("POST", "/login", payload={"email": email, "password": password})
    expect(response, {200}, f"POST /login ({role_label})")
    token = response.body.get("access_token") if isinstance(response.body, dict) else None
    if not isinstance(token, str) or not token:
        raise WorkflowError(f"Login response for {role_label} contained no access_token.")
    profile_response = expect(request("GET", "/customers/me", token=token), {200}, f"GET /customers/me ({role_label})")
    profile = profile_response.body
    if not isinstance(profile, dict) or profile.get("role") != expected_role:
        actual = profile.get("role") if isinstance(profile, dict) else "unreadable profile"
        raise WorkflowError(f"Expected role {expected_role!r} for {role_label}, got {actual!r}. No order has been created yet.")
    print_result(True, f"Role check ({role_label})", f"role={expected_role}, id={profile.get('id')}")
    return token, profile


def extract_list(body: Any, label: str, keys: tuple[str, ...] = ("items", "service_areas", "data", "results")) -> list[dict[str, Any]]:
    if isinstance(body, list):
        return [x for x in body if isinstance(x, dict)]
    if isinstance(body, dict):
        for key in keys:
            value = body.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    raise WorkflowError(f"Unexpected response shape from {label}; expected a list of objects.")


def main() -> int:
    created_order_id: int | None = None
    print(f"Marketplace workflow integration test: {BASE_URL}")
    print("This will create a test order and reduce the chosen seller-product stock by 1.")
    print("Use only a development/test database. No real shipment is intended.\n")

    try:
        # Authenticate and verify all four roles before any data is changed.
        customer_token, customer = login("customer", EXPECTED_ROLES["customer"])
        seller_token, seller = login("seller", EXPECTED_ROLES["seller"])
        admin_token, admin = login("admin", EXPECTED_ROLES["admin"])
        agent_token, agent = login("delivery agent", EXPECTED_ROLES["delivery agent"])

        if not all(isinstance(x, int) for x in (customer.get("id"), seller.get("id"), admin.get("id"), agent.get("id"))):
            raise WorkflowError("A profile did not return a numeric id. No order has been created.")

        # Discover active seller products with stock available.
        product_response = expect(request("GET", "/seller-products/", token=seller_token), {200}, "GET /seller-products/")
        products = extract_list(product_response.body, "GET /seller-products/")
        candidates = [p for p in products if p.get("is_active") is True and isinstance(p.get("stock"), int) and p["stock"] > 0 and isinstance(p.get("seller_product_id"), int)]
        if not candidates:
            raise WorkflowError("The seller has no active products with stock > 0. No order has been created.")

        # A seller must support the postal code used for the test delivery.
        area_response = expect(request("GET", "/seller/service-areas/", token=seller_token), {200}, "GET /seller/service-areas/")
        areas = extract_list(area_response.body, "GET /seller/service-areas/")
        postal_codes = sorted({str(a.get("postal_code")).strip() for a in areas if a.get("postal_code") is not None and str(a.get("postal_code")).strip()})
        if not postal_codes:
            raise WorkflowError("No postal_code could be read from seller service areas. No order has been created.")

        print("\nActive seller products with stock:")
        for i, p in enumerate(candidates, start=1):
            print(f"  {i}. {p.get('name', '(unnamed)')} | seller_product_id={p['seller_product_id']} | SKU={p.get('sku')} | price={p.get('price')} | stock={p['stock']}")
        while True:
            raw_choice = input(f"Choose a product number (1-{len(candidates)}): ").strip()
            try:
                choice = int(raw_choice)
                if 1 <= choice <= len(candidates):
                    product = candidates[choice - 1]
                    break
            except ValueError:
                pass
            print("Enter one of the listed numbers.")

        print("\nSeller delivery postal codes:")
        for i, postal in enumerate(postal_codes, start=1):
            print(f"  {i}. {postal}")
        while True:
            raw_choice = input(f"Choose a serviceable postal code (1-{len(postal_codes)}): ").strip()
            try:
                choice = int(raw_choice)
                if 1 <= choice <= len(postal_codes):
                    postal_code = postal_codes[choice - 1]
                    break
            except ValueError:
                pass
            print("Enter one of the listed numbers.")

        print("\nPlanned test order:")
        print(f"  Customer: {customer.get('email')} (id={customer.get('id')})")
        print(f"  Seller: {seller.get('email')} (id={seller.get('id')})")
        print(f"  Product: {product.get('name')} (seller_product_id={product['seller_product_id']})")
        print(f"  Quantity: 1; current stock: {product['stock']} (stock will decrease by 1)")
        print(f"  Test delivery postal code: {postal_code}")
        print("  Address line: AUTOMATED API WORKFLOW TEST - DO NOT SHIP")
        print("  The order and delivery records will remain in the database after the test.")
        confirmation = input("To create this persistent test order, type CREATE TEST ORDER: ").strip()
        if confirmation != "CREATE TEST ORDER":
            print("Cancelled before creating an order. No marketplace data was changed.")
            return 0

        # Buy-now avoids adding items to, or removing items from, the customer's existing cart.
        payload = {
            "seller_product_id": product["seller_product_id"],
            "quantity": 1,
            "latitude": 0.0,
            "longitude": 0.0,
            "address_line": "AUTOMATED API WORKFLOW TEST - DO NOT SHIP",
            "city": "Workflow Test City",
            "state": "Test State",
            "postal_code": postal_code,
        }
        order_resp = expect(request("POST", "/order/buy-now", payload=payload, token=customer_token), {200, 201}, "POST /order/buy-now")
        order_body = order_resp.body if isinstance(order_resp.body, dict) else {}
        created_order_id = order_body.get("order_id")
        if not isinstance(created_order_id, int):
            raise WorkflowError("Buy-now response did not contain order_id. Check the API response and database before retrying.")
        print_result(True, "Test order created", f"order_id={created_order_id}; initial status={order_body.get('status')}")

        # Find the generated order_item_id using the customer's order detail endpoint.
        detail_resp = expect(request("GET", f"/order/{created_order_id}", token=customer_token), {200}, "GET /order/{order_id} (customer)")
        detail = detail_resp.body if isinstance(detail_resp.body, dict) else {}
        items = detail.get("items") if isinstance(detail.get("items"), list) else []
        matching_items = [item for item in items if isinstance(item, dict) and isinstance(item.get("order_item_id"), int)]
        if len(matching_items) != 1:
            raise WorkflowError(f"Expected one order item for order {created_order_id}; found {len(matching_items)}.")
        order_item_id = matching_items[0]["order_item_id"]

        # Seller lifecycle: pending -> confirmed -> shipped.
        for item_status in ("confirmed", "shipped"):
            resp = expect(
                request("PATCH", f"/order/items/{order_item_id}/status", payload={"status": item_status}, token=seller_token),
                {200}, f"PATCH /order/items/{order_item_id}/status -> {item_status}",
            )
            returned = resp.body.get("status") if isinstance(resp.body, dict) else None
            if returned != item_status:
                raise WorkflowError(f"Seller status response mismatch: expected {item_status!r}, got {returned!r}.")
            print_result(True, "Verify seller item status", returned)

        # Admin assigns the shipped order to the delivery agent.
        assign_resp = expect(
            request("POST", f"/orders/{created_order_id}/assign-delivery", payload={"delivery_agent_id": agent["id"]}, token=admin_token),
            {201}, f"POST /orders/{created_order_id}/assign-delivery",
        )
        assignment = assign_resp.body if isinstance(assign_resp.body, dict) else {}
        if assignment.get("status") != "assigned":
            raise WorkflowError(f"Expected assignment status 'assigned', got {assignment.get('status')!r}.")
        print_result(True, "Verify delivery assignment", f"assignment_id={assignment.get('id')}, status=assigned")

        # Delivery status state machine: assigned -> picked_up -> out_for_delivery -> delivered.
        for delivery_status in ("picked_up", "out_for_delivery", "delivered"):
            resp = expect(
                request("PATCH", f"/orders/{created_order_id}/delivery-status", payload={"status": delivery_status}, token=agent_token),
                {200}, f"PATCH /orders/{created_order_id}/delivery-status -> {delivery_status}",
            )
            body = resp.body if isinstance(resp.body, dict) else {}
            if body.get("status") != delivery_status:
                raise WorkflowError(f"Delivery status response mismatch: expected {delivery_status!r}, got {body.get('status')!r}.")
            print_result(True, "Verify delivery status", delivery_status)

        # Final customer-visible consistency check.
        final_resp = expect(request("GET", f"/order/{created_order_id}", token=customer_token), {200}, "GET final order detail")
        final_body = final_resp.body if isinstance(final_resp.body, dict) else {}
        if final_body.get("status") != "delivered":
            raise WorkflowError(f"Expected final order status 'delivered', got {final_body.get('status')!r}.")
        if final_body.get("delivery_status") != "delivered":
            raise WorkflowError(f"Expected final delivery_status 'delivered', got {final_body.get('delivery_status')!r}.")
        print_result(True, "Final customer order state", f"order={final_body.get('status')}; delivery={final_body.get('delivery_status')}")

        print("\n=============== SUMMARY ===============")
        print("Result: WORKFLOW PASSED")
        print(f"Created test order ID: {created_order_id}")
        print(f"Created order item ID: {order_item_id}")
        print("The test order and delivery history remain in the database; product stock was reduced by one.")
        print("The address is explicitly marked as an automated test / DO NOT SHIP.")
        return 0

    except WorkflowError as exc:
        print(f"\n[STOP] {exc}")
        if created_order_id is not None:
            print(f"IMPORTANT: Test order {created_order_id} was already created. It and the stock change may remain; inspect it before rerunning.")
        print("Do not rerun blindly if a failure occurred after order creation, or you may create duplicate orders.")
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        if created_order_id is not None:
            print(f"Test order {created_order_id} may remain in the database; inspect it before rerunning.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
