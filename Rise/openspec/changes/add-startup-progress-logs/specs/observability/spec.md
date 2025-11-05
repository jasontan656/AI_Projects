## MODIFIED Requirements
### Requirement: Startup Console Visibility
Startup console logs MUST surface meaningful progress markers so operators can distinguish expected delays from hangs.

#### Scenario: Aiogram bootstrap progress visibility
- **GIVEN** the service is launching
- **WHEN** the aiogram bootstrap begins
- **THEN** the console emits a progress log indicating the bootstrap start
- **AND** it emits another log when the bootstrap completes.

#### Scenario: Knowledge snapshot progress visibility
- **GIVEN** the knowledge snapshot orchestrator is loading data
- **WHEN** loading begins
- **THEN** a progress log is emitted immediately before the load
- **AND** completion is logged after the load with relevant metadata.

#### Scenario: Clean startup visibility
- **GIVEN** `python app.py --clean` is invoked
- **WHEN** each cleanup segment (logs, runtime state, Redis, Mongo) runs
- **THEN** the console shows the segment start and completion in order.
