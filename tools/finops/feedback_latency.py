"""Latencia del feedback FinOps: cuánto espera el developer desde el push hasta el comentario.

Lee las ejecuciones del workflow `finops-pr` con `gh run list` y calcula
p50 y p95 (rango más cercano) de su duración: desde que el push dispara la
ejecución hasta que termina el job que publica el comentario. Es una métrica
de experiencia del developer, no de la aplicación.

Con pocas ejecuciones el p95 es poco informativo; el script indica n.

Uso:
    python tools/finops/feedback_latency.py [--repo org/repo] [--limit 100]
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime


def percentile(values: list[float], pct: float) -> float:
    """Percentil por rango más cercano: sin interpolar entre observaciones."""
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def durations_seconds(runs: list[dict]) -> list[float]:
    out = []
    for run in runs:
        if run.get("event") != "pull_request" or run.get("conclusion") != "success":
            continue
        start = datetime.fromisoformat(run["createdAt"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(run["updatedAt"].replace("Z", "+00:00"))
        out.append((end - start).total_seconds())
    return out


def fmt(seconds: float) -> str:
    minutes, secs = divmod(round(seconds), 60)
    return f"{minutes} min {secs:02d} s"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default="dabo-demo-lab/shift-left-finops")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    raw = subprocess.run(
        [
            "gh", "run", "list", "--repo", args.repo, "--workflow", "finops-pr.yml",
            "--limit", str(args.limit), "--json", "event,conclusion,createdAt,updatedAt",
        ],
        check=True, capture_output=True, text=True,
    ).stdout
    values = durations_seconds(json.loads(raw))
    if not values:
        print("Sin ejecuciones exitosas de pull_request.")
        return 1
    print(f"n = {len(values)} ejecuciones exitosas")
    print(f"p50 = {fmt(percentile(values, 50))}")
    print(f"p95 = {fmt(percentile(values, 95))}")
    print(f"máx = {fmt(max(values))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
