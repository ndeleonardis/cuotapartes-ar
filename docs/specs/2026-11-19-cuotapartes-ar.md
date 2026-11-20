# cuotapartes-ar. Spec v1

Estado: aprobada el 2026-11-19.

## 1. Overview

cuotapartes-ar entrega los valores de cuotaparte de los fondos comunes de inversión argentinos, buscados por código CAFCI: el último valor de cada fondo y la serie de valores entre dos fechas. Los valores son los que la ingesta diaria ya guarda desde la planilla de la CAFCI. El servicio no los modifica. Su primer consumidor es el proceso que copia cada noche los valores a LemonHouse.

## 2. Usuarios objetivo

- **El proceso de copia de LemonHouse.** Todas las noches necesita el último valor de los fondos que se operan en LemonHouse y, la primera vez, todos los valores desde el 19/10/2026. Necesita respuestas que no obliguen a conocer cómo está guardada la planilla.
- **La dueña del servicio.** Consulta un fondo a mano para ver si el dato llegó, o para entender por qué un fondo quedó sin precio en LemonHouse, sin abrir la base.
- **Quien mire el portfolio.** Lee el repo y necesita entender qué problema resuelve y cómo se decidió cada cosa.

## 3. Contexto del problema

La CAFCI publica cada día una planilla con el valor de unos 4.300 fondos, pero solo la del último día. Su API dejó de responder en abril de 2026. La ingesta guarda la planilla todas las noches desde el 19/10, así que el histórico existe. Hoy solo se puede leer entrando a la base por un túnel, y para leerlo bien hay que conocer las trampas de la planilla: cada fila trae su propia fecha, el valor es cada 1.000 cuotapartes, algunas celdas traen marcadores de texto en vez de números y hay clases dadas de baja que siguen apareciendo.

LemonHouse necesita esos valores para mostrar cuánto vale hoy cada fondo. Si el proceso de copia leyera la base directamente, cada consumidor tendría que repetir esas reglas y quedaría atado a cómo está guardada la planilla.

Ninguna fuente pública ofrece hoy una serie de cuotapartes con códigos estables.

## 4. Señales de éxito

- El fondo IOLDOLAR muestra en LemonHouse el valor del día, y ese valor pasó por cuotapartes-ar, sin que nadie consulte la base a mano.
- Ante un fondo sin precio en LemonHouse, la dueña averigua el motivo con una sola consulta al servicio (código inexistente, fondo sin valor o planilla vieja).

## 5. Alcance

### Entra

- El último valor de uno o varios fondos, por código CAFCI.
- La serie de valores de uno o varios fondos entre dos fechas.
- El aviso de los códigos que no existen, sin cortar la respuesta de los demás.
- La fecha de la última planilla cargada, para saber si los datos están al día.
- Acceso solo para consumidores autorizados.

### Queda fuera

| Qué | Motivo |
|---|---|
| Cotizaciones del dólar | Ya las ofrecen varias fuentes y LemonHouse no las usa. No es lo que diferencia al servicio |
| Acceso público desde internet | Los términos de la CAFCI exigen su consentimiento escrito para redistribuir los datos (pendiente, tsk-009) |
| Cargar o corregir valores | Los valores vienen solo de la ingesta. Un valor escrito a mano puede quedar viejo o inventado sin que se note |
| Calcular tenencias o rendimientos | El servicio nunca recibe cantidades ni posiciones. Esas cuentas las hace cada consumidor con sus datos |
| Las demás columnas de la planilla (patrimonio, market share, sociedad gerente, etc.) | Poco impacto ahora. Quedan guardadas para un uso futuro (C14) |
| Buscar fondos por nombre | Poco impacto. LemonHouse ya tiene el código de cada fondo (C13) |
| Las revisiones que la CAFCI publica al día siguiente | La ingesta no las baja (decisión del 2026-11-04): el valor provisorio de la noche queda como definitivo |

## 6. Comportamiento esperado

### Último valor

