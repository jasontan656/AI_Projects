from __future__ import annotations

import unittest

from interface_entry.config.manifest_loader import load_top_entry_manifest


class InterfaceEntryManifestTestCase(unittest.TestCase):
    def test_default_manifest_contains_interface_entry_paths(self) -> None:
        manifest = load_top_entry_manifest()
        telegram_paths = manifest.get("telegrambot", [])
        self.assertTrue(any("interface_entry/telegram" in path for path in telegram_paths))


if __name__ == "__main__":
    unittest.main()
