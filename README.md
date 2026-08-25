# Findog Ledger

<p align="center">
  <img src="frontend/public/assets/images/findog-logo.svg" alt="Findog Ledger" width="280" />
</p>

<p align="center"><strong>A calm, self-hosted home for recurring payments and obligations.</strong></p>

> **Early development:** Findog Ledger is actively evolving. The data model and
> core workflow are usable, but integrations, automation, and parts of the
> product experience are still being shaped.

Findog Ledger helps a household or small team keep recurring bills in one
shared ledger. Instead of relying on a bank feed or a third-party financial
dashboard, you keep control of the application and its data: run it on your
own infrastructure, invite the people who need access, and decide how the
workflow should grow.

## What it does today

- Organises recurring costs into category groups and categories.
- Creates and tracks payment obligations for billing periods.
- Supports shared ledgers with owner, editor, and viewer access.
- Keeps an explicit workflow from collecting payment data to ready, paid,
  canceled, or reopened obligations.
- Highlights approaching and overdue payments, while keeping paid obligations
  clearly separate.

For the precise obligation-state rules, API actions, and planned integration
behaviour, see the [obligation lifecycle](docs/obligation-lifecycle.md).

## Screenshots

Screenshots will be added as the interface settles.

| Obligations workspace | Categories and groups |
| --- | --- |
| _Placeholder: `docs/screenshots/obligations-workspace.png`_ | _Placeholder: `docs/screenshots/categories-workspace.png`_ |

## Run it yourself

The production setup is designed for a self-hosted Docker Compose deployment.
It uses prebuilt container images, an externally managed PostgreSQL database,
and an existing reverse proxy network named `firefly_net`.

Before starting, make sure your server has Docker Compose, access to PostgreSQL,
and a reverse proxy that can route your chosen frontend and API hostnames to
the `findog-ledger-frontend` and `findog-ledger-backend` aliases on that
network.

1. Create a deployment directory and download the production files. There is no
   need to clone the application source code.

   ```bash
   mkdir findog-ledger
   cd findog-ledger
   curl -fsSL https://raw.githubusercontent.com/findog-app/findog-ledger/main/scripts/install.sh | bash
   ```

2. Edit `.env` and set the values for your deployment. At minimum, choose an
   immutable image `TAG`, public URLs, PostgreSQL credentials, a random
   `SECRET_KEY`, and the first administrator account.

3. Ensure the external Docker network exists and configure your reverse proxy
   to forward the public frontend and API hostnames to the aliases above.

4. Pull and start the stack. The `prestart` service runs database migrations
   before the application starts.

   ```bash
   docker compose pull
   docker compose up -d
   ```

5. Confirm that the services are healthy, then open the frontend URL from your
   `.env` file.

   ```bash
   docker compose ps
   ```

For later releases, change `TAG` to the desired immutable version and run the
same two Compose commands. Keep database backups and migration compatibility in
mind before rolling a version back.
