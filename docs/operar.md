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
4. **Crear el `.env`** a partir del ejemplo, y dejarlo legible solo por tu usuario:
   ```sh
   cd ~/cuotapartes-ar && cp .env.ejemplo .env && chmod 600 .env && nano .env
   ```
   - `URL_BASE`: el usuario es `api_lectura`, la contraseña es la que está en `~/stack/.env.roles` y el host es el nombre del paso 2.
   - `CLAVES`: `lemonhouse:` seguido de la clave del paso 3.
5. **Sumar el servicio al compose** del stack con el fragmento de `docs/compose-ejemplo.yml`, sin publicar puertos, y levantarlo:
   ```sh
   cd ~/stack && docker compose up -d --build cuotapartes
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
