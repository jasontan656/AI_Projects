# Capability: Interface Entry Telegram

## ADDED Requirements

### Requirement: Telegram runtime delegates via interface_entry
The Interface Layer MUST expose `interface_entry.telegram.runtime` helpers that bootstrap aiogram dispatchers, wire webhook routes, and surface telemetry without duplicating foundational logic.

#### Scenario: Bootstrap telegram runtime
GIVEN a test configuration with environment variables set
WHEN calling `interface_entry.telegram.runtime.bootstrap_aiogram_service(...)`
THEN the function returns a runtime state object with dispatcher/router references
AND no import from removed `telegram_api.*` modules occurs.

### Requirement: Webhook routes reside under interface_entry
FastAPI webhook endpoints MUST be defined under `interface_entry.telegram.routes` and registered through the new app factory.

#### Scenario: Include webhook router
GIVEN a FastAPI app built via `interface_entry.bootstrap.app.create_app()`
WHEN inspecting `app.routes`
THEN the `/telegram/webhook` and `/telegram/setup_webhook` endpoints originate from `interface_entry.telegram.routes`.

### Requirement: Telegram handlers integrate foundational contracts
Telegram message handlers MUST translate updates using `foundational_service.contracts` helpers while residing in `interface_entry.telegram.handlers`.

#### Scenario: Process inbound message
GIVEN a unit test invoking `interface_entry.telegram.handlers.process_update`
WHEN a Telegram message payload is provided
THEN the handler calls `foundational_service.contracts.telegram.behavior_telegram_inbound`
AND returns the normalized result without accessing deprecated adapters.

