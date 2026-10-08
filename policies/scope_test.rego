package main

import rego.v1

cap(before, after) := {"min_before": before, "min_after": after, "delta_hours": (after - before) * 730}

shared_pr := {
	"profile": {"shared_changed_keys": ["min_size"], "override_envs_changed": []},
	"envs": {"prod": cap(2, 6), "staging": cap(2, 6), "dev": cap(2, 6)},
}

override_pr := {
	"profile": {"shared_changed_keys": [], "override_envs_changed": ["prod"]},
	"envs": {"prod": cap(2, 6), "staging": cap(2, 2), "dev": cap(2, 2)},
}

test_shared_change_warns_scope_and_each_nonprod if {
	msgs := warn with input as shared_pr
	count(msgs) == 3
	some m in msgs
	contains(m, "sube en 3 entornos (dev, prod, staging)")
}

test_prod_override_has_no_warnings if {
	count(warn) == 0 with input as override_pr
}

test_explicit_nonprod_override_is_not_flagged if {
	explicit := {
		"profile": {"shared_changed_keys": [], "override_envs_changed": ["staging"]},
		"envs": {"prod": cap(2, 2), "staging": cap(2, 6), "dev": cap(2, 2)},
	}
	count(warn) == 0 with input as explicit
}
