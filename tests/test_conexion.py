"""T3. Configuración, conexión de solo lectura y salud del servicio.

Cubre C10 (el servicio nunca escribe), la regla 7 (sin .env no arranca) y el
caso de la base caída de la sección 7 de la spec.
"""

import pytest
from fastapi.testclient import TestClient
from psycopg import errors

from cuotapartes.app import crear_app
from cuotapartes.config import Configuracion, ConfiguracionInvalida, cargar_configuracion
from cuotapartes.db import BaseDeMercado
from tests.conftest import CLAVE_LEMONHOUSE_TEST


def test_la_sesion_del_servicio_es_de_solo_lectura_aunque_el_rol_pueda_escribir(
    url_base_admin: str,
):
    # Con el superusuario, que sí tiene permisos: lo que frena es la sesión.
    base = BaseDeMercado(url_base_admin)
    base.abrir()
    try:
        with base.conexion() as conexion, pytest.raises(errors.ReadOnlySqlTransaction):
            conexion.execute("insert into cafci.captura (fuente, http_status) values ('x', 200)")
    finally:
        base.cerrar()


def test_salud_responde_ok_sin_datos_de_mercado(cliente: TestClient):
    respuesta = cliente.get("/salud")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok"}


def test_salud_con_la_base_caida_responde_503_en_espanol():
    configuracion = Configuracion(
        url_base="postgresql://api_lectura:x@127.0.0.1:1/mercado?connect_timeout=1",
        claves=f"lemonhouse:{CLAVE_LEMONHOUSE_TEST}",
        espera_base_segundos=2,
    )
    with TestClient(crear_app(configuracion)) as cliente:
        respuesta = cliente.get("/salud")

    assert respuesta.status_code == 503
    assert respuesta.json() == {"error": "Servicio sin datos: la base de mercado no responde."}


def test_una_ruta_que_no_existe_responde_en_espanol(cliente: TestClient):
    respuesta = cliente.get("/no-existe")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"error": "No existe la ruta /no-existe."}


def test_sin_url_base_el_servicio_no_arranca(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.delenv("URL_BASE", raising=False)
    monkeypatch.chdir(tmp_path)  # sin .env a mano

    with pytest.raises(ConfiguracionInvalida, match="URL_BASE"):
        cargar_configuracion()
