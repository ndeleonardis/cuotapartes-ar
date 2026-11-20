# cuotapartes-ar. Plan v1

Estado: aprobado el 2026-11-19.

## 1. Objetivo

Construir un servicio de solo lectura que, por código CAFCI, devuelva el último valor de cuotaparte y la serie entre dos fechas, leyendo la base `mercado` que ya llena la ingesta. Se despliega dentro de la VM, al lado de n8n, sin salida a internet.

## 2. Contexto del problema

La CAFCI publica solo la planilla del último día y su API no responde desde abril de 2026. La ingesta guarda todo desde el 19/10, pero leerlo bien exige conocer las trampas de la planilla: cada fila trae su propia fecha, el valor es cada 1.000 cuotapartes, hay marcadores de texto en lugar de números y versiones repetidas de un mismo día. LemonHouse necesita esos valores sin que cada consumidor repita esas reglas.

## 3. Spec de referencia

`docs/specs/2026-11-19-cuotapartes-ar.md`

## 4. Código existente

Es un producto nuevo, sin código previo. Se reusa:

- **El esquema de la base `mercado`** (`datos-financieros-ar/recursos/esquema-mercado-2026-10-19.sql`), copiado a `db/esquema.sql` sin contraseñas. Los tests levantan una base con este mismo esquema.
- **Los roles que ya existen**: el servicio entra como `api_lectura`, que solo tiene `SELECT` y no ve `planilla_archivo`.
- **Las skills del flujo SDD** de LemonHouse (`design-spec`, `design-plan`, `verify-after-changes`), copiadas a `.claude/skills/`. En `verify-after-changes`, la parte del navegador se reemplaza por llamadas al servicio.

Cómo se leen los datos guardados:

- **Una versión por día.** `cuotaparte_version` puede tener varias filas del mismo código y la misma `fecha` (cambios de `market_share`, relanzadas). Para cada (código, fecha) vale la de mayor `id`.
- **Último valor (C1, C4).** La versión con `valor_mil_cuotapartes` no nulo con la mayor `fecha`, y entre las de esa fecha la de mayor `id`. Si no hay ninguna, el código está "sin valor" y se devuelven las `anotaciones` de su última versión.
- **Estado (C9).** La última fila de `captura` con `http_status = 200`.

## 5. Stack y arquitectura

