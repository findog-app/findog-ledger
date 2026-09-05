# Oblidog - Frontend

React/Vite frontend for Oblidog. It uses Bun; run the following commands from the repository root.

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

The frontend includes end-to-end tests using Playwright. Run them in the dedicated, isolated Compose project:

```bash
make e2e
```

This project has its own Docker network and PostgreSQL volume, and does not publish the API port on the host. It can therefore run while `make dev-b` is serving the manual test environment.

To remove the isolated stack and its test data:

```bash
make e2e-down
```

To update the tests, navigate to the tests directory and modify the existing test files or add new ones as needed.

For more information on writing and running Playwright tests, refer to the official [Playwright documentation](https://playwright.dev/docs/intro).
