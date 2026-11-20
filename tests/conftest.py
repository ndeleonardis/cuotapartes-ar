"""Base de prueba: un Postgres 17 real con el esquema de `mercado` y datos inventados.

URL_BASE_TEST apunta a un Postgres con un superusuario (por defecto, el que
levanta scripts/postgres-local.ps1). Cada corrida crea una base nueva, le aplica
db/esquema.sql y db/roles.sql, y la borra al terminar.
"""

import os
import uuid
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.types.json import Jsonb

RAIZ = Path(__file__).resolve().parent.parent
URL_ADMIN = os.environ.get(
    "URL_BASE_TEST", "postgresql://postgres@127.0.0.1:54317/postgres?connect_timeout=5"
)
CLAVE_API_LECTURA_TEST = "solo-para-tests"

# Regla 6: las semillas usan códigos que no existen en la CAFCI.
CODIGO_MINIMO_INVENTADO = 900000


def _conectar_admin(**kwargs: Any) -> psycopg.Connection:
    try:
        return psycopg.connect(URL_ADMIN, **kwargs)
    except psycopg.OperationalError as error:
        pytest.exit(
            f"No hay Postgres de prueba en {URL_ADMIN}. "
            "En Windows: scripts/postgres-local.ps1 levantar. "
            f"Detalle: {error}",
            returncode=3,
        )


@pytest.fixture(scope="session")
def url_base_admin() -> Iterator[str]:
    """Crea la base de prueba con el esquema y los roles, y devuelve su URL de superusuario."""
    nombre = f"mercado_test_{uuid.uuid4().hex[:8]}"
    with _conectar_admin(autocommit=True) as admin:
        admin.execute(f'create database "{nombre}"')
        admin.execute(
            """
            do $$ begin
              if not exists (select from pg_roles where rolname = 'ingesta') then
                create role ingesta login;
              end if;
              if not exists (select from pg_roles where rolname = 'api_lectura') then
                create role api_lectura login;
              end if;
            end $$
            """
        )
        admin.execute(
            sql.SQL("alter role api_lectura password {}").format(
                sql.Literal(CLAVE_API_LECTURA_TEST)
            )
        )
    url = make_conninfo(URL_ADMIN, dbname=nombre)
    with psycopg.connect(url, autocommit=True) as base:
        base.execute((RAIZ / "db" / "esquema.sql").read_text(encoding="utf-8"))
        base.execute((RAIZ / "db" / "roles.sql").read_text(encoding="utf-8"))
    yield url
    with _conectar_admin(autocommit=True) as admin:
        admin.execute(f'drop database "{nombre}" with (force)')


@pytest.fixture(scope="session")
def url_base_lectura(url_base_admin: str) -> str:
    """La misma base, entrando como api_lectura, que es como entra el servicio."""
    datos = conninfo_to_dict(url_base_admin)
    datos.update(user="api_lectura", password=CLAVE_API_LECTURA_TEST)
    return make_conninfo(**datos)


@pytest.fixture
def base(url_base_admin: str) -> Iterator[psycopg.Connection]:
    """Conexión de superusuario para cargar semillas. Vacía los datos después de cada test."""
    with psycopg.connect(url_base_admin, autocommit=True) as conexion:
        yield conexion
        conexion.execute(
            "truncate cafci.cuotaparte_version, cafci.captura restart identity cascade"
        )


def nueva_captura(
    base: psycopg.Connection,
    *,
    fecha_planilla: date | None = None,
    http_status: int = 200,
    capturada_en: str | None = None,
) -> int:
    """Inserta una descarga de planilla inventada y devuelve su id."""
    fila = base.execute(
        """
        insert into cafci.captura (fuente, http_status, fecha_planilla, capturada_en)
        values ('semilla', %s, %s, coalesce(%s::timestamptz, now()))
        returning id
        """,
        (http_status, fecha_planilla, capturada_en),
    ).fetchone()
    assert fila is not None
    return fila[0]


def nueva_version(
    base: psycopg.Connection,
    *,
    codigo: int,
    fecha: date | None,
    valor: Decimal | None,
    moneda: str | None = "ARS",
    fondo: str = "Fondo Inventado - Clase A",
    anotaciones: dict[str, str] | None = None,
    captura_id: int | None = None,
) -> int:
    """Inserta una versión inventada de una clase y devuelve su id."""
    if codigo < CODIGO_MINIMO_INVENTADO:
        raise ValueError(
            f"Regla 6: las semillas usan códigos desde {CODIGO_MINIMO_INVENTADO}, no {codigo}"
        )
    if captura_id is None:
        captura_id = nueva_captura(base, fecha_planilla=fecha)
    fila = base.execute(
        """
        insert into cafci.cuotaparte_version
          (captura_id, fuente, capturada_en, fila_excel, hash_contenido,
           fondo, moneda, fecha, valor_mil_cuotapartes, codigo_cafci, anotaciones)
        values (%s, 'semilla', now(), 1, %s, %s, %s, %s, %s, %s, %s)
        returning id
        """,
        (
            captura_id,
            uuid.uuid4().hex,
            fondo,
            moneda,
            fecha,
            valor,
            codigo,
            Jsonb(anotaciones) if anotaciones is not None else None,
        ),
    ).fetchone()
    assert fila is not None
    return fila[0]
