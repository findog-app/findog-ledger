# Findog Ledger

<p align="center">
  <img src="frontend/public/assets/images/findog-logo.svg" alt="Findog Ledger" width="280" />
</p>

<p align="center"><strong>A calm, self-hosted home for recurring payments and obligations.</strong></p>

> **Early development:** Findog Ledger is actively evolving. The core ledger,
> category, obligation, and access-control workflows are usable, while
> integrations, automation, analytics, and parts of the product experience are
> still being shaped.

Findog Ledger is a self-hosted application for keeping recurring household or
small-team obligations under control. It is deliberately not another banking
or budgeting dashboard: the central object is an **obligation** — something
that needs to be known, prepared, paid, and eventually closed.

You keep control of the application and its data, can share a ledger with other
users, and can progressively automate data collection through the API without
making external integrations part of the core application.

## What it does today

- Organises recurring costs into category groups and categories.
- Uses categories as templates for creating obligations for billing periods.
- Creates and tracks obligations through an explicit lifecycle.
- Supports shared ledgers with owner, editor, and viewer access.
- Highlights upcoming and overdue payments while keeping completed obligations
  clearly separated.
- Stores structured, category-specific data alongside obligations.
- Supports obligation components, so a total can be represented by individual
  items such as invoices or charge components.
- Exposes API operations intended for external integrations and automation.
- Supports scoped API keys for machine-to-machine access to a ledger.

For the precise obligation-state rules and available lifecycle actions, see the
[obligation lifecycle](docs/obligation-lifecycle.md).

## Core concepts

### Ledger

A ledger is the shared workspace. It owns categories and obligations and defines
who can access them.

### Category

A category describes a recurring type of obligation. Categories belong to
category groups and provide the metadata used when obligations are created.
They can also define a schema for structured data collected for that type of
obligation.

### Obligation

An obligation represents one concrete payment or responsibility for a billing
period. Its lifecycle separates incomplete data from an item that is ready to
pay, paid, canceled, or reopened.

### Components and structured data

Not every obligation is just a single amount. Components allow an obligation to
carry a breakdown of its total, while category-defined structured data can hold
domain-specific information such as invoice details, consumption, readings, or
other integration-provided values.

## Automation and integrations

Findog Ledger is designed so integrations can live outside the main
application. A mail processor, provider-specific scraper, or scheduled job can
use the API instead of being coupled to the backend.

The integration surface is built around ledger-scoped API keys and explicit
obligation operations. This keeps the core application useful on its own while
allowing automation to be added incrementally.

The Python client is maintained separately in the
[`findog-client-python`](https://github.com/findog-app/findog-client-python)
repository and is generated from the Ledger OpenAPI specification.

## Screenshots

The UI is still moving quickly, so screenshots are intentionally postponed
until the main desktop and mobile navigation settles.

## Run it yourself

The production setup is designed for a self-hosted Docker Compose deployment.
It uses prebuilt container images, an externally managed PostgreSQL database,
and an existing reverse proxy network named `firefly_net`.

Before starting, make sure your server has Docker Compose, access to PostgreSQL,
and a reverse proxy that can route your chosen frontend and API hostnames to
the `findog-ledger-frontend` and `findog-ledger-backend` aliases on that
network.

### Install

Create a deployment directory and run the installer. There is no need to clone
the application source code.

```bash
mkdir findog-ledger
cd findog-ledger
curl -fsSL https://raw.githubusercontent.com/findog-app/findog-ledger/main/scripts/install.sh | bash
```

The installer downloads the production Compose file and environment template.

Then:

1. Edit `.env` and set the values for your deployment. At minimum, choose an
   immutable image `TAG`, public URLs, PostgreSQL credentials, a random
   `SECRET_KEY`, and the first administrator account.
2. Ensure the external Docker network exists and configure your reverse proxy
   to forward the frontend and API hostnames to the aliases above.
3. Pull and start the stack. The `prestart` service runs database migrations
   before the application starts.

```bash
docker compose pull
docker compose up -d
```

Confirm that the services are healthy, then open the frontend URL configured in
`.env`.

```bash
docker compose ps
```

### Upgrade

Change `TAG` to the desired immutable release and run:

```bash
docker compose pull
docker compose up -d
```

Keep database backups and migration compatibility in mind before rolling a
version back.

## Project status

Findog Ledger is currently an early-stage project rather than a finished
consumer product. The direction is to keep the core ledger small and predictable
while building richer UX, external integrations, reporting, and automation on
top of it.

The project is developed in public under the
[`findog-app`](https://github.com/findog-app) GitHub organisation.
