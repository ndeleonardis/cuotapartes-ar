"""T6. Serie de valores entre dos fechas (C6, C7, C8 y C3 dentro de la serie)."""

from datetime import date
from decimal import Decimal

import psycopg
import pytest
from fastapi.testclient import TestClient

from tests.conftest import nueva_version


def _serie(cliente: TestClient, codigos: str, desde: str, hasta: str) -> dict:
    respuesta = cliente.get(
        "/v1/serie", params={"codigos": codigos, "desde": desde, "hasta": hasta}
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_un_valor_por_fecha_ordenado_sin_rellenar_los_dias_que_faltan(
    cliente: TestClient, base: psycopg.Connection
):
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 20), valor=Decimal("3"))
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 17), valor=Decimal("1"), moneda="USD")
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 18), valor=Decimal("2.1"))
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 18), valor=Decimal("2.2"))
    # El 19/11 no hay valor (feriado): no aparece y no se rellena.

    respuesta = _serie(cliente, "900001", "2026-11-17", "2026-11-20")

    [serie] = respuesta["series"]
    assert serie["estado"] == "ok"
    assert serie["cada"] == 1000
    assert serie["valores"] == [
        {"fecha": "2026-11-17", "valor": "1", "moneda": "USD"},
        {"fecha": "2026-11-18", "valor": "2.2", "moneda": "ARS"},
        {"fecha": "2026-11-20", "valor": "3", "moneda": "ARS"},
    ]


def test_el_rango_incluye_sus_dos_puntas_y_nada_mas(cliente: TestClient, base: psycopg.Connection):
    for dia in (16, 17, 18, 19):
        nueva_version(base, codigo=900001, fecha=date(2026, 11, dia), valor=Decimal(dia))

    respuesta = _serie(cliente, "900001", "2026-11-17", "2026-11-18")

    assert [v["fecha"] for v in respuesta["series"][0]["valores"]] == ["2026-11-17", "2026-11-18"]


def test_un_dia_cuya_ultima_version_trae_un_marcador_no_aparece(
    cliente: TestClient, base: psycopg.Connection
):
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 18), valor=Decimal("5"))
    nueva_version(
        base,
        codigo=900001,
        fecha=date(2026, 11, 18),
        valor=None,
        anotaciones={"valor_mil_cuotapartes": "(**)"},
    )

    respuesta = _serie(cliente, "900001", "2026-11-18", "2026-11-18")

    assert respuesta["series"][0]["valores"] == []


def test_aclara_desde_cuando_hay_datos_si_el_rango_empieza_antes(
    cliente: TestClient, base: psycopg.Connection
):
    nueva_version(base, codigo=900001, fecha=date(2026, 10, 19), valor=Decimal("1"))
    nueva_version(base, codigo=900001, fecha=date(2026, 10, 20), valor=Decimal("2"))

    respuesta = _serie(cliente, "900001", "2026-10-01", "2026-10-31")

    serie = respuesta["series"][0]
    assert serie["datos_desde"] == "2026-10-19"
    assert [v["fecha"] for v in serie["valores"]] == ["2026-10-19", "2026-10-20"]


def test_codigos_que_no_existen_o_invalidos_van_junto_a_los_demas(
    cliente: TestClient, base: psycopg.Connection
):
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 18), valor=Decimal("1"))

    respuesta = _serie(cliente, "900999,900001,abc", "2026-11-01", "2026-11-30")

    assert [(s["codigo"], s["estado"], len(s["valores"])) for s in respuesta["series"]] == [
        ("900999", "no_encontrado", 0),
        ("900001", "ok", 1),
        ("abc", "invalido", 0),
    ]


@pytest.mark.parametrize(
    ("desde", "hasta", "mensaje"),
    [
        (
            "2026-11-20",
            "2026-11-17",
            "La fecha desde (2026-11-20) es posterior a hasta (2026-11-17).",
        ),
        ("2026-13-01", "2026-11-17", "La fecha desde no es válida: 2026-13-01. Usá AAAA-MM-DD."),
        ("2026-11-01", "17/11/2026", "La fecha hasta no es válida: 17/11/2026. Usá AAAA-MM-DD."),
        ("2025-01-01", "2026-11-17", "El rango puede tener hasta 400 días, pediste 686."),
    ],
)
def test_un_rango_mal_armado_responde_422_sin_valores(
    cliente: TestClient, desde: str, hasta: str, mensaje: str
):
    respuesta = cliente.get(
        "/v1/serie", params={"codigos": "900001", "desde": desde, "hasta": hasta}
    )

    assert respuesta.status_code == 422
    assert respuesta.json() == {"error": mensaje}


def test_sin_fechas_responde_422(cliente: TestClient):
    respuesta = cliente.get("/v1/serie", params={"codigos": "900001"})

    assert respuesta.status_code == 422
    assert respuesta.json() == {"error": "Faltan las fechas desde y hasta, en formato AAAA-MM-DD."}
