## 1. Pipeline Node API Enhancements
- [x] Update FastAPI router to return paginated envelope and support PUT/DELETE handlers with structured errors.
- [x] Extend repository/service to handle updates, deletion, and timestamp/version management; add tests covering success/conflict/not found paths.

## 2. Prompt API Implementation
- [x] Define Mongo models/repository/service for prompts, including pagination and auditing metadata.
- [x] Expose `/api/prompts` GET/PUT/DELETE routes; cover happy-path and error scenarios with FastAPI tests.

## 3. Frontend Integration
- [x] Replace stubbed pipeline node service with real API calls (list/update/delete) and update Pinia store/components to handle new responses and errors.
- [x] Implement prompt service/store/UI updates for list/edit/delete operations; ensure structured error messaging.

## 4. Documentation & Validation
- [x] Document REST contracts (nodes & prompts) and update README/instruction references.
- [x] Run backend/frontend test suites and `openspec validate add-pipeline-and-prompt-management --strict`.