- **C1 (P0).** DADO un código CAFCI que está en la base, CUANDO se pide su último valor, ENTONCES devuelve el código, el nombre del fondo y la clase, la fecha del valor (la que trae la fila de la planilla, no la de la carga), el valor cada 1.000 cuotapartes tal como lo publicó la CAFCI y la moneda (ARS o USD). Ejemplo: código 1234, "Fondo X - Clase A", 18/11/2026, 1.523,456789 cada 1.000, USD.
- **C2 (P0).** DADO un pedido con varios códigos, CUANDO se responde, ENTONCES trae un resultado por cada código pedido, aunque un código se repita en el pedido.
- **C3 (P0).** DADO un código que nunca estuvo en la planilla, CUANDO se pide, ENTONCES se informa como "no encontrado" y se devuelven los demás. Nunca aparece con valor 0.
- **C4 (P0).** DADO un fondo cuya última fila trae un marcador en vez de un valor (por ejemplo `(**)`), CUANDO se pide su último valor, ENTONCES devuelve el último valor numérico que haya tenido, con su fecha. Si nunca tuvo uno, lo informa como "sin valor" junto con el texto del marcador. Nunca devuelve 0.
- **C5 (P1).** DADO un fondo que dejó de aparecer en la planilla, CUANDO se pide, ENTONCES devuelve su último valor y aclara que ya no figura en la planilla desde cierta fecha.

### Serie de valores

- **C6 (P0).** DADO uno o varios códigos y un rango de fechas, CUANDO se pide la serie, ENTONCES devuelve un valor por cada fecha que tenga valor en el rango, ordenado por fecha, con los mismos datos de C1. Los días sin valor (fines de semana, feriados) no aparecen, y nunca se rellenan con el valor de otro día.
- **C7 (P0).** DADO un rango con la fecha de inicio posterior a la de fin, o con una fecha que no es una fecha válida, CUANDO se pide, ENTONCES responde un error que dice qué está mal y no devuelve valores.
- **C8 (P1).** DADO un rango que empieza antes del 19/10/2026, CUANDO se pide, ENTONCES devuelve lo que hay desde la primera fecha guardada y aclara desde cuándo hay datos.

### Estado

- **C9 (P1).** DADO cualquier momento, CUANDO se pide el estado, ENTONCES dice la fecha de la última planilla cargada y cuándo se cargó, así se puede saber si los valores están al día.

### Acceso y datos

- **C10 (P0).** DADO cualquier pedido, CUANDO se responde, ENTONCES ningún dato de la base cambia. El servicio solo lee.
- **C11 (P1).** DADO un pedido sin la credencial de un consumidor autorizado, o con una credencial inválida, CUANDO llega, ENTONCES se rechaza sin devolver ningún valor.
- **C12 (P0).** DADO un valor guardado, CUANDO el servicio lo devuelve, ENTONCES tiene exactamente los mismos dígitos que la planilla, sin redondeos.

### Futuro

- **C13 (P2).** DADO un texto, CUANDO se busca, ENTONCES devuelve los fondos cuyo nombre o sociedad gerente lo contienen, con su código.
- **C14 (P2).** DADO un fondo, CUANDO se pide su ficha, ENTONCES devuelve también el patrimonio, la sociedad gerente y las demás columnas de la planilla.
- **C15 (P2).** DADO el consentimiento escrito de la CAFCI, CUANDO se abre el servicio al público, ENTONCES cada respuesta cita a la CAFCI como fuente.

## 7. Posibles errores y mitigaciones

| Caso | Qué pasa |
|---|---|
| La base de mercado no responde | Error claro de "servicio sin datos". Nunca una respuesta vacía que parezca "no hay fondos" |
| La ingesta de la noche falló o trajo una planilla incompleta | Cada valor trae su fecha, así que un valor de ayer nunca pasa por uno de hoy. El estado (C9) muestra que la última planilla es vieja |
| Un código pedido no es un número | Se informa como inválido, junto con los demás resultados |
| Un pedido trae miles de códigos o un rango de años | Se pone un tope razonable y, si se supera, se responde un error que lo dice. Nunca se corta en silencio |
| La CAFCI cambia el formato de la planilla | Lo frena la ingesta, que falla en voz alta ante un marcador desconocido. El servicio sigue devolviendo lo último guardado, con su fecha |
| La moneda de un fondo viene vacía o con un valor desconocido | Se devuelve el valor con la moneda como "desconocida". Nunca se adivina. El consumidor decide (LemonHouse no lo guarda y avisa) |

## 8. Preguntas abiertas

- **No bloqueante.** ¿El valor de una clase en dólares viene en dólares en la planilla, según la columna `moneda` o según `moneda_fondo`? Se confirma al implementar, con la fila de IOLDOLAR contra el valor que muestra el banco.
- **No bloqueante.** ¿Cuál es el tope de códigos por pedido y de días por rango? Se fija en el plan, con el pedido de la carga inicial (todos los fondos de LemonHouse desde el 19/10) como caso de referencia.
