"""T7. Estado: de qué fecha es la última planilla cargada y cuándo se cargó (C9)."""

from datetime import date

import psycopg
from fastapi.testclient import TestClient

from tests.conftest import nueva_captura


def test_devuelve_la_ultima_planilla_cargada_e_ignora_las_descargas_fallidas(
    cliente: TestClient, base: psycopg.Connection
):
    nueva_captura(base, fecha_planilla=date(2026, 11, 17), capturada_en="2026-11-17T23:00:05-03:00")
    nueva_captura(base, fecha_planilla=date(2026, 11, 18), capturada_en="2026-11-18T23:00:07-03:00")
    # Después: una descarga con error y una respuesta sin planilla.
    nueva_captura(base, http_status=500, capturada_en="2026-11-19T23:00:03-03:00")
    nueva_captura(base, fecha_planilla=None, capturada_en="2026-11-19T23:05:00-03:00")

    respuesta = cliente.get("/v1/estado")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "fecha_planilla": "2026-11-18",
        "cargada_en": "2026-11-19T02:00:07Z",
        "aviso": None,
    }


def test_sin_ninguna_planilla_lo_dice_en_vez_de_responder_vacio(cliente: TestClient):
    respuesta = cliente.get("/v1/estado")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "fecha_planilla": None,
        "cargada_en": None,
        "aviso": "Todavía no se cargó ninguna planilla.",
    }


def test_el_estado_pide_clave(cliente_sin_clave: TestClient):
    assert cliente_sin_clave.get("/v1/estado").status_code == 401
