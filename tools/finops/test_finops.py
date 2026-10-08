"""Pruebas de las herramientas del workflow. Ejecutar: python -m unittest discover tools/finops"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from affected_envs import affected  # noqa: E402
from compute_estimate import PRICING_FILE  # noqa: E402
from env_summary import capacity_summary  # noqa: E402
from render_comment import fmt_int, fmt_usd, render  # noqa: E402

PRICING = json.loads(PRICING_FILE.read_text(encoding="utf-8"))


def plan(min_before: int | None, min_after: int) -> dict:
    template = {
        "type": "aws_launch_template",
        "address": "module.checkout.aws_launch_template.app",
        "values": {"instance_type": "t4g.micro", "block_device_mappings": [{"ebs": [{"volume_size": 8}]}]},
    }
    asg = {
        "type": "aws_autoscaling_group",
        "address": "module.checkout.aws_autoscaling_group.app",
        "values": {"min_size": min_after, "max_size": 8},
    }
    before = None if min_before is None else {"min_size": min_before}
    return {
        "planned_values": {"root_module": {"child_modules": [{"resources": [template, asg]}]}},
        "resource_changes": [{"type": "aws_autoscaling_group", "change": {"before": before}}],
    }


class AffectedEnvsTest(unittest.TestCase):
    def test_profile_change_reaches_every_env(self):
        self.assertEqual(list(affected(["profiles/checkout-capacity.json"])), ["prod", "staging", "dev"])

    def test_env_change_reaches_only_that_env(self):
        self.assertEqual(list(affected(["envs/staging/main.tf", "README.md"])), ["staging"])

    def test_unrelated_change_reaches_nothing(self):
        self.assertEqual(affected(["README.md", "docs/progress.svg"]), {})


class CapacitySummaryTest(unittest.TestCase):
    def test_raise_from_two_to_six(self):
        cap = capacity_summary(plan(2, 6), PRICING)
        self.assertEqual((cap["hours_before"], cap["hours_after"], cap["delta_hours"]), (1460, 4380, 2920))
        # 4 × (730 h × 0,0084 + 8 GB × 0,08) = 27,09
        self.assertAlmostEqual(cap["delta_compute_usd"], 27.09, places=2)

    def test_new_asg_has_no_before(self):
        cap = capacity_summary(plan(None, 2), PRICING)
        self.assertIsNone(cap["hours_before"])
        self.assertEqual(cap["delta_hours"], 1460)


class RenderTest(unittest.TestCase):
    def test_spanish_number_format(self):
        self.assertEqual(fmt_int(13140), "13.140")
        self.assertEqual(fmt_usd(1234.5), "USD 1.234,50")
        self.assertEqual(fmt_usd(-27.09, signed=True), "−USD 27,09")

    def test_render_marks_nonprod_and_totals(self):
        with tempfile.TemporaryDirectory() as tmp:
            caps = {env: capacity_summary(plan(2, 6), PRICING) for env in ("prod", "staging", "dev")}
            summaries = Path(tmp, "s")
            summaries.mkdir()
            for env, cap in caps.items():
                Path(summaries, f"{env}.json").write_text(
                    json.dumps({"env": env, "capacity": cap, "infracost": None}), encoding="utf-8"
                )
            input_path = Path(tmp, "input.json")
            input_path.write_text(json.dumps({"envs": caps}), encoding="utf-8")
            text = render(str(input_path), str(summaries), str(Path(tmp, "missing.json")), "abcdef123")
        self.assertIn("cambia en 3 de 3 entornos", text)
        self.assertIn("| staging ⚠️ |", text)
        self.assertIn("4.380 → 13.140", text)
        self.assertIn("No se pudieron evaluar", text)


if __name__ == "__main__":
    unittest.main()
