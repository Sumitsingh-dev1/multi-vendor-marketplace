# Multi-Vendor Marketplace Backend

A backend REST API for a multi-vendor e-commerce marketplace built with **FastAPI, Python, and PostgreSQL**. The platform supports customer accounts, seller onboarding, product and inventory management, shopping carts, orders, COD payments, delivery assignments, reviews, notifications, and support tickets.

This project demonstrates backend development concepts including JWT authentication, role-based authorization, asynchronous database access, transactional inventory management, database migrations, and automated testing.

## Features

### Authentication and Account Security
- Customer registration and login using JWT authentication.
- Password hashing and validation.
- Role-based access control.
- Secure seller onboarding through administrator approval.
- Password reset functionality.
- Session invalidation following password changes.

### Seller Management
- Seller application submission and administrative review.
- Seller-specific product management.
- Inventory management.
- Seller service-area management.

### Product Catalog
- Product and category management.
- Product image upload support.
- Product reviews and ratings.
- Administrative review moderation.
- Aggregate ratings based on visible reviews.

### Shopping Cart and Orders
- Shopping cart management.
- Order creation and management.
- Atomic inventory deduction during order creation.
- Inventory restoration when an eligible item is cancelled.
- Checkout idempotency using the optional `Idempotency-Key` request header.
- Customer-specific order access.

### Payments
- Cash on Delivery (COD) checkout.
- Payment amounts calculated from persisted order-item prices.
- COD collection by an assigned delivery agent.
- Exact amount verification using integer paise.
- Duplicate collection prevention.
- COD delivery completion restricted until collection is recorded.

**Payment limitation:** Razorpay checkout is not yet available. Gateway order creation, signature verification, webhooks, capture, retries, and refund handling must be implemented and verified before gateway payments can be enabled.

### Delivery Management
- Delivery assignments.
- Delivery-agent access controls.
- Shipment status management.
- COD collection integrated with delivery workflows.

### Reviews and Ratings
- Review eligibility verified against delivered order items.
- One review per eligible order item.
- Customer review management.
- Administrative review visibility controls.
- Hidden reviews excluded from public review listings and catalog rating summaries.

### In-App Notifications
- User-specific notification access.
- Unread notification counts.
- Pagination and unread-only filtering.
- Individual and bulk read operations.
- Database-backed notifications for supported marketplace events.

Email, SMS, and push notification delivery are not included.

### Support Tickets
- Ticket creation by eligible customers, sellers, and delivery agents.
- Ticket messages and chronological message pagination.
- Ticket ownership enforcement.
- Administrative assignment, prioritization, filtering, and status management.
- Ticket reopening by owners.
- Restrictions on replies to closed tickets.
- Database-backed notifications for supported ticket events.

The support system is backend-only. It does not include a frontend, attachments, external help-desk integration, or email/SMS/push delivery.

## Technology Stack

- **Language:** Python
- **API framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Validation:** Pydantic
- **Database migrations:** Alembic
- **Testing:** pytest
- **Containerization:** Docker and Docker Compose

Redis is not described as an implemented feature in this README. Add it to the active technology stack only if the application currently uses it.

## Architecture

The application follows a layered backend structure:

- **API routes:** HTTP endpoints and request handling.
- **Schemas:** Request and response validation.
- **Models:** Database entities.
- **Services:** Business logic.
- **Dependencies:** Database sessions and authentication/authorization checks.
- **Migrations:** Version-controlled database schema changes.
- **Tests:** Unit and database-backed integration tests.

See the repository structure for the implementation details.

## Security and Account Provisioning

Public `POST /customers` registration creates customer accounts only. Role fields are rejected during registration.

Seller access is granted through an approval workflow:

1. A customer submits an application using `POST /seller-applications/`.
2. An administrator reviews the application using `PATCH /seller-applications/{application_id}`.
3. The administrator approves or rejects the application.
4. Seller access is granted only after approval.

After applying migrations to a fresh database, provision the initial administrator using:

```powershell
python scripts/provision_first_admin.py
```

The script securely prompts for credentials and refuses to create another administrator if one already exists.

The `/db-test` endpoint is not registered by default. Set `ENABLE_DB_TEST_ENDPOINT=true` only for local development.

Passwords require at least eight characters. The SMTP timeout defaults to ten seconds.

## Order and Inventory Consistency

Inventory is deducted atomically when an order is created and restored once when an eligible item is cancelled.

Checkout and Buy Now support the optional `Idempotency-Key` request header. Keys are unique per customer and operation; a completed replay returns the original order.

These mechanisms help prevent duplicate checkout processing and inconsistent inventory updates.

## Local Development with Docker

### Prerequisites

- Python
- Docker Desktop
- Git

### 1. Clone the repository

```powershell
git clone https://github.com/Sumitsingh-dev1/multi-vendor-marketplace.git
cd multi-vendor-marketplace
```

### 2. Configure environment variables

Copy the Docker environment template:

```powershell
Copy-Item .env.docker.example .env.docker
```

Edit `.env.docker` and replace the placeholder database password and secret values with secure local values.

**Never commit `.env`, `.env.docker`, or other files containing credentials or secrets.**

### 3. Start the application

Ensure Docker Desktop is running, then execute:

```powershell
docker compose --env-file .env.docker up --build
```

The Compose configuration starts the API and its PostgreSQL service. The application waits for PostgreSQL health and applies database migrations.

The API is bound to `127.0.0.1:8000`, and PostgreSQL is not exposed through a host port by the documented Compose configuration.

### 4. Open the API documentation

With the application running, visit:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

These interfaces allow you to explore the available endpoints and inspect request and response schemas.

### 5. Stop the application

```powershell
docker compose --env-file .env.docker down
```

Avoid adding `-v` unless you intentionally want to remove the Compose database volume and its stored data.

## Automated Testing

The project includes unit tests and opt-in database integration tests.

The Docker setup provides separate `marketplace_dev` and `marketplace_test` databases.

Run the integration test suite only against the isolated test database:

```powershell
docker compose --env-file .env.docker run --build --rm `
    -e DATABASE_URL="postgresql+asyncpg://marketplace:YOUR_PASSWORD@db:5432/marketplace_test" `
    -e RUN_DB_INTEGRATION_TESTS=1 `
    app python -m pytest -q
```

Replace `YOUR_PASSWORD` with the local Docker database password. Do not use a development or production database URL for tests.

The project has previously passed a Docker-backed test run, including authorization integration tests. Rerun the suite against the current code before publishing a new test result.

The legacy smoke and workflow scripts may contact a running API, create orders, or change inventory. Do not run them against a shared or production environment.

## Current Project Status

The core marketplace backend features have been implemented, including authentication, seller approval, product management, cart and order workflows, COD payments, delivery assignments, reviews, notifications, and support tickets.

The project includes Docker-based development and testing infrastructure.

Gateway payment integration, external notification delivery, a frontend, and production deployment are not claimed as completed features.

## Future Improvements

Potential next steps include:

- Razorpay integration with verified webhooks and refund handling.
- Email, SMS, or push notifications.
- Redis caching, if needed.
- Continuous integration and automated checks.
- Frontend development.
- Production deployment and monitoring.

## License

No license has been specified yet. Add a license file if you intend to distribute or reuse the project under explicit terms.