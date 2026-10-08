"""Entornos que un PR obliga a planificar, según los archivos cambiados.

Un cambio en el módulo, el perfil compartido, los precios o las herramientas
alcanza a todos los consumidores; un cambio en envs/<env>/ solo a ese entorno.
Revisar solo la carpeta modificada dejaría fuera a staging y dev cuando el PR
toca profiles/.

Uso:
    python tools/finops/affected_envs.py <base-sha> <head-sha>
Escribe `envs=<json>` y `reasons=<json>` en formato $GITHUB_OUTPUT.
"""

from __future__ import annotations

import json
import subprocess
import sys

ENVS = ("prod", "staging", "dev")
SHARED_PREFIXES = (
    "modules/",
    "profiles/",
    "pricing/",
    "tools/finops/",
    "policies/",
    ".github/workflows/finops-pr.yml",
)


def changed_files(base: str, head: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def affected(files: list[str]) -> dict[str, list[str]]:
    """Devuelve {entorno: [archivos que lo afectan]} en el orden de ENVS."""
    reasons: dict[str, list[str]] = {env: [] for env in ENVS}
    for path in files:
        if path.startswith(SHARED_PREFIXES):
            for env in ENVS:
                reasons[env].append(path)
            continue
        parts = path.split("/")
        if len(parts) > 2 and parts[0] == "envs" and parts[1] in reasons:
            reasons[parts[1]].append(path)
    return {env: paths for env, paths in reasons.items() if paths}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    reasons = affected(changed_files(*argv))
    print(f"envs={json.dumps(list(reasons))}")
    print(f"reasons={json.dumps(reasons)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
