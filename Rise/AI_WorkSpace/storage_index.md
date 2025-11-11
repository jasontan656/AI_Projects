# 数据持久化索引

_生成时间：2025-11-11T16:04:45+00:00_

## RABBIT

- `channel_binding.updated` · src/business_service/channel/events.py · Business Service Layer · ataclasses import dataclass, field
- `channel_binding.health` · src/business_service/channel/events.py · Business Service Layer · mport datetime, timezone

## REDIS

- `events` · src/business_service/channel/events.py · Business Service Layer · 包含 redis 关键字
- `health_store` · src/business_service/channel/health_store.py · Business Service Layer · 包含 redis 关键字
- `rate_limit` · src/business_service/channel/rate_limit.py · Business Service Layer · 包含 redis 关键字
- `models` · src/business_service/knowledge/models.py · Business Service Layer · 包含 redis 关键字
- `snapshot_service` · src/business_service/knowledge/snapshot_service.py · Business Service Layer · 包含 redis 关键字
- `redis_queue` · src/foundational_service/persist/redis_queue.py · Foundational Service Layer · 包含 redis 关键字
- `retry_scheduler` · src/foundational_service/persist/retry_scheduler.py · Foundational Service Layer · 包含 redis 关键字
- `task_envelope` · src/foundational_service/persist/task_envelope.py · Foundational Service Layer · 包含 redis 关键字
- `worker` · src/foundational_service/persist/worker.py · Foundational Service Layer · 包含 redis 关键字