| Decisión | Alternativa descartada y por qué |
|---|---|
| **Python 3.12 + FastAPI**, administrado con `uv` (es lo que hay en esta PC, que no tiene Python suelto) | Node con Fastify: LemonHouse ya muestra TypeScript, y la spec de la plataforma del 15/10 eligió FastAPI para mostrar Python |
| **psycopg 3** con un pool chico y consultas SQL escritas a mano | Un ORM (SQLAlchemy): son tres consultas de lectura, y el ORM esconde justo el SQL que la pieza quiere mostrar |
| **Valores como `Decimal` de punta a punta, y en el JSON como texto** (`"1523.456789"`) | Números JSON: pasan por `float` en casi cualquier cliente y pierden dígitos (C12). `guardar_precios` de LemonHouse ya convierte el texto a `numeric` |
| **Sesión de solo lectura** (`default_transaction_read_only = on`) además del rol `api_lectura` | Confiar solo en el rol: si alguien le da más permisos por error, la sesión igual rechaza escribir |
| **Clave por consumidor** en el encabezado `X-Clave`, comparada en tiempo constante. Las claves van en `.env` con el formato `nombre:clave` | Sin clave, porque el servicio es interno: cualquier contenedor de la VM podría leerlo, y la spec lo pide (C11) |
| **Rutas**: `GET /v1/ultimo?codigos=…`, `GET /v1/serie?codigos=…&desde=…&hasta=…`, `GET /v1/estado`. Además, `GET /salud` sin clave y sin datos, para el chequeo del contenedor | Un solo `/cuotapartes` con parámetros opcionales: mezcla dos respuestas distintas y complica los errores |
| **Un resultado por código pedido**, con `estado` igual a `ok`, `no_encontrado`, `sin_valor` o `invalido`. El orden es el del pedido, y si un código se repite, el resultado también (C2) | Responder 404 si falta un código: corta la respuesta de los demás (C3) |
| **Topes**: hasta 100 códigos por pedido y hasta 400 días por rango, con error 422 si se pasa. La carga inicial de LemonHouse es menos de 20 fondos por unos 30 días | Sin tope: un pedido mal armado lee la tabla entera |
| **Errores en español** con el formato `{"error": "…"}`. La base caída responde 503 con "servicio sin datos" | Los mensajes de FastAPI por defecto: están en inglés y muestran la estructura interna |
| **Tests: pytest** contra un **Postgres 17 real** con `db/esquema.sql` y datos inventados. En esta PC corre con los binarios portables de Postgres (zip de EDB, sin instalar nada) y un script que la levanta y la baja. En CI, con un contenedor `postgres:17` | Docker Desktop en Windows: pesado, necesita WSL2 y no hace falta. Usar la base de la VM: mezcla pruebas con datos reales. Simular la base: las trampas a probar están en el SQL |
| **Calidad: ruff** para lint y formato | Más herramientas (mypy, pre-commit): se suman si el código crece |
| **CI en GitHub Actions**: ruff, pytest y el chequeo de repo limpio, en cada push | No hay alternativa razonable para un repo público en GitHub |
| **Despliegue**: imagen de Docker construida en la VM desde el repo, y un servicio más en el compose de `/home/ubuntu/stack`, en la red de n8n y del Postgres, **sin puertos publicados**. n8n la llama por el nombre del servicio | Publicarlo detrás de Nginx: no hace falta (n8n está en la misma red) y los términos de la CAFCI lo frenan (fuera de alcance). systemd sin Docker: el resto del stack ya es Docker |
| **Licencia MIT** y README con un resumen en inglés arriba, para el portfolio | Sin licencia: un repo público sin licencia no se puede reusar legalmente |

## 6. Guardas de la constitución

El repo todavía no tiene `CLAUDE.md`. T1 lo crea con estas reglas, y cada una tiene su guarda:

| Regla | Guarda |
|---|---|
| 1. **Español** en documentos, código y mensajes de error. El resumen en inglés del README es la única excepción | Test que recorre las rutas con pedidos inválidos y verifica que cada `error` esté en español (sin los textos por defecto de FastAPI o Pydantic) |
| 2. **Solo lectura.** El servicio nunca escribe la base | El rol `api_lectura` sin permisos de escritura, más la sesión de solo lectura. Test: un `INSERT` con la conexión del servicio falla (C10) |
| 3. **Sin valor no es cero.** Nunca se devuelve 0 ni se rellena un día con el valor de otro | Tipo: el modelo de respuesta exige `valor > 0` cuando `estado` es `ok`, y `valor` nulo en los demás estados. Tests de C3, C4 y C6 |
| 4. **Dígitos exactos.** Nunca `float` | Tipo `Decimal` en los modelos, con serialización a texto. Test con un valor de 12 decimales que vuelve idéntico (C12). Regla de ruff que avisa si aparece `float(` en `src/` |
| 5. **Cada valor lleva su fecha y su moneda** | Tipo: `fecha` y `moneda` obligatorias en el modelo de un valor. La moneda es `ARS`, `USD` o `desconocida`, nunca adivinada. Test de moneda desconocida |
| 6. **Repo público sin datos de la CAFCI.** Solo semillas inventadas | `.gitignore` con `*.xlsx` y `*.csv`. Test de repo limpio (corre también en CI): `git ls-files` no tiene planillas ni dumps, y los códigos de las semillas están en un rango que no existe en la CAFCI (900000 en adelante) |
| 7. **Secretos solo en `.env`**, que no se versiona | `.gitignore` con `.env`, y `.env.ejemplo` con valores falsos. El mismo test de repo limpio falla si se versiona un `.env`. La configuración no tiene valores por defecto para la URL de la base ni para las claves: sin `.env`, el servicio no arranca |

