# Category Data Records

Category data is stored as a timestamped history of observations. Each record
is validated against the category's active custom-field schema and permanently
keeps the schema version that was active when it was created.

## Create an observation through the integration API

Use a ledger-scoped API key with the `ledger:write` scope. Replace the example
API key, category code, timestamp, fields, source, and external ID with your
own values.

```bash
curl --silent --show-error --fail-with-body \
  --request POST \
  --header "Authorization: Bearer fdg_live_your_api_key" \
  --header "Content-Type: application/json" \
  --data '{
    "observed_at": "2026-08-24T12:00:00Z",
    "data": {
      "DK": "2026-08-24",
      "apartment_fee": 199.99
    },
    "source": "meter-importer",
    "external_id": "flat-2026-08-24"
  }' \
  "http://localhost:8000/api/v1/integration/categories/FLAT/data-records"
```

`observed_at` is the time at which the value was observed, rather than the time
at which the request is sent. The `data` object must satisfy the active schema
for the category.

When both `source` and `external_id` are supplied, they form an idempotency
identity for that category. Retrying the same request returns the existing
record instead of creating a duplicate.

## Read observations

```bash
curl --silent --show-error --fail-with-body \
  --header "Authorization: Bearer fdg_live_your_api_key" \
  "http://localhost:8000/api/v1/integration/categories/FLAT/data-records?limit=100"
```

The list is ordered from newest to oldest. It supports `from`, `to`, `limit`,
and `offset` query parameters. To retrieve only the newest record, use:

```bash
curl --silent --show-error --fail-with-body \
  --header "Authorization: Bearer fdg_live_your_api_key" \
  "http://localhost:8000/api/v1/integration/categories/FLAT/data-records/latest"
```
