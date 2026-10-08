"""Horas-instancia mínimas y costo de lista del ASG a partir de un plan de Terraform.

Infracost no costea el ASG del módulo (no fija desired_capacity). Este script
toma `min_size`, el tipo de instancia y el disco del launch template del plan
JSON (`terraform show -json`) y los multiplica por los precios de
`pricing/aws-us-east-2.json`. La métrica principal son las horas mínimas
comprometidas; los dólares son precio de lista, no factura.

Uso:
    python tools/finops/compute_estimate.py prod=plan-prod.json staging=plan-staging.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PRICING_FILE = Path(__file__).resolve().parents[2] / "pricing" / "aws-us-east-2.json"


def _planned_resources(module: dict) -> list[dict]:
    resources = list(module.get("resources", []))
    for child in module.get("child_modules", []):
        resources.extend(_planned_resources(child))
    return resources


def asg_capacity(plan: dict) -> list[dict]:
    """Devuelve min/max, tipo de instancia y GB de disco de cada ASG del plan."""
    resources = _planned_resources(plan.get("planned_values", {}).get("root_module", {}))
    templates = [r["values"] for r in resources if r["type"] == "aws_launch_template"]
    if len(templates) != 1:
        raise ValueError(f"se esperaba un launch template, hay {len(templates)}")
    template = templates[0]
    volume_gb = sum(
        ebs.get("volume_size") or 0
        for bdm in template.get("block_device_mappings", [])
        for ebs in bdm.get("ebs", [])
    )
    return [
        {
            "address": r["address"],
            "min_size": r["values"]["min_size"],
            "max_size": r["values"]["max_size"],
            "instance_type": template["instance_type"],
            "volume_gb": volume_gb,
        }
        for r in resources
        if r["type"] == "aws_autoscaling_group"
    ]


def estimate(plan: dict, pricing: dict) -> dict:
    hours = pricing["hours_per_month"]
    asgs = []
    for asg in asg_capacity(plan):
        instance_hours = asg["min_size"] * hours
        ec2 = instance_hours * pricing["ec2_hourly"][asg["instance_type"]]
        ebs = asg["min_size"] * asg["volume_gb"] * pricing["ebs_gb_month"]["gp3"]
        asgs.append({**asg, "min_instance_hours": instance_hours, "monthly_usd": round(ec2 + ebs, 2)})
    return {
        "min_instance_hours": sum(a["min_instance_hours"] for a in asgs),
        "monthly_usd": round(sum(a["monthly_usd"] for a in asgs), 2),
        "asgs": asgs,
    }


def main(argv: list[str]) -> int:
    if not argv or any("=" not in arg for arg in argv):
        print(__doc__, file=sys.stderr)
        return 2
    pricing = json.loads(PRICING_FILE.read_text(encoding="utf-8"))
    result = {
        "pricing": {k: pricing[k] for k in ("source", "retrieved", "currency", "hours_per_month")},
        "environments": {},
    }
    for arg in argv:
        env, path = arg.split("=", 1)
        plan = json.loads(Path(path).read_text(encoding="utf-8"))
        result["environments"][env] = estimate(plan, pricing)
    envs = result["environments"].values()
    result["total"] = {
        "min_instance_hours": sum(e["min_instance_hours"] for e in envs),
        "monthly_usd": round(sum(e["monthly_usd"] for e in envs), 2),
    }
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
