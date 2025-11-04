## ADDED Requirements

### Requirement: Conversation Service Primitives
Business Service MUST expose granular helpers (`IntentClassifier`, `AgentDelegator`, `AdapterBuilder`) returning typed dictionaries so Business Logic consumers can compose conversation flows without duplicating transport logic.

#### Scenario: Intent classifier returns normalized result
- **GIVEN** a user message string
- **WHEN** `IntentClassifier.classify` is called
- **THEN** it returns a mapping containing the resolved intent key, confidence flags, and any system tags needed by downstream flows.

### Requirement: Knowledge Snapshot Delegation
Business Service MUST retain responsibility for IO-bound knowledge snapshot operations (YAML loading, Redis sync) while offering a pure interface (`KnowledgeSnapshotService.load/refresh`) consumable by Business Logic orchestrators.

#### Scenario: Snapshot load reuses Business Service
- **GIVEN** Business Logic requests a snapshot via the new orchestrator
- **WHEN** Business Service `KnowledgeSnapshotService.load()` executes
- **THEN** it returns an immutable snapshot payload plus refresh callable without requiring direct filesystem or Redis access in the logic layer.

### Requirement: Interface Independence
Interface layers MUST depend on Business Logic entrypoints rather than directly using Business Service implementations, ensuring downward-only dependencies (Interface → Business Logic → Business Service).

#### Scenario: Telegram handler consumes logic layer
- **GIVEN** the Telegram handler needs to process a message
- **WHEN** the change is complete
- **THEN** the handler invokes `TelegramConversationFlow.process(...)` and uses the resulting contract, without importing `business_service.conversation` modules directly.
