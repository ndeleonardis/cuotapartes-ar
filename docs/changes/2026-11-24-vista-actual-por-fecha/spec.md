# Vista del valor actual por fecha. Spec del cambio

Estado: aprobada el 2026-11-24. Cambia la spec v1 (`docs/specs/2026-11-19-cuotapartes-ar.md`).

## 1. Overview

La base tiene una consulta del "valor actual" de cada fondo (`cafci.cuotaparte_actual`) que hoy devuelve la última versión **cargada** y no la de **fecha más reciente**. Este cambio hace que devuelva la de fecha más reciente, igual que el último valor del servicio (C1).

## 2. Usuarios objetivo

- **La dueña del servicio.** Mira el valor actual desde DBeaver y necesita ver el último día, no el último archivo que bajó.
- **La ingesta de cada noche.** Usa esta consulta para decidir si una fila es nueva. Necesita seguir sin perder cambios.
- **La copia a LemonHouse del 04/11, si está activa.** Lee el valor actual de esta consulta.

## 3. Contexto del problema

El lunes 23/11/2026 fue feriado y la CAFCI sirvió una revisión del 19/11 que pisó el archivo del 20/11. La ingesta la guardó como versiones nuevas, que es correcto porque es una revisión válida. Pero como la consulta ordena por orden de carga, 3.806 clases muestran hoy como actual el 19/11 en vez del 20/11. El servicio no se ve afectado porque ordena por fecha. Quien lea la consulta directo, sí.

## 4. Señales de éxito

- Desde DBeaver, el valor actual de IOLDOLAR coincide con el de `/v1/ultimo` y con el del banco.
- La ingesta de la noche siguiente al cambio carga una cantidad normal de versiones nuevas, sin perder ni repetir en masa.

## 5. Alcance

### Entra

- Que el valor actual de cada clase sea el de fecha más reciente y, entre versiones de la misma fecha, el último cargado.
- Que una clase sin ninguna versión con fecha siga apareciendo, con su último cargado.
- Que el mismo cambio quede en la base real y en el esquema del repo.

### Queda fuera

| Qué | Motivo |
|---|---|
| Que la ingesta deduplique sin depender de esta consulta | Más prolijo, pero obliga a cambiar y volver a probar el workflow de n8n. Ninguno de los dos órdenes pierde datos |
| Avisar cuando llega un archivo con fecha vieja | Va con las alertas de la ingesta (tsk-012) |
| Rechazar los archivos con fecha vieja | Son revisiones válidas y la serie las usa |
| Las clases dadas de baja | Otra tarea (tsk-018, C5) |
| `market_share` dentro del hash | Otra tarea (tsk-014) |
| Cambios en las rutas del servicio | El servicio ya ordena por fecha |

## 6. Comportamiento esperado

- **C16 (P0, AGREGA).** DADO una clase con versiones de fechas distintas, cargadas en cualquier orden, CUANDO se consulta el valor actual, ENTONCES devuelve la versión de fecha más reciente.
- **C17 (P0, AGREGA).** DADO una clase con varias versiones de la misma fecha (revisiones), CUANDO se consulta el valor actual, ENTONCES devuelve la última cargada de esa fecha.
- **C18 (P1, AGREGA).** DADO una clase con versiones con fecha y otras sin fecha, CUANDO se consulta el valor actual, ENTONCES gana la de fecha más reciente. DADO una clase que nunca tuvo fecha, ENTONCES aparece con su última versión cargada.
- **C19 (P0, AGREGA).** DADO el cambio aplicado, CUANDO la ingesta lee la consulta y cuando los roles de la ingesta y del servicio la leen, ENTONCES siguen pudiendo leerla con los mismos permisos de antes.

## 7. Posibles errores y mitigaciones

| Caso | Qué pasa |
|---|---|
| La CAFCI sirve el mismo archivo viejo dos noches seguidas | La ingesta lo guarda dos veces, porque compara contra la versión de fecha más reciente. Es un duplicado inofensivo y no se pierde nada. Antes pasaba lo mismo en el caso inverso |
| Una clase que tenía fecha empieza a llegar sin fecha | Se duplicaría cada noche. Hoy no hay ninguna (medido el 2026-11-24). Si aparece, se ve en el conteo de versiones nuevas |
| El cambio se aplica mientras corre la ingesta | Se aplica de día, lejos de las 23:00 |
| La base real y el esquema del repo quedan distintos | Se aplica el mismo texto en los dos lados, y después se compara la definición de la base con la del repo |

## 8. Preguntas abiertas

- **No bloqueante.** ¿Está activa en n8n la copia a LemonHouse del 04/11? Si lo está, desde el 23/11 copió el 19/11. Se corrige sola en la próxima corrida.
