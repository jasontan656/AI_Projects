import pytest

from foundational_service.contracts.workflow_exec import WorkflowExecutionPayload
from foundational_service.persist.task_envelope import TaskEnvelope
from foundational_service.persist.worker import WorkflowTaskProcessor


class StubExecutor:
    def __init__(self) -> None:
        self.payloads: list[WorkflowExecutionPayload] = []

    async def execute(self, payload: WorkflowExecutionPayload):
        self.payloads.append(payload)
        return {
            "final_text": "workflow:ok",
            "stage_results": [
                {
                    "stage_id": "stage-1",
                    "name": "Stage 1",
                    "prompt_used": "prompt::1",
                    "output_text": "output::1",
                    "raw_response": {"usage": {"tokens": 10}},
                }
            ],
            "telemetry": {"stages": []},
        }


@pytest.mark.asyncio
async def test_processor_passes_normalized_payload_to_executor():
    envelope = TaskEnvelope(
        task_id="task-1",
        type="workflow",
        payload={
            "workflowId": "wf-1",
            "userText": "hello",
            "historyChunks": ["prev"],
            "policy": {"mode": "safe"},
            "coreEnvelope": {
                "metadata": {"chat_id": "chat-1"},
                "inbound": {"chat_id": "chat-1"},
            },
        },
        context={"requestId": "req-1"},
    )
    executor = StubExecutor()
    processor = WorkflowTaskProcessor(workflow_executor=executor)

    result = await processor.process(envelope)

    assert executor.payloads[0]["workflow_id"] == "wf-1"
    assert executor.payloads[0]["request_id"] == "req-1"
    assert executor.payloads[0]["history_chunks"] == ("prev",)
    assert result["finalText"] == "workflow:ok"
    assert result["stageResults"][0]["usage"] == {"tokens": 10}
