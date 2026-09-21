"""Check host manifests and marketplace paths without requiring either host."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PackagingTests(unittest.TestCase):
    def test_host_manifests_and_marketplaces_agree(self):
        manifests = []
        for marketplace, manifest, structured in (
            (".agents/plugins/marketplace.json", ".codex-plugin/plugin.json", True),
            (".claude-plugin/marketplace.json", ".claude-plugin/plugin.json", False),
        ):
            data = json.loads((ROOT / marketplace).read_text())
            entry = next(p for p in data["plugins"] if p["name"] == "rubric-evaluator")
            source = entry["source"]["path"] if structured else entry["source"]
            plugin = ROOT / source
            self.assertTrue(plugin.is_dir(), source)
            metadata = json.loads((plugin / manifest).read_text())
            self.assertEqual(metadata["name"], entry["name"])
            if "version" in entry:
                self.assertEqual(entry["version"], metadata["version"])
            skills = plugin / metadata.get("skills", "skills")
            self.assertTrue((skills / "rubric-evaluator/SKILL.md").is_file())
            for key in ("composerIcon", "logo"):
                asset = metadata.get("interface", {}).get(key)
                if asset:
                    self.assertTrue((plugin / asset).is_file(), asset)
            manifests.append(metadata)
        for key in ("name", "version", "license", "repository"):
            self.assertEqual(manifests[0][key], manifests[1][key])


if __name__ == "__main__":
    unittest.main()
