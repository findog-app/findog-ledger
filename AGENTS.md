# Local environment safety

- `make dev-b` is the host development backend. It connects to the manual
  quasi-production test data through Mikr.us.
- `TEST_SQLALCHEMY_DATABASE_URI` intentionally points at the local Docker
  PostgreSQL instance and is safe for backend test cleanup.
- Never start the default Compose `backend` service while `make dev-b` is
  running. Both use the API port and the frontend can then reach the Docker
  backend and show local automated-test data instead of the host backend data.
- Do not run Playwright through the default Compose project. Use a dedicated,
  isolated e2e Compose project and ensure it does not publish the API port on
  the host. If that isolation is not already configured, ask before running
  e2e tests.
