# cuotapartes-ar

> **In English.** A private, read-only service that returns the daily unit value (NAV per 1,000 units) of Argentine mutual funds (FCI) by their CAFCI code: the latest value and the series between two dates. CAFCI publishes only the last day's spreadsheet and its API stopped responding in April 2026. A nightly ingestion keeps every day since October 2026, and this service serves that history without the spreadsheet's traps. Exact decimals end to end, never a zero for a missing price. Built spec-first: see `docs/specs/` and `docs/plans/`.

Servicio de solo lectura que devuelve el valor de cuotaparte de los fondos comunes de inversión argentinos, por código CAFCI: el último valor y la serie entre dos fechas.

## Por qué existe

La CAFCI publica cada día una planilla con el valor de unos 4.300 fondos, pero solo la del último día, y su API dejó de responder en abril de 2026. Una ingesta diaria guarda la planilla todas las noches desde el 19/10/2026. Este servicio entrega ese histórico sin que cada consumidor tenga que conocer las trampas de la planilla: la fecha propia de cada fila, el valor cada 1.000 cuotapartes, los marcadores de texto en lugar de números y las versiones repetidas de un mismo día.

Su primer consumidor es [LemonHouse](https://github.com/ndeleonardis/dashboard-inversiones), que copia cada noche el valor de los fondos que se operan.

## Qué no hace

- No es público. Los términos de uso de la CAFCI piden su consentimiento escrito para redistribuir los datos.
- No carga ni corrige valores. Solo lee lo que guardó la ingesta.
- No recibe tenencias ni calcula rendimientos.

## Cómo se trabaja

Primero la spec (`docs/specs/`), después el plan (`docs/plans/`) y recién después el código, una tarea por commit y con el test escrito antes. Las reglas que no se negocian están en `CLAUDE.md`, cada una con su guarda.

```sh
uv sync
uv run pytest
uv run ruff check
```

Los tests corren contra un Postgres 17 real (ver `scripts/postgres-local.ps1`).

## Licencia

MIT. Los datos son de la CAFCI y no forman parte de este repositorio.
