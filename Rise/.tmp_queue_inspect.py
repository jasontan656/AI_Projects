import os, json
import redis

redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
r = redis.Redis.from_url(redis_url)
namespace = os.environ.get('TASK_QUEUE_NAMESPACE', 'queue')
stream_key = f"{namespace}:tasks"
task_prefix = f"{namespace}:task"
print(f"Inspecting stream={stream_key} ...")

entries = r.xrange(stream_key, count=20)
print(f"Found {len(entries)} stream items (latest 20 shown)")
for entry_id, payload in entries:
    task_json = payload.get(b'task')
    if not task_json:
        continue
    data = json.loads(task_json)
    meta = data.get('payload', {}).get('metadata', {})
    status = data.get('status')
    print(f"- task={data.get('taskId')} status={status} workflow={data.get('payload', {}).get('workflowId')} channel={data.get('payload', {}).get('telemetry', {}).get('channel')} chat_id={meta.get('chat_id')}" )

keys = r.keys(f"{task_prefix}:*")
print(f"Persisted task docs: {len(keys)}")
preview = []
for key in keys[:5]:
    data = json.loads(r.get(key))
    preview.append({
        'taskId': data.get('taskId'),
        'status': data.get('status'),
        'workflowId': data.get('payload', {}).get('workflowId'),
        'channel': data.get('payload', {}).get('telemetry', {}).get('channel'),
        'createdAt': data.get('createdAt'),
    })
print(json.dumps(preview, indent=2, ensure_ascii=False))

pending = r.xpending(stream_key, os.environ.get('TASK_QUEUE_GROUP', 'persist-workers'))
print('Pending summary:', pending)
