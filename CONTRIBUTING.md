# Contributing to Findog Ledger

Findog Ledger is a private, multi-user payment-obligation application. Before
starting substantial work, open an issue or align the scope with a maintainer.

## Development setup

- Use `uv` for backend dependencies and commands.
- Use Bun for frontend dependencies and commands.
- Copy and configure the required environment values before running the stack.
  See [development.md](./development.md) for local-development details.

```bash
uv sync
bun install --frozen-lockfile
```

## Before opening a pull request

- Keep a change focused on one concern.
- Add or update tests for changed behaviour.
- Regenerate the frontend OpenAPI client after backend API changes:

  ```bash
  bash ./scripts/generate-client.sh
  ```

- Run the relevant checks:

  ```bash
  uv run pre-commit run --all-files
  cd backend && uv run pytest
  bun run --filter frontend build
  ```

## Commits and pull requests

Use Conventional Commit messages, for example:

```text
feat: add ledger member roles
fix: validate recurring category due day
docs: clarify local development setup
```

Pull requests are squash-merged. The pull request title becomes the final
commit on `main`, so it must also follow the Conventional Commits format. This
allows automated release version calculation to treat one merged pull request
as one release-relevant commit.

Commitizen updates the canonical versions in `pyproject.toml` and
`backend/pyproject.toml`. After a version bump, run `uv lock` to regenerate the
lockfile instead of editing its version metadata directly. To determine the
next version without changing files or prompting for input, run:

```bash
bash ./scripts/cz.sh bump --dry-run --yes --get-next
```

Describe the purpose of the pull request, the validation performed, and any
configuration or migration steps required for reviewers. Do not include
credentials, tokens, or production data.

## Reporting issues

Use the GitHub bug-report and feature-request forms for product and development
work. Do not report security vulnerabilities in a public issue; follow
[SECURITY.md](./SECURITY.md) instead.
