from __future__ import annotations

import time
import unittest

from foundational_service.contracts.envelope import CoreEnvelope
from foundational_service.contracts.telegram import (
    ChannelNotSupportedError,
    build_core_schema,
)


class FoundationalContractsTestCase(unittest.TestCase):
    def test_core_envelope_validate_payload_trims_context_quotes(self) -> None:
        quotes = [
            {"speaker": "user", "excerpt": f"quote-{idx}", "role": "user"}
            for idx in range(7)
        ]
        payload = {
            "chat_id": "123",
            "convo_id": "123",
            "channel": "telegram",
            "language": "en",
            "user_message": "hello world",
            "context_quotes": quotes,
            "attachments": [],
            "system_tags": [],
        }

        model = CoreEnvelope.validate_payload(payload)

        self.assertEqual(len(model.payload.context_quotes), 5)
        self.assertEqual(model.trimmed_context_quote_count, 2)
        self.assertEqual(model.payload.context_quotes[0].excerpt, "quote-2")

    def test_build_core_schema_generates_envelope_with_metadata(self) -> None:
        now_ts = int(time.time())
        update = {
            "message": {
                "message_id": 42,
                "date": now_ts,
                "chat": {"id": 999, "type": "private"},
                "text": "Rise test payload",
            }
        }

        result = build_core_schema(update, channel="telegram")

        envelope = result["core_envelope"]
        telemetry = result["telemetry"]

        self.assertEqual(envelope["metadata"]["chat_id"], "999")
        self.assertEqual(envelope["payload"]["user_message"], "Rise test payload")
        self.assertIsNotNone(telemetry.get("validation_ms"))

    def test_build_core_schema_rejects_unknown_channel(self) -> None:
        with self.assertRaises(ChannelNotSupportedError):
            build_core_schema({}, channel="web")


if __name__ == "__main__":
    unittest.main()
