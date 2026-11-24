# Vista del valor actual por fecha. Plan del cambio

Estado: aprobado el 2026-11-24.

## 1. Objetivo

Que `cafci.cuotaparte_actual` devuelva la versión de fecha más reciente de cada clase, en la base real y en `db/esquema.sql`, sin cambiar sus columnas ni sus permisos.

## 2. Contexto del problema

La vista ordena por `id desc`. El archivo viejo que la CAFCI sirvió el feriado del 23/11 dejó 3.806 clases mostrando el 19/11 en vez del 20/11. La ingesta usa la vista para decidir si una fila es nueva, y ninguno de los dos órdenes pierde datos.

## 3. Spec de referencia

`docs/changes/2026-11-24-vista-actual-por-fecha/spec.md`

## 4. Código existente

- `db/esquema.sql`: la definición de la vista (línea 82). Se cambia solo el `order by`.
- `db/roles.sql`: los `grant` sobre la vista. No se toca.
- `tests/test_base.py`: ya prueba que la vista devuelve la última versión, con fechas cargadas en orden. Se suman los casos nuevos ahí.
- `tests/conftest.py`: `nueva_version()` acepta `fecha=None` y `captura_id`. Se reusa sin cambios.
- `src/`: no se toca. El servicio no usa la vista.

## 5. Stack y arquitectura

- **Orden nuevo**: `order by codigo_cafci, fecha desc nulls last, id desc`. `nulls last` es obligatorio: en Postgres, `desc` pone los `NULL` primero, y sin esa cláusula una versión sin fecha le ganaría a todas.
- **En la base real se aplica con `create or replace view`**, que conserva el dueño y los `grant`. Descartado `drop` + `create`: borra los permisos y deja a la ingesta sin poder leer la vista hasta volver a darlos.
- **El SQL para la VM va en `docs/changes/2026-11-24-vista-actual-por-fecha/aplicar.sql`**, en una transacción que verifica antes del `commit`. Descartado un directorio de migraciones: es el primer cambio de esquema y una carpeta por cambio alcanza.
- **Sin índice nuevo.** La tabla tiene unas 100.000 filas y suma unas 4.000 por día hábil. Ya existe `(codigo_cafci, fecha)`.
- **Tests**: pytest contra Postgres 17, como el resto. Los permisos se prueban con `set role` desde la conexión de prueba, sin crear contraseñas nuevas.

## 6. Guardas de la constitución

| Regla | Guarda |
|---|---|
| 2. Solo lectura | El servicio no cambia. El cambio lo aplica la dueña con el superusuario del contenedor, no `api_lectura` |
| 6. Sin datos de la CAFCI | Los tests usan `nueva_version()`, que rechaza códigos menores a 900000. `aplicar.sql` no trae datos |
| 7. Secretos solo en `.env` | `aplicar.sql` no tiene credenciales: se corre con `$POSTGRES_USER` dentro del contenedor |
| 1, 3, 4 y 5 | No aplican: no cambian rutas, valores ni respuestas |

## 7. Lista de tareas

- **T1. Vista por fecha** (`db/esquema.sql`, `tests/test_base.py`). Tres tests nuevos: versiones cargadas con la fecha más nueva primero (C16); dos versiones de la misma fecha, gana la última cargada (C17); una clase con versión con fecha y después una sin fecha, gana la con fecha, y una clase sin ninguna fecha aparece igual (C18). Los tres fallan con la vista actual. Después se cambia el `order by`.
- **T2. Permisos de la vista** (`tests/test_base.py`). Test: con `set role ingesta` y con `set role api_lectura`, `select` sobre la vista funciona (C19). **Este test pasa desde antes**, porque es una guarda para que un cambio futuro no rompa los permisos. Lo que realmente prueba C19 en la base real es T3. Depende de T1.
- **T3. Aplicar en la VM** (`docs/changes/…/aplicar.sql`). En una transacción: `create or replace view` con el mismo texto de T1, y antes del `commit` muestra la cantidad de filas de la vista (la misma de antes), la fila de IOLDOLAR (tiene que dar 20/11) y los `grant`, que tienen que seguir siendo de `ingesta` y `api_lectura`. Si algo no da, `rollback`. Lo corre Noelia, de día. Después compara `pg_get_viewdef` con el repo (C16 a C19 en real). Depende de T1.
- **T4. Verificar y cerrar.** A la mañana siguiente, contar las versiones nuevas de la captura de las 23:00 y comparar con las noches anteriores (señal de éxito 2). Correr `verify-after-changes`, que fusiona C16 a C19 en la spec principal, y sacar de `docs/operar.md` el aviso de que la vista no coincide con `/v1/ultimo`. Depende de T3.

## 8. Cobertura

| Criterio | Tarea | Test o verificación |
|---|---|---|
| C16 | T1, T3 | Test de versiones cargadas en desorden. En real: IOLDOLAR da 20/11 |
| C17 | T1 | Test de dos versiones de la misma fecha |
| C18 | T1 | Test de versión sin fecha y de clase sin ninguna fecha |
| C19 | T2, T3 | Test con `set role`. En real: `grant` antes del `commit` y la ingesta de la noche |
