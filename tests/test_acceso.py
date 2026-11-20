"""T4. Solo los consumidores con clave reciben valores (C11)."""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from cuotapartes.acceso import Acceso
from cuotapartes.config import Configuracion, ConfiguracionInvalida
from tests.conftest import CLAVE_LEMONHOUSE_TEST

CLAVES = {"lemonhouse": CLAVE_LEMONHOUSE_TEST}


@pytest.fixture
def protegido() -> TestClient:
    app = FastAPI()
    acceso = Acceso(CLAVES)
    acceso.instalar(app)

    @app.get("/v1/prueba")
    def prueba(consumidor: str = Depends(acceso)) -> dict[str, str]:
        return {"valor": "1523.45", "consumidor": consumidor}

    return TestClient(app)


def test_sin_clave_responde_401_sin_ningun_valor(protegido: TestClient):
    respuesta = protegido.get("/v1/prueba")

    assert respuesta.status_code == 401
    assert respuesta.json() == {"error": "Falta la clave o no es válida."}


def test_con_una_clave_invalida_responde_401(protegido: TestClient):
    respuesta = protegido.get("/v1/prueba", headers={"X-Clave": "otra-clave-cualquiera-123456"})

    assert respuesta.status_code == 401
    assert "valor" not in respuesta.text


def test_con_una_clave_valida_pasa_y_sabe_quien_es(protegido: TestClient):
    respuesta = protegido.get("/v1/prueba", headers={"X-Clave": CLAVE_LEMONHOUSE_TEST})

    assert respuesta.status_code == 200
    assert respuesta.json()["consumidor"] == "lemonhouse"


def test_salud_no_pide_clave(cliente_sin_clave: TestClient):
    assert cliente_sin_clave.get("/salud").status_code == 200


def test_las_claves_se_leen_con_el_formato_nombre_clave():
    configuracion = Configuracion(
        url_base="postgresql://x@y/z",
        claves=f"lemonhouse:{CLAVE_LEMONHOUSE_TEST}, otro:{'b' * 24}",
    )

    assert configuracion.claves_por_consumidor() == {
        "lemonhouse": CLAVE_LEMONHOUSE_TEST,
        "otro": "b" * 24,
    }


@pytest.mark.parametrize(
    "claves",
    ["", "lemonhouse", "lemonhouse:", ":clave-larga-de-veinte-caracteres", "lemonhouse:CAMBIAR"],
)
def test_una_clave_mal_armada_o_corta_no_deja_arrancar(claves: str):
    with pytest.raises(ConfiguracionInvalida, match="CLAVES"):
        Configuracion(url_base="postgresql://x@y/z", claves=claves).claves_por_consumidor()
