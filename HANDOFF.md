# Handoff. Dónde quedó cuotapartes-ar

Última sesión: 2026-11-19.

## Hecho
- Spec (`docs/specs/2026-11-19-cuotapartes-ar.md`) y plan (`docs/plans/2026-11-19-cuotapartes-ar.md`) aprobados. C5 pasó a P2.
- Tareas T1 a T10 y T12, una por commit. Son 60 tests, la CI está en verde (tests e imagen de Docker) y hubo una prueba local con curl contra datos inventados.

## Falta, en orden
1. **T11. Despliegue en la VM**, siguiendo `docs/operar.md`. Lo corre Noelia, porque los comandos con sudo no los corre Claude.
   - Ver cómo se llama el servicio del Postgres en `~/stack` y armar el `.env` (contraseña de `api_lectura` en `~/stack/.env.roles`, clave nueva para LemonHouse).
   - Sumar el servicio al compose sin puertos, levantarlo y probarlo desde `stack-n8n-1`.
   - Con el código de IOLDOLAR: comparar la fila contra el valor del banco y confirmar si la moneda sale de `moneda` o de `moneda_fondo`. Si es `moneda_fondo`, se corrige `consultas.py` con su test.
   - Corregir la guía donde no coincida con la VM.
2. **`verify-after-changes`** y `/code-review`.
3. **Cambio de LemonHouse** (otra spec, en `dashboard-inversiones`). Es el flujo de n8n de las 23:30 que llama a `/v1/ultimo` y guarda en `precio`, más la carga única del histórico con `/v1/serie`, el gráfico de evolución y el rendimiento por período. Antes hay que subir al real las migraciones pendientes y darle login a `carga_precios`.

## Para retomar en esta PC
- `scripts\postgres-local.ps1 levantar`, después `uv run pytest`.
- Al terminar, `scripts\postgres-local.ps1 bajar`.