## 7. Lista de tareas

- **T1. Esqueleto del repo.** `pyproject.toml` (uv, FastAPI, psycopg, pytest, ruff), `CLAUDE.md` con la constitución, `.claude/skills/`, `.gitignore`, `.env.ejemplo`, `LICENSE`, `README.md` y `src/cuotapartes/`.
  Test: `tests/test_repo_limpio.py` (reglas 6 y 7), que tiene que fallar al agregar un `.env` o un `.xlsx` de prueba y pasar sin ellos.
- **T2. Base de prueba.** `db/esquema.sql`, `scripts/postgres-local.ps1` (bajar los binarios portables una vez, levantar y bajar la base) y `tests/conftest.py`. El conftest crea una base nueva por corrida, aplica el esquema, crea `api_lectura` con una contraseña de prueba y trae una fábrica de versiones inventadas.
  Test: `tests/test_base.py`. El esquema carga, y `api_lectura` no puede insertar en `cuotaparte_version` ni leer `planilla_archivo` (C10). Depende de T1.
- **T3. Configuración, conexión y salud.** `src/cuotapartes/config.py`, `db.py` (pool con sesión de solo lectura), `app.py` y `GET /salud`. Errores en español con el formato propio.
  Tests: `tests/test_conexion.py`, con un `INSERT` por la conexión del servicio que falla (C10, regla 2), la base caída que responde 503 "servicio sin datos" (sección 7 de la spec) y el servicio que no arranca sin `.env` (regla 7). Depende de T2.
- **T4. Clave por consumidor.** `src/cuotapartes/acceso.py`.
  Tests: `tests/test_acceso.py`. Sin clave o con una clave inválida responde 401 sin ningún valor, una clave válida pasa, y `/salud` no pide clave ni devuelve datos (C11). Depende de T3.
- **T5. Último valor.** `src/cuotapartes/modelos.py` y `consultas.py`, y `GET /v1/ultimo`.
  Tests: `tests/test_ultimo.py`, con estos casos:
  - Fecha de la fila y no de la carga, valor cada 1.000, moneda y nombre (C1).
  - Varios códigos y un código repetido (C2).
  - Un código que no existe, que sale `no_encontrado` y no 0 (C3).
  - Un código cuya última versión trae `(**)` y devuelve el último valor numérico con su fecha. Si nunca tuvo, sale `sin_valor` con el marcador (C4).
  - Dos versiones del mismo día, donde gana la de mayor `id`.
  - 12 decimales que vuelven exactos, y como texto (C12).
  - Moneda vacía, que sale como `desconocida` (regla 5).
  - Un código no numérico, que sale `invalido`.
  - Más de 100 códigos, que da 422 con un mensaje en español.

  Depende de T4.
- **T6. Serie.** `GET /v1/serie`.
  Tests: `tests/test_serie.py`, con estos casos:
  - Una fila por fecha, ordenada, con la última versión de cada día y sin días inventados (C6).
  - Inicio posterior al fin y fecha mal escrita, que dan 422 sin valores (C7).
  - Un rango que arranca antes del primer dato y aclara `datos_desde` (C8).
  - Más de 400 días, que da 422.
  - Un código que no existe dentro de la serie, que sale `no_encontrado`.

  Depende de T5.
- **T7. Estado.** `GET /v1/estado`.
  Test: `tests/test_estado.py`. Devuelve la fecha de la última planilla y cuándo se cargó, ignora las capturas con error y, sin capturas, lo dice en vez de responder vacío (C9). Depende de T4.
- **T8. Errores en español en todas las rutas.**
  Test: `tests/test_idioma.py` (regla 1). Depende de T5, T6 y T7.
