# Obligations Domain Architecture

1. `Ledger` is the top-level container because obligations, categories, and templates must belong to a shared business space instead of being copied per user. Sharing access is granted to the same ledger data.
2. Categories are database-driven because they are part of user-managed configuration and cannot be safely modeled as hard-coded enums.
3. Obligation lifecycle is separate from field completeness because a record can be in `collecting_data` or `ready` independently from whether amount or dates are still unknown, estimated, confirmed, or overridden.
4. Manual override is represented explicitly with per-field source and state columns. A manually overridden amount or date can be marked with source `manual` and state `overridden` without needing history tables yet.
5. Ledger sharing uses a dedicated membership table with roles. `ledger.owner_user_id` is the canonical owner, while memberships provide uniform access control for owner, editor, and viewer roles.
6. Category archiving is soft-archive only so historical obligations keep stable references to archived groups and categories while normal assignment flows can filter to active records.
7. Obligation creation for current and next period is handled by a deterministic service that only targets `precreate` templates and relies on a unique database constraint to keep repeated runs idempotent.
