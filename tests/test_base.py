"""T2. La base de prueba tiene el esquema de `mercado`, y api_lectura solo puede leer (C10)."""

from datetime import date
from decimal import Decimal

import psycopg
import pytest
from psycopg import errors

from tests.conftest import nueva_version


def test_el_esquema_carga_y_la_vista_devuelve_la_ultima_version(base: psycopg.Connection):
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 17), valor=Decimal("1000.5"))
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 18), valor=Decimal("1001.25"))

    fila = base.execute(
        "select fecha, valor_mil_cuotapartes from cafci.cuotaparte_actual"
        " where codigo_cafci = 900001"
    ).fetchone()

    assert fila == (date(2026, 11, 18), Decimal("1001.25"))


def test_api_lectura_lee_versiones(base: psycopg.Connection, url_base_lectura: str):
    nueva_version(base, codigo=900002, fecha=date(2026, 11, 18), valor=Decimal("12.5"))

    with psycopg.connect(url_base_lectura) as lectura:
        filas = lectura.execute("select codigo_cafci from cafci.cuotaparte_version").fetchall()

    assert filas == [(900002,)]


def test_api_lectura_no_puede_escribir(base: psycopg.Connection, url_base_lectura: str):
    captura_id = base.execute(
        "insert into cafci.captura (fuente, http_status) values ('semilla', 200) returning id"
    ).fetchone()[0]

    with psycopg.connect(url_base_lectura) as lectura, pytest.raises(errors.InsufficientPrivilege):
        lectura.execute(
            "insert into cafci.cuotaparte_version"
            " (captura_id, fuente, capturada_en, fila_excel, hash_contenido, codigo_cafci)"
            " values (%s, 'x', now(), 1, 'x', 900003)",
            (captura_id,),
        )


def test_api_lectura_no_ve_las_planillas(url_base_lectura: str):
    with psycopg.connect(url_base_lectura) as lectura, pytest.raises(errors.InsufficientPrivilege):
        lectura.execute("select sha256 from cafci.planilla_archivo")


def test_las_semillas_no_usan_codigos_reales(base: psycopg.Connection):
    with pytest.raises(ValueError, match="Regla 6"):
        nueva_version(base, codigo=1234, fecha=date(2026, 11, 18), valor=Decimal("1"))
