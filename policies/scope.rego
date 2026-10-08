# Reglas de alcance del cambio de capacidad. Advisory: solo `warn`, nunca
# bloquean el merge. La entrada la genera tools/finops/render_comment.py.
package main

import rego.v1

nonprod := {"staging", "dev"}

raised_envs contains env if {
	some env, cap in input.envs
	cap.delta_hours > 0
}

# Un cambio en `shared` alcanza a todos los consumidores del perfil.
warn contains msg if {
	"min_size" in input.profile.shared_changed_keys
	count(raised_envs) > 1
	msg := sprintf(
		"`shared.min_size` cambió en `profiles/checkout-capacity.json`: el mínimo sube en %d entornos (%s). Si la intención es solo prod, usa `overrides.prod`.",
		[count(raised_envs), concat(", ", sort(raised_envs))],
	)
}

# Subir el mínimo de no-prod puede estar justificado (paridad para pruebas de
# carga), pero debe ser una decisión explícita.
warn contains msg if {
	some env in nonprod
	cap := input.envs[env]
	cap.delta_hours > 0
	not env in input.profile.override_envs_changed
	msg := sprintf(
		"%s hereda un mínimo de %d instancias (antes %v): +%s h/mes sin override propio. Confirma si necesita paridad de capacidad permanente.",
		[env, cap.min_after, cap.min_before, cap.delta_hours_label],
	)
}
