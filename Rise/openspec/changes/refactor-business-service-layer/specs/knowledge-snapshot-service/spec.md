## ADDED Requirements

### Requirement: Knowledge Snapshot Load
Provide a `KnowledgeSnapshotService.load()` method that reads the organisation index and agency indexes from `KnowledgeBase/`, calculates the checksum, and (optionally) synchronises the snapshot to Redis. The returned `SnapshotResult` MUST include:
- `snapshot`: dictionary with `org_metadata`, `routing_table`, `agencies`, `created_at`, `checksum`, and `missing_agencies`;
- `status`: `"ready"` when all agencies exist and Redis sync succeeds, otherwise `"memory_only"`;
- `telemetry`: stage-by-stage records noting initial load and Redis sync outcomes;
- `health`: summary containing Redis status/error and missing agencies list;
- `metadata.redis`: backend/primary selection, availability flag, and sync keys when present.

#### Scenario: Successful Redis-backed snapshot
- **GIVEN** the Knowledge Base root and org index file exist and Redis is reachable
- **WHEN** `KnowledgeSnapshotService.load()` is called with Redis enabled
- **THEN** it returns `status="ready"`, `health.redis_status="ready"`, and `metadata.redis.available=True`
- **AND** the `snapshot.checksum` is populated with the digest of org + agency indexes
- **AND** the telemetry records both the `initial_load` and `redis_sync` stages with `status="ready"`.

### Requirement: Snapshot Refresh API
`KnowledgeSnapshotService.refresh(reason)` MUST reload indexes, rerun Redis synchronisation, and return a new `SnapshotResult` reflecting the latest status while leaving the original load result unchanged.

#### Scenario: Refresh after missing agency is added
- **GIVEN** an initial load that returned `missing_agencies=["dole"]`
- **AND** the agency index for `dole` is added to the repository
- **WHEN** `refresh(reason="manual")` is invoked
- **THEN** the refreshed result reports `missing_agencies=[]` and `status="ready"`
- **AND** the telemetry contains a `redis_sync` stage whose keys match the newly published snapshot.

### Requirement: Asset Guard Reporting
The service MUST expose an `asset_guard()` helper that verifies required directories/files (config, KnowledgeBase, foundational contracts) and surfaces prompt events compatible with existing alert prompts.

#### Scenario: Missing knowledge base directory
- **GIVEN** the repository root lacks the `KnowledgeBase/` folder
- **WHEN** `asset_guard()` executes
- **THEN** it returns a report with `status="violation"`, lists the missing directory, and produces a prompt event referencing `asset_guard_violation`.
