# Shift-Left FinOps · demo multi-entorno

Demo de la charla *Shift-Left FinOps That Developers Don't Hate*. Un servicio de checkout desplegado en tres entornos (prod, staging y dev) que comparten un perfil de capacidad. El objetivo es que un PR muestre, antes del merge, a qué entornos alcanza un cambio y cuántas horas-instancia mínimas compromete.

## Estado

| Parte | Estado |
|---|---|
| Bootstrap de la cuenta (presupuesto, rol OIDC de solo lectura, bucket de estado) | Aplicado |
| Módulo `checkout-service` y entornos `envs/{prod,staging,dev}` | Desplegado en sesiones de demo; se destruye al terminar |
| Workflow de PR (plan, estimación, reglas y comentario) | `.github/workflows/finops-pr.yml` |

## Estructura

```
platform/bootstrap/        Cuenta: presupuesto, OIDC, rol de GitHub Actions, bucket de estado
modules/checkout-service/  VPC, ALB, ASG y RDS PostgreSQL
envs/{prod,staging,dev}/   Un root y un estado por entorno
profiles/                  Perfil de capacidad compartido
pricing/                   Precios de lista de AWS usados para el cómputo del ASG
policies/                  Reglas Rego de alcance (advisory) y sus pruebas
tools/finops/              Entornos afectados, resumen por entorno y comentario del PR
.github/workflows/         finops-pr: feedback en cada pull request
```

`profiles/checkout-capacity.json` define `shared` (aplica a los tres entornos) y `overrides.<env>` (aplica a uno). Cambiar `shared.min_size` cambia el mínimo de prod, staging y dev a la vez.

## Qué hace el workflow en un PR

1. Detecta los entornos que el cambio alcanza. Un cambio en `profiles/` o `modules/` alcanza a los tres, aunque el diff no toque `envs/`.
2. Ejecuta `terraform plan` en cada uno con un rol OIDC de solo lectura.
3. Calcula horas-instancia mínimas y costo de lista del ASG (`tools/finops`) y la infraestructura fija con Infracost.
4. Evalúa reglas de alcance con Conftest. Son advisory: avisan, no bloquean.
5. Publica un único comentario que se actualiza en cada push.

Solo el resumen de cada entorno sale del job; el plan completo, con ARNs e IDs de la cuenta, no se publica.

## Decisiones y límites

- Una sola cuenta AWS con VPC y estado separados por entorno. En una organización real cada entorno tendría su propia cuenta.
- El ALB usa HTTP: la demo no tiene dominio ni certificado.
- prod: 2 NAT y RDS Multi-AZ. staging y dev: 1 NAT y RDS en una AZ.
- El ASG no fija `desired_capacity`; la controla el autoscaling dentro de `min_size` y `max_size`.
- Los costos que muestre la demo son estimaciones de precio de lista o mediciones de pocas horas. No son una factura mensual ni ahorro realizado.

## Uso local

Requiere Terraform (versión en `.terraform-version`) y credenciales de AWS.

```bash
terraform -chdir=envs/prod init
terraform -chdir=envs/prod plan
```

GitHub Actions solo ejecuta `plan` con un rol de lectura. Los `apply` se hacen en local y la infraestructura se destruye al terminar cada sesión.
