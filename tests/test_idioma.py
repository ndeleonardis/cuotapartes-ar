"""T8. Todos los errores del servicio están en español y con la forma {"error": "..."}
(regla 1), y toda ruta de /v1 pide clave (C11)."""

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from cuotapartes.app import crear_app
from tests.conftest import CLAVE_LEMONHOUSE_TEST, _configuracion

TEXTOS_EN_INGLES = (
    "Not Found",
    "Method Not Allowed",
    "Field required",
    "Internal Server Error",
    "Unauthorized",
    "Unprocessable",
    "detail",
)


def _es_error_en_espanol(texto: str, cuerpo: dict) -> bool:
    return (
        list(cuerpo) == ["error"]
        and isinstance(cuerpo["error"], str)
        and not any(ingles in texto for ingles in TEXTOS_EN_INGLES)
    )


@pytest.mark.parametrize(
    ("metodo", "ruta", "con_clave"),
    [
        ("GET", "/no-existe", True),
        ("POST", "/v1/ultimo", True),
        ("GET", "/v1/ultimo", True),
        ("GET", "/v1/ultimo?codigos=" + ",".join(["1"] * 101), True),
        ("GET", "/v1/serie?codigos=1&desde=ayer&hasta=hoy", True),
        ("GET", "/v1/serie?codigos=1", True),
        ("GET", "/v1/estado", False),
        ("GET", "/v1/ultimo?codigos=1", False),
    ],
)
def test_cada_error_esta_en_espanol(cliente: TestClient, metodo: str, ruta: str, con_clave: bool):
    encabezados = {} if con_clave else {"X-Clave": ""}

    respuesta = cliente.request(metodo, ruta, headers=encabezados)

    assert respuesta.status_code >= 400
    assert _es_error_en_espanol(respuesta.text, respuesta.json()), respuesta.text


def test_un_error_inesperado_responde_500_en_espanol_sin_detalles_internos(
    url_base_lectura: str, monkeypatch: pytest.MonkeyPatch
):
    def falla(*_: object) -> None:
        raise RuntimeError("detalle interno que no tiene que salir")

    monkeypatch.setattr("cuotapartes.app.ultimo_valor", falla)
    app = crear_app(_configuracion(url_base_lectura))
    encabezados = {"X-Clave": CLAVE_LEMONHOUSE_TEST}
    with TestClient(app, headers=encabezados, raise_server_exceptions=False) as cliente:
        respuesta = cliente.get("/v1/ultimo", params={"codigos": "900001"})

    assert respuesta.status_code == 500
    assert respuesta.json() == {"error": "Error interno del servicio."}


def test_toda_ruta_de_v1_pide_clave(cliente_sin_clave: TestClient):
    app = cliente_sin_clave.app
    # Ninguna ruta /v1 se agrega directo a la app, por fuera del router con clave.
    sueltas = [r.path for r in app.routes if isinstance(r, APIRoute) and r.path.startswith("/v1")]
    assert sueltas == []

    rutas = [r.path for r in app.state.router_v1.routes if isinstance(r, APIRoute)]

    assert sorted(rutas) == ["/v1/estado", "/v1/serie", "/v1/ultimo"]
    for ruta in rutas:
        assert cliente_sin_clave.get(ruta).status_code == 401, ruta
