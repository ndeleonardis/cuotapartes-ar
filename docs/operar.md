# Operar cuotapartes-ar

Cómo se instala en la VM, cómo se consulta a mano y cómo se mantiene. Los comandos van en la terminal de la VM (`ssh oracle`), no en la PC.

## 1. Instalar

1. **Clonar el repo** en la VM:
   ```sh
   git clone https://github.com/ndeleonardis/cuotapartes-ar.git ~/cuotapartes-ar
   ```
2. **Averiguar cómo se llama el servicio del Postgres** en el compose del stack:
   ```sh
   cd ~/stack && docker compose config --services
   ```
   El de la base `mercado` es el que va en `URL_BASE` (en el ejemplo, `postgres`).
3. **Generar la clave de LemonHouse:**
   ```sh
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   Guardala también en la credencial de n8n que va a llamar al servicio. Nunca en el repo ni en el chat.
4. **Crear el `.env`** sin que la contraseña ni la clave pasen por la pantalla ni por el historial. Primero, que la contraseña de `api_lectura` no tenga caracteres que haya que escapar en una URL:
   ```sh
   grep '^PG_API_PASSWORD=' ~/stack/.env.roles | cut -d= -f2- | grep -q '[^A-Za-z0-9._~-]' && echo "TIENE caracteres especiales" || echo "sin caracteres especiales"
   ```
   Si dice "sin caracteres especiales", armá el `.env` (el host `postgres` es el nombre del paso 2). Si dice "TIENE caracteres especiales", la contraseña va escapada con `%XX` dentro de `URL_BASE`:
   ```sh
   cd ~/cuotapartes-ar
   API_PASS=$(grep '^PG_API_PASSWORD=' ~/stack/.env.roles | cut -d= -f2-)
   read -s -p "Clave de LemonHouse: " CLAVE_LH; echo
   umask 077
   printf 'URL_BASE=postgresql://api_lectura:%s@postgres:5432/mercado\nCLAVES=lemonhouse:%s\n' "$API_PASS" "$CLAVE_LH" > .env
   unset API_PASS CLAVE_LH
   ```
   Verificalo sin mostrar valores. Tiene que dar `600`, `URL_BASE` y `CLAVES`, y `0`:
   ```sh
   stat -c '%a' .env; cut -d= -f1 .env; grep -c 'CAMBIAR' .env
   ```
5. **Sumar el servicio al stack** con un `docker-compose.override.yml`, que Docker Compose lee solo junto con `docker-compose.yml`. Así no se edita el compose principal, y el servicio no puede quedar debajo de otra sección por error. Después, levantarlo:
   ```sh
   cd ~/stack
   [ -e docker-compose.override.yml ] && echo "YA EXISTE: sumá el servicio a mano" || cp ~/cuotapartes-ar/docs/compose-ejemplo.yml docker-compose.override.yml
   docker compose config --services   # tiene que aparecer cuotapartes
   docker compose up -d --build cuotapartes
   docker compose ps cuotapartes      # Up (healthy) y PORTS solo 8000/tcp, sin 0.0.0.0
   ```
6. **Probar desde el contenedor de n8n**, que es desde donde lo va a llamar el flujo:
   ```sh
   docker exec stack-n8n-1 wget -qO- http://cuotapartes:8000/salud
   ```
   Tiene que responder `{"estado":"ok"}`.

## 2. Consultar a mano

Desde la VM, con la clave en una variable para que no quede en el historial de comandos:

```sh
read -s CLAVE   # pegá la clave y Enter
docker exec stack-n8n-1 wget -qO- --header "X-Clave: $CLAVE" \
  "http://cuotapartes:8000/v1/ultimo?codigos=1234,5678"
```

| Ruta | Para qué |
|---|---|
| `/v1/ultimo?codigos=1234,5678` | Último valor de cada fondo |
| `/v1/serie?codigos=1234&desde=2026-10-19&hasta=2026-11-19` | Valores día por día entre dos fechas (hasta 400 días) |
| `/v1/estado` | De qué fecha es la última planilla cargada y cuándo se cargó |
| `/salud` | Si el servicio está vivo y llega a la base. No pide clave ni devuelve datos |

Hasta 100 códigos por pedido. Los valores vienen **cada 1.000 cuotapartes** y como texto, para no perder decimales.

## 3. Qué significa cada estado

| `estado` | Qué pasa | Qué hacer |
|---|---|---|
| `ok` | Hay valor. `fecha` es la del valor, no la de la consulta | Si la fecha es vieja, mirar `/v1/estado`: puede que la ingesta no haya corrido |
| `no_encontrado` | El código nunca estuvo en la planilla | Revisar el código CAFCI cargado en LemonHouse |
| `sin_valor` | El código existe pero nunca tuvo un número, solo un marcador (`anotaciones` dice cuál) | Nada que corregir de este lado: la CAFCI no publica valor para esa clase |
| `invalido` | Lo pedido no es un número de código | Revisar el pedido |

Si `moneda` dice `desconocida`, la planilla trajo una moneda que no es ARS ni USD. El servicio no la adivina.

Si el servicio responde `503` con "Servicio sin datos", no llega a la base: mirar que el contenedor del Postgres esté arriba (`docker ps`).

## 4. Mantener

- **Actualizar a una versión nueva:**
  ```sh
  cd ~/cuotapartes-ar && git pull && cd ~/stack && docker compose up -d --build cuotapartes
  ```
- **Rotar una clave:** cambiarla en `~/cuotapartes-ar/.env` y en la credencial de n8n, y recrear el contenedor con `docker compose up -d cuotapartes` desde `~/stack`. La clave vieja deja de andar en ese momento.
- **Sumar un consumidor:** agregar `,nombre:clave` en `CLAVES` y recrear el contenedor.
- **Ver los registros:** `docker compose logs -f cuotapartes` desde `~/stack`. Los errores inesperados quedan ahí con el detalle, que nunca se le muestra al consumidor.
- **Mirar la base directo**, por ejemplo para comparar con lo que devuelve el servicio, sin escribir contraseñas:
  ```sh
  cd ~/stack
  docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d mercado' <<'SQL'
  select id, capturada_en, fecha_planilla, filas_datos from cafci.captura order by id desc limit 5;
  SQL
  ```
  La vista `cafci.cuotaparte_actual` toma la última versión **cargada** y no la de fecha más reciente. Si la CAFCI sirve un archivo viejo, como pasó en el feriado del 23/11/2026, puede no coincidir con `/v1/ultimo`. En ese caso el que acierta es el servicio.
