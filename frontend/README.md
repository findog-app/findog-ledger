# Findog Ledger - Frontend

React/Vite frontend for Findog Ledger. It uses Bun; run the following commands from the repository root.

## Requirements

- [Bun](https://bun.sh/)

## Quick Start

```bash
bun install --frozen-lockfile
bun run --filter frontend dev
```

Open <http://localhost:5173>. The local dev server is the recommended frontend workflow; Docker Compose is useful for testing the full stack.

## Generate Client

### Automatically

* Activate the backend virtual environment.
* From the top level project directory, run the script:

```bash
bash ./scripts/generate-client.sh
```

* Commit the changes.

### Manually

* Start the Docker Compose stack.

* Download the OpenAPI JSON file from `http://localhost/api/v1/openapi.json` and copy it to a new file `openapi.json` at the root of the `frontend` directory.

* To generate the frontend client, run:

```bash
bun run --filter frontend generate-client
```

* Commit the changes.

Notice that every time the backend OpenAPI schema changes, you should regenerate the frontend client.

## Current Frontend Scope

- No public signup flow.
- Admin user management is limited to superusers.
- Ledger, membership sharing, and category management are available.

## End-to-End Testing with Playwright

The frontend includes initial end-to-end tests using Playwright. To run the tests, you need to have the Docker Compose stack running. Start the stack with the following command:

```bash
docker compose up -d --wait backend
```

Then, you can run the tests with the following command:

```bash
bun run --filter frontend test
```

You can also run your tests in UI mode to see the browser and interact with it running:

```bash
bun run --filter frontend test:ui
```

To stop and remove the Docker Compose stack and clean the data created in tests, use the following command:

```bash
docker compose down -v
```

To update the tests, navigate to the tests directory and modify the existing test files or add new ones as needed.

For more information on writing and running Playwright tests, refer to the official [Playwright documentation](https://playwright.dev/docs/intro).
