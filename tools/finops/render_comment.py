"""Entrada de las reglas y comentario del PR a partir de los resúmenes por entorno.

Subcomandos:
    input  <summaries-dir> <base-sha> <head-sha>
        Escribe en stdout el JSON que evalúan las reglas Rego: archivos
        cambiados, qué claves del perfil cambiaron y la capacidad por entorno.
        EXPECTED_ENVS (JSON) lista los entornos que debían planificarse; los que
        no tienen resumen se marcan como plan fallido.
    render <input.json> <summaries-dir> <conftest.json> <head-sha>
        Escribe en stdout el comentario en Markdown.

Formato numérico en español (4.380 · USD 27,09), como en las láminas.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

MARKER = "<!-- finops-pr-comment -->"
PROFILE = "profiles/checkout-capacity.json"
ENV_ORDER = ("prod", "staging", "dev")


def fmt_int(value: int | float | None) -> str:
    if value is None:
        return "—"
    return f"{round(value):,}".replace(",", ".")


def fmt_signed_int(value: int | float) -> str:
    sign = "+" if value > 0 else ("−" if value < 0 else "±")
    return f"{sign}{fmt_int(abs(value))}"


def fmt_usd(value: float | None, signed: bool = False) -> str:
    if value is None:
        return "—"
    text = f"{abs(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    if signed:
        sign = "+" if value > 0 else ("−" if value < 0 else "±")
        return f"{sign}USD {text}"
    return f"USD {text}"


def load_summaries(directory: str) -> dict[str, dict]:
    summaries = {}
    for path in Path(directory).rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        summaries[data["env"]] = data
    return {env: summaries[env] for env in ENV_ORDER if env in summaries}


def git_show_json(ref: str, path: str) -> dict | None:
    result = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True)
    return json.loads(result.stdout) if result.returncode == 0 else None


def profile_change(base: str, head: str) -> dict:
    before = git_show_json(base, PROFILE) or {}
    after = git_show_json(head, PROFILE) or {}
    shared_before, shared_after = before.get("shared", {}), after.get("shared", {})
    over_before, over_after = before.get("overrides", {}), after.get("overrides", {})
    return {
        "shared_changed_keys": sorted(
            k for k in set(shared_before) | set(shared_after) if shared_before.get(k) != shared_after.get(k)
        ),
        "override_envs_changed": sorted(
            e for e in set(over_before) | set(over_after) if over_before.get(e) != over_after.get(e)
        ),
    }


def build_input(summaries_dir: str, base: str, head: str) -> dict:
    files = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"], check=True, capture_output=True, text=True
    ).stdout.split()
    envs = {env: s["capacity"] for env, s in load_summaries(summaries_dir).items()}
    expected = json.loads(os.environ.get("EXPECTED_ENVS") or "[]")
    return {
        "changed_files": files,
        "profile": profile_change(base, head),
        "envs": envs,
        "failed_envs": [env for env in ENV_ORDER if env in expected and env not in envs],
    }


def rule_messages(conftest_path: str) -> tuple[list[str], list[str], bool]:
    """Devuelve (advertencias, fallos, evaluado)."""
    path = Path(conftest_path)
    if not path.is_file():
        return [], [], False
    try:
        results = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [], [], False
    warnings = [w["msg"] for r in results for w in (r.get("warnings") or [])]
    failures = [f["msg"] for r in results for f in (r.get("failures") or [])]
    return warnings, failures, True


def render(input_path: str, summaries_dir: str, conftest_path: str, head: str) -> str:
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    summaries = load_summaries(summaries_dir)
    envs = data["envs"]
    changed = [e for e, c in envs.items() if c["delta_hours"] != 0]

    failed = data.get("failed_envs", [])

    lines = [MARKER, "## FinOps · alcance del cambio", ""]
    if failed:
        lines += [
            "> [!WARNING]",
            f"> No se pudo planificar: **{', '.join(failed)}**. "
            "El alcance está incompleto; revisa los jobs `Plan` de esta ejecución.",
            "",
        ]
    if changed:
        lines.append(
            f"**La capacidad mínima cambia en {len(changed)} de {len(envs)} entornos planificados: "
            f"{', '.join(changed)}.**"
        )
    else:
        lines.append(f"Ningún entorno cambia su capacidad mínima ({len(envs)} planificados).")
    lines += [
        "",
        "| Entorno | `min_size` | Horas mín./mes | Δ horas | Δ cómputo* | Infra fija (Infracost)** |",
        "|---|---|---|---|---|---|",
    ]
    tot_before = tot_after = tot_dh = tot_dusd = 0.0
    for env, cap in envs.items():
        infra = (summaries.get(env) or {}).get("infracost")
        mark = " ⚠️" if cap["delta_hours"] and env != "prod" else ""
        lines.append(
            f"| {env}{mark} | {fmt_int(cap['min_before'])} → {cap['min_after']} "
            f"| {fmt_int(cap['hours_before'])} → {fmt_int(cap['hours_after'])} "
            f"| {fmt_signed_int(cap['delta_hours'])} | {fmt_usd(cap['delta_compute_usd'], signed=True)} "
            f"| {fmt_usd(infra['monthly_usd']) if infra else 'no disponible'} |"
        )
        tot_before += cap["hours_before"] or 0
        tot_after += cap["hours_after"]
        tot_dh += cap["delta_hours"]
        tot_dusd += cap["delta_compute_usd"]
    for env in failed:
        lines.append(f"| {env} | plan fallido | — | — | — | — |")
    lines += [
        f"| **Total** | | {fmt_int(tot_before)} → {fmt_int(tot_after)} | **{fmt_signed_int(tot_dh)}** "
        f"| **{fmt_usd(tot_dusd, signed=True)}** | |",
        "",
    ]

    warnings, failures, evaluated = rule_messages(conftest_path)
    lines.append("### Reglas de alcance (advisory: no bloquean el merge)")
    if not evaluated:
        lines.append("- No se pudieron evaluar en esta ejecución.")
    elif not warnings and not failures:
        lines.append("- ✓ Sin observaciones.")
    lines += [f"- ⚠️ {m}" for m in warnings] + [f"- ✗ {m}" for m in failures]
    lines.append("")

    policy_lines = []
    for env, summary in summaries.items():
        infra = summary.get("infracost")
        if infra and infra["failing_policies"]:
            policy_lines.append(f"- **{env}:** " + "; ".join(infra["failing_policies"]))
    if policy_lines:
        lines += [
            "<details><summary>Políticas de Infracost que fallan (no evaluadas por este PR)</summary>",
            "",
            *policy_lines,
            "",
            "</details>",
            "",
        ]

    lines += [
        "### Supuestos",
        "- \\* Cómputo = `min_size` × 730 h × precio de lista on-demand (us-east-2, `pricing/aws-us-east-2.json`). "
        "No incluye horas del autoscaling por encima del mínimo, transferencia, descuentos ni impuestos.",
        "- \\*\\* Infracost estima NAT, ALB, RDS y EIP; no costea el ASG. Es el total del entorno, no el delta del PR.",
        "- La base es el estado desplegado. Una cifra estimada no es factura ni ahorro realizado.",
        "- Un aumento puede ser la decisión correcta: registrar motivo, responsable y fecha de revisión.",
        "",
        f"<sub>Commit `{head[:7]}` · comentario generado por el workflow `finops-pr`.</sub>",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) == 4 and argv[0] == "input":
        json.dump(build_input(*argv[1:]), sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 0
    if len(argv) == 5 and argv[0] == "render":
        sys.stdout.write(render(*argv[1:]))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
