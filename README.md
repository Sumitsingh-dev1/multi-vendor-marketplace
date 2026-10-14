# Multi-Vendor Marketplace Backend

A production-oriented REST API for a multi-vendor marketplace built with FastAPI.

## Project Overview

This project allows multiple sellers to manage products and inventory while customers can browse products, add items to a cart, place orders, and make payments.

## Planned Features

- User authentication with JWT
- Customer, seller, and admin roles
- Product and category management
- Product image uploads
- Inventory management
- Shopping cart
- Order management
- Payment integration
- Product reviews
- Search, filtering, and pagination
- Email notifications
- Redis caching
- Background tasks
- Automated testing
- Docker
- CI/CD
- Production deployment

## Security and account provisioning

Public `POST /customers` registration creates customer accounts only; role fields are rejected. Customers submit `POST /seller-applications/`, then an administrator reviews a pending application at `PATCH /seller-applications/{application_id}` with `approved` or `rejected`. Only approval grants seller access.

After applying migrations to a fresh database, manually provision the sole initial administrator with `python scripts/provision_first_admin.py`. It securely prompts for credentials and refuses if an administrator already exists.

Set `ENABLE_DB_TEST_ENDPOINT=true` only for local development. The minimal `/db-test` connectivity endpoint is not registered by default. `SMTP_TIMEOUT_SECONDS` defaults to 10; passwords require at least 8 characters.

## Order and inventory policy

Inventory is deducted atomically when an order is created and restored once when an eligible item is cancelled. `Idempotency-Key` is an optional request header for checkout and Buy Now, unique per customer and operation; a completed replay returns the original order.

## COD payments

Checkout defaults to `payment_method: "cod"` and calculates the due amount from persisted order-item prices. It creates one pending-collection COD payment in the same transaction as the order and stock deduction. An assigned delivery agent must move the shipment to `out_for_delivery`, then call `POST /payments/orders/{order_id}/collect-cod` with the exact integer-paise amount. Collection is recorded once; only after it is collected can that COD delivery be completed. Razorpay checkout remains unavailable until gateway order creation, signature verification, webhooks, retries, capture, and refund flows are fully configured and verified.

## Product reviews

Customers may create one review per delivered order item at `POST /products/{product_id}/reviews`; server-side eligibility verifies the authenticated customer, product/listing match, and delivered item. Public reviews are listed at `GET /products/{product_id}/reviews`; customers manage their own reviews at `GET /reviews/me`, `PATCH /reviews/{review_id}`, and `DELETE /reviews/{review_id}`. Administrators can hide or restore a review with `PATCH /admin/reviews/{review_id}/visibility`. Hidden reviews are excluded from public lists and catalog rating summaries. Catalog ratings are aggregate queries over visible reviews. Migration `f2b5e8a7c430` follows `e7a4c1d8b920`.

## In-app notifications

Authenticated users read only their own notifications through `GET /notifications/me`, with `unread_only`, pagination, `GET /notifications/me/unread-count`, `PATCH /notifications/{id}/read`, and `PATCH /notifications/me/read-all`. Notifications cover supported order, seller-item, delivery, and COD-collection events. They are database-backed only: email, SMS, and push delivery are not included. Migration `a9c3d7e1f640` follows `f2b5e8a7c430`.

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Pydantic
- Alembic
- Redis
- Docker
- Pytest

## Project Status

🚧 Currently under development.
