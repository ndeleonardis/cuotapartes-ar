# cuotapartes-ar. Contexto para Claude

## Qué es
Servicio de solo lectura que devuelve el valor de cuotaparte de los fondos comunes de inversión argentinos por código CAFCI: el último valor y la serie entre dos fechas. Lee la base `mercado`, que llena una ingesta diaria de n8n desde la planilla de la CAFCI. Corre dentro de la VM, al lado de n8n, sin salida a internet. Su primer consumidor es LemonHouse.

## Reglas no negociables (constitución)
1. **Español** en documentos, código y mensajes de error. El resumen en inglés del README es la única excepción.
2. **Solo lectura.** El servicio nunca escribe la base.
3. **Sin valor no es cero.** Nunca se devuelve 0 ni se rellena un día con el valor de otro.
4. **Dígitos exactos.** Los valores son `Decimal` de punta a punta y viajan como texto. Nunca `float`.
5. **Cada valor lleva su fecha y su moneda.** La moneda es `ARS`, `USD` o `desconocida`, nunca adivinada.
6. **Repo público sin datos de la CAFCI.** Solo semillas inventadas, con códigos desde 900000.
7. **Secretos solo en `.env`**, que no se versiona.

Cada regla tiene una guarda en código (permiso de la base, test o tipo). Están en la sección 6 de cada plan. Una regla que solo está escrita acá no cuenta como guarda.

## Metodología (Spec-Driven Development)
Flujo con las skills de `.claude/skills/`.
1. `design-spec` escribe la spec en `docs/specs/` si es producto nuevo, o en `docs/changes/AAAA-MM-DD-nombre/` si es un cambio. Tiene approval gate.
2. `design-plan` escribe el plan, con un test por cada criterio de la spec. Tiene approval gate.
3. Se implementa tarea por tarea. Test que falla, código, test que pasa, y 1 commit por tarea.
4. `verify-after-changes` corre los tests, llama al servicio de verdad y chequea la deriva entre código y spec.
5. `/code-review` antes de dar algo por terminado.

No se escribe código sin spec y plan aprobados.

## Comandos
- `uv sync`, `uv run pytest` y `uv run ruff check`.
- Los tests necesitan un Postgres 17. En Windows: `scripts/postgres-local.ps1 levantar` (y `bajar` al terminar).

## Archivos clave
- `docs/specs/` y `docs/plans/`. El ciclo SDD.
- `db/esquema.sql`. El esquema de la base `mercado`, sin contraseñas. Los tests lo usan tal cual.
- `.claude/skills/`. Las skills del flujo.
