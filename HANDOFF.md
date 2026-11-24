# Handoff. Dónde quedó cuotapartes-ar

Última sesión: 2026-11-24.

## Hecho
- Spec (`docs/specs/2026-11-19-cuotapartes-ar.md`) y plan (`docs/plans/2026-11-19-cuotapartes-ar.md`) aprobados. C5 pasó a P2.
- Tareas T1 a T10 y T12, una por commit. Son 60 tests, la CI está en verde (tests e imagen de Docker) y hubo una prueba local con curl contra datos inventados.
- **T11, el despliegue en la VM** (2026-11-24). Servicio `cuotapartes` en `~/stack` vía `docker-compose.override.yml`, `healthy` y sin puertos publicados. `/salud`, `/v1/ultimo` y `/v1/estado` responden desde `stack-n8n-1`. El valor de IOLDOLAR que devuelve `/v1/ultimo` coincide al sexto decimal con el que publica el banco. `docs/operar.md` quedó corregida con lo que se hizo de verdad: el `.env` armado sin que las claves pasen por pantalla, el override del compose y cómo mirar la base.

## Abierto
- **Moneda.** Para IOLDOLD, `moneda` y `moneda_fondo` dicen USD, así que el caso no decide la pregunta abierta 1. En la base hay 341 clases donde las dos columnas difieren (222 USD/ARS, 45 ARS/USD, 38 USB/USD, 27 USD/USB, 6 USB/ARS y 3 ARS/USB). Para confirmar que el valor sale de `moneda`, comparar clases del mismo fondo (Adcap Balanceado I, Adcap Renta Dólar, Alpha Latam). Si sale de `moneda_fondo`, se corrige `consultas.py` con su test.
- **`USB`.** Es una tercera moneda de la planilla (¿dólar cable?). Hoy sale como `desconocida`, a propósito.
- **La vista `cuotaparte_actual`** ordena por `id desc`. El 23/11 (feriado) la CAFCI sirvió una revisión del 19/11 y la vista muestra esa fecha como la actual. El servicio no la usa, pero conviene corregirla en `db/esquema.sql` y en la base.

## Falta, en orden
1. **`verify-after-changes`** y `/code-review`.
2. **Cambio de LemonHouse** (otra spec, en `dashboard-inversiones`). Es el flujo de n8n de las 23:30 que llama a `/v1/ultimo` y guarda en `precio`, más la carga única del histórico con `/v1/serie`, el gráfico de evolución y el rendimiento por período. Antes hay que subir al real las migraciones pendientes y darle login a `carga_precios`. La clave `lemonhouse` ya existe y se carga como credencial de n8n.

## Para retomar en esta PC
- `scripts\postgres-local.ps1 levantar`, después `uv run pytest`.
- Al terminar, `scripts\postgres-local.ps1 bajar`.
