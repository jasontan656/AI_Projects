## ADDED Requirements

### Requirement: Knowledge Snapshot Facade
Business Service MUST expose a `KnowledgeSnapshotFacade` that coordinates asset loading, checksum calculation, and publish decisions, returning a typed `SnapshotBundle` with snapshot data, metadata, and refresh hooks.

#### Scenario: Snapshot bundle exposes refresh callable and telemetry
- **GIVEN** the facade is configured with repository and publisher collaborators
- **WHEN** `facade.load()` runs
- **THEN** it returns a `SnapshotBundle` dataclass containing the snapshot payload, checksum, missing agencies, telemetry stages, and a callable `refresh(reason)` that reuses the same collaborators
- **AND** the bundle surfaces Redis status and errors in structured fields for Business Logic.

### Requirement: Asset Repository Encapsulates Business Asset Layout
Business Service MUST provide a repository abstraction that reads Business Asset files (`KnowledgeBase/` indexes, agency folders) and enforces schema guards before the snapshot facade accesses the payloads.

#### Scenario: Repository reports missing agency with asset-aware path
- **GIVEN** an agency id without a corresponding `<agency>/<agency>_index.yaml`
- **WHEN** the repository loads assets
- **THEN** it returns a structured `MissingAsset` event containing the agency id and expected path relative to `KnowledgeBase`
- **AND** the facade records this in snapshot telemetry and `missing_agencies` without Business Logic inspecting filesystem paths.

### Requirement: Snapshot Publisher Metadata Standardization
Business Service MUST encapsulate Redis (or alternative cache) publication behind a `SnapshotPublisher` that records publish timestamps, reasons, and checksum metadata, ensuring audit-friendly outputs aligned with Business Asset governance.

#### Scenario: Publisher enriches metadata on successful publish
- **GIVEN** the publisher pushes a snapshot to Redis
- **WHEN** the operation succeeds
- **THEN** it returns metadata containing keys `backend`, `status`, `cached_at`, `checksum`, and `missing_agencies`
- **AND** the facade merges this metadata into the `SnapshotBundle` while handling failure states (e.g., Redis unavailable) without raising unhandled exceptions.