- **T9. CI.** `.github/workflows/ci.yml`, con ruff, pytest contra `postgres:17` y el test de repo limpio.
  Verificación: la primera corrida en GitHub sale en verde. Es manual, se mira una vez. Depende de T8 y de que el repo exista en GitHub.
- **T10. Imagen y compose de ejemplo.** `Dockerfile` (usuario sin privilegios, chequeo con `/salud`) y `docs/compose-ejemplo.yml`, sin puertos publicados.
  Verificación: la imagen se construye en CI y `/salud` responde 200 dentro del contenedor (un paso de CI). Depende de T9.
- **T11. Despliegue en la VM.** Es manual y lo corrés vos:
  1. Clonar el repo en la VM y armar el `.env` (la contraseña de `api_lectura` ya está en `.env.roles`, y la clave de LemonHouse se genera ahí).
  2. Sumar el servicio al compose y levantarlo.
  3. Probar desde el contenedor de n8n: `/salud`, `/v1/estado` y `/v1/ultimo` con el código de IOLDOLAR.

  Acá se cierra la pregunta abierta 1: la fila de IOLDOLAR se compara contra el valor del banco, para saber si la moneda del valor sale de `moneda` o de `moneda_fondo`. Si sale de `moneda_fondo`, se corrige la consulta de T5 con su test.
  Verificación: la señal de éxito 2 (averiguar el motivo de un "sin precio" con una sola consulta), con un código inexistente y con uno real. Depende de T10.
- **T12. Guía de operación.** `docs/operar.md`, con cómo consultar a mano desde la VM, qué significa cada `estado`, cómo rotar una clave y cómo actualizar la imagen.
  Verificación: se sigue la guía una vez durante T11. Depende de T11.

**Lo que no entra acá.** La señal de éxito 1 (IOLDOLAR con su valor en LemonHouse) necesita el flujo de n8n y el cambio de LemonHouse, que son la otra spec. Este plan deja el servicio listo y probado desde n8n.

## 8. Cobertura

| Criterio | Tarea | Test |
|---|---|---|
| C1 | T5 | `test_ultimo.py`: fecha de la fila, valor cada 1.000, moneda y nombre |
| C2 | T5 | `test_ultimo.py`: varios códigos y código repetido |
| C3 | T5, T6 | `test_ultimo.py` y `test_serie.py`: `no_encontrado`, nunca 0 |
| C4 | T5 | `test_ultimo.py`: marcador con valor anterior y marcador sin ningún valor |
| C5 | — | Pasó a P2 al aprobar el plan. No se construye ahora. Ver la nota debajo |
| C6 | T6 | `test_serie.py`: orden, última versión del día y sin días rellenados |
| C7 | T6 | `test_serie.py`: rango invertido y fecha inválida |
| C8 | T6 | `test_serie.py`: `datos_desde` |
| C9 | T7 | `test_estado.py` |
| C10 | T2, T3 | `test_base.py` y `test_conexion.py`: escribir falla |
| C11 | T4 | `test_acceso.py` |
| C12 | T5 | `test_ultimo.py`: 12 decimales exactos y como texto |
| C13, C14, C15 | — | P2. No se construyen. El diseño no los impide: son rutas nuevas sobre las mismas tablas, y C15 suma un campo de fuente a la respuesta |

**C5 (fondo dado de baja) no se puede cubrir con los datos que hay hoy.** La ingesta guarda una versión nueva solo si cambió el contenido de la fila, así que la base no registra qué códigos vinieron en cada planilla. Que un código no tenga versiones recientes no prueba que haya salido de la planilla: puede seguir ahí sin cambios. Para saberlo, la ingesta tendría que guardar en cada corrida la lista de códigos de la planilla (unas 4.300 filas por día, poco espacio). Es un cambio en datos-financieros-ar, que se uniría a tsk-018. Decidido al aprobar el plan: C5 pasa a P2 en la spec y se retoma con ese cambio.
