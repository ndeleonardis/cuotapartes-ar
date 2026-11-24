"""T2. La base de prueba tiene el esquema de `mercado`, y api_lectura solo puede leer (C10)."""

from datetime import date
from decimal import Decimal

import psycopg
import pytest
from psycopg import errors, sql

from tests.conftest import nueva_version


def test_el_esquema_carga_y_la_vista_devuelve_la_ultima_version(base: psycopg.Connection):
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 17), valor=Decimal("1000.5"))
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 18), valor=Decimal("1001.25"))

    fila = base.execute(
        "select fecha, valor_mil_cuotapartes from cafci.cuotaparte_actual"
        " where codigo_cafci = 900001"
    ).fetchone()

    assert fila == (date(2026, 11, 18), Decimal("1001.25"))


def _actual(base: psycopg.Connection, codigo: int) -> tuple[date | None, Decimal | None] | None:
    return base.execute(
        "select fecha, valor_mil_cuotapartes from cafci.cuotaparte_actual where codigo_cafci = %s",
        (codigo,),
    ).fetchone()


def test_la_vista_toma_la_fecha_mas_reciente_aunque_se_cargue_antes(base: psycopg.Connection):
    """C16. Como el feriado del 23/11: después del 20/11 llega una revisión del 19/11."""
    nueva_version(base, codigo=900010, fecha=date(2026, 11, 19), valor=Decimal("1091.196"))
    nueva_version(base, codigo=900010, fecha=date(2026, 11, 20), valor=Decimal("1083.715"))
    nueva_version(base, codigo=900010, fecha=date(2026, 11, 19), valor=Decimal("1091.2"))

    assert _actual(base, 900010) == (date(2026, 11, 20), Decimal("1083.715"))


def test_la_vista_toma_la_ultima_revision_de_la_misma_fecha(base: psycopg.Connection):
    """C17."""
    nueva_version(base, codigo=900011, fecha=date(2026, 11, 20), valor=Decimal("10.1"))
    nueva_version(base, codigo=900011, fecha=date(2026, 11, 20), valor=Decimal("10.2"))

    assert _actual(base, 900011) == (date(2026, 11, 20), Decimal("10.2"))


def test_la_vista_prefiere_una_version_con_fecha_y_no_pierde_las_que_nunca_tuvieron(
    base: psycopg.Connection,
):
    """C18."""
    nueva_version(base, codigo=900012, fecha=date(2026, 11, 20), valor=Decimal("5.5"))
    nueva_version(base, codigo=900012, fecha=None, valor=None)
    nueva_version(base, codigo=900013, fecha=None, valor=None, anotaciones={"valor": "(**)"})

    assert _actual(base, 900012) == (date(2026, 11, 20), Decimal("5.5"))
    assert _actual(base, 900013) == (None, None)


@pytest.mark.parametrize("rol", ["ingesta", "api_lectura"])
def test_los_roles_siguen_leyendo_la_vista(base: psycopg.Connection, rol: str):
    """C19. Guarda: la ingesta compara contra la vista cada noche, y el servicio puede leerla."""
    nueva_version(base, codigo=900014, fecha=date(2026, 11, 20), valor=Decimal("7.5"))

    base.execute(sql.SQL("set role {}").format(sql.Identifier(rol)))
    try:
        fila = _actual(base, 900014)
    finally:
        base.execute("reset role")

    assert fila == (date(2026, 11, 20), Decimal("7.5"))


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
