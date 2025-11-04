# Logging Runtime

## ADDED Requirements

### Requirement: Provide reusable Rich logging bootstrap
The platform SHALL expose a shared logging helper that configures Rich console output, alert panels, and file handlers without requiring service modules to embed the implementation.

#### Scenario: Service configures logging
Given a service imports `shared_utility.logging.rich_config.configure_logging`
When the service calls `configure_logging()` during startup
Then the helper MUST install the same Rich console handlers, alert panels, rotating file handlers, and UVicorn alias filter that currently exist in `app.py`
And the helper MUST create log files under the directory returned by `shared_utility.config.paths.get_log_root()`.

#### Scenario: Service module remains slim
Given `app.py` previously contained custom handler classes
When the refactor is complete
Then `app.py` MUST no longer define logging handler/filter classes inline
And it MUST only rely on the shared helper to configure logging.
