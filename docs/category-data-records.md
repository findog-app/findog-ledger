# Category Data Records

Category data is stored as a timestamped history of observations. Each record
is validated against the category's active custom-field schema and permanently
keeps the schema version that was active when it was created.

## Define a category data schema

A schema describes the shape of the `data` object in every observation for a
category. Create it in the **Custom fields** page for a category, or send it to
`POST /api/v1/ledgers/{ledger_id}/categories/{category_id}/data-schema` as the
`schema` property of the request body. Every successful update creates a new
schema version; existing records keep the version used when they were created.

The API accepts a valid JSON Schema whose root has `"type": "object"`. This
is the smallest useful schema:

```json
{
  "schema": {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": false
  }
}
```

`properties` maps each field name to its definition. `required` lists the
property names that must be supplied. Set `additionalProperties` to `false` to
reject fields that are not explicitly defined; this is recommended for stable
integration payloads.

For example, a category that records a billing period, an amount, and an
optional tariff can use:

```json
{
  "schema": {
    "type": "object",
    "properties": {
      "billing_date": {
        "type": "string",
        "format": "date",
        "title": "Billing date"
      },
      "amount": {
        "type": "number",
        "minimum": 0,
        "title": "Amount"
      },
      "tariff": {
        "type": "string",
        "enum": ["standard", "night"],
        "description": "Provider tariff at the time of the reading"
      }
    },
    "required": ["billing_date", "amount"],
    "additionalProperties": false
  }
}
```

### Fields supported by the Custom fields builder

The backend validates standard JSON Schema, but the in-app builder intentionally
edits a smaller, predictable subset. To keep a schema editable in the builder,
use only these root keywords: `type`, `properties`, `required`, and
`additionalProperties`. The root must be an object, `properties` must be an
object, `required` must be an array of defined field names, and
`additionalProperties` must be `false`.

For each property, the builder supports the following definitions:

| Field type | JSON Schema | Optional keywords |
| --- | --- | --- |
| Text | `"type": "string"` | `title`, `description`, `minLength`, `maxLength`, `enum` |
| Number | `"type": "number"` | `title`, `description`, `minimum`, `maximum` |
| Integer | `"type": "integer"` | `title`, `description`, `minimum`, `maximum` |
| Yes / no | `"type": "boolean"` | `title`, `description` |
| Date | `"type": "string", "format": "date"` | `title`, `description` |

Use a field key that is meaningful and stable, such as `meter_reading_kwh` or
`billing_date`. A property that uses another JSON Schema keyword, type, or
format can still be valid through the API, but the Custom fields page presents
it as read-only so that it cannot accidentally remove configuration it does not
understand.

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
