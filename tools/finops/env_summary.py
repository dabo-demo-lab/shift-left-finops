"""Resumen de un entorno para el comentario del PR, sin datos de la cuenta.

Combina el plan (capacidad mínima antes y después) con la salida de
`infracost inspect --json` (infraestructura fija y políticas que fallan). El
resumen se publica como artefacto en un repo público, por eso no incluye
ARNs, IDs de recursos ni el ID de la cuenta.

Uso:
    python tools/finops/env_summary.py <env> <plan.json> [<infracost.json>]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compute_estimate import PRICING_FILE, asg_capacity  # noqa: E402


def asg_min_before(plan: dict) -> int | None:
    """min_size desplegado según el estado; None si el ASG aún no existe."""
    for change in plan.get("resource_changes", []):
        if change["type"] == "aws_autoscaling_group":
            before = change["change"].get("before")
            return before["min_size"] if before else None
    return None


def capacity_summary(plan: dict, pricing: dict) -> dict:
    asgs = asg_capacity(plan)
    if len(asgs) != 1:
        raise ValueError(f"se esperaba un ASG, hay {len(asgs)}")
    asg = asgs[0]
    hours = pricing["hours_per_month"]
    per_instance_month = (
        hours * pricing["ec2_hourly"][asg["instance_type"]]
        + asg["volume_gb"] * pricing["ebs_gb_month"]["gp3"]
    )
    before = asg_min_before(plan)
    after = asg["min_size"]
    return {
        "instance_type": asg["instance_type"],
        "min_before": before,
        "min_after": after,
        "max_after": asg["max_size"],
        "hours_before": None if before is None else before * hours,
        "hours_after": after * hours,
        "delta_hours": (after - (before or 0)) * hours,
        "compute_usd_after": round(after * per_instance_month, 2),
        "delta_compute_usd": round((after - (before or 0)) * per_instance_month, 2),
    }


def infracost_summary(inspect: dict | None) -> dict | None:
    if not inspect:
        return None
    failing = sorted({p["name"] for p in inspect.get("failing_policy_list", [])})
    return {
        "monthly_usd": round(float(inspect.get("monthly_cost") or 0), 2),
        "costed_resources": inspect.get("costed_resources"),
        "failing_policies": failing,
    }


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    env, plan_path = argv[0], argv[1]
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    pricing = json.loads(PRICING_FILE.read_text(encoding="utf-8"))
    inspect = None
    if len(argv) == 3 and Path(argv[2]).is_file():
        try:
            inspect = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            inspect = None
    summary = {
        "env": env,
        "capacity": capacity_summary(plan, pricing),
        "infracost": infracost_summary(inspect),
    }
    json.dump(summary, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
