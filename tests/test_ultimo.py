"""T5. Último valor de uno o varios fondos (C1, C2, C3, C4, C12 y reglas 3 y 5)."""

from datetime import date
from decimal import Decimal

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from cuotapartes.modelos import CADA, Estado, Moneda, Resultado
from tests.conftest import nueva_captura, nueva_version


def _resultados(cliente: TestClient, codigos: str) -> list[dict]:
    respuesta = cliente.get("/v1/ultimo", params={"codigos": codigos})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["resultados"]


def test_devuelve_la_fecha_de_la_fila_el_valor_cada_mil_la_moneda_y_el_nombre(
    cliente: TestClient, base: psycopg.Connection
):
    # La planilla se descargó el 19/11, pero la fila trae el valor del 18/11 (C1).
    captura = nueva_captura(base, fecha_planilla=date(2026, 11, 19))
    nueva_version(
        base,
        codigo=900001,
        fecha=date(2026, 11, 18),
        valor=Decimal("1523.456789"),
        moneda="USD",
        fondo="Fondo Inventado Dólar - Clase A",
        captura_id=captura,
    )

    [resultado] = _resultados(cliente, "900001")

    assert resultado == {
        "codigo": "900001",
        "estado": "ok",
        "fondo": "Fondo Inventado Dólar - Clase A",
        "fecha": "2026-11-18",
        "valor": "1523.456789",
        "cada": 1000,
        "moneda": "USD",
        "anotaciones": None,
    }


def test_varios_codigos_y_uno_repetido_dan_un_resultado_por_codigo_pedido(
    cliente: TestClient, base: psycopg.Connection
):
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 18), valor=Decimal("10"))
    nueva_version(base, codigo=900002, fecha=date(2026, 11, 18), valor=Decimal("20"))

    resultados = _resultados(cliente, "900002,900001,900002")

    assert [(r["codigo"], r["valor"]) for r in resultados] == [
        ("900002", "20"),
        ("900001", "10"),
        ("900002", "20"),
    ]


def test_un_codigo_que_no_existe_sale_no_encontrado_y_nunca_con_cero(
    cliente: TestClient, base: psycopg.Connection
):
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 18), valor=Decimal("10"))

    resultados = _resultados(cliente, "900001,900999")

    assert resultados[0]["estado"] == "ok"
    assert resultados[1] == {
        "codigo": "900999",
        "estado": "no_encontrado",
        "fondo": None,
        "fecha": None,
        "valor": None,
        "cada": None,
        "moneda": None,
        "anotaciones": None,
    }


def test_si_la_ultima_fila_trae_un_marcador_devuelve_el_ultimo_valor_numerico(
    cliente: TestClient, base: psycopg.Connection
):
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 17), valor=Decimal("99.5"))
    nueva_version(
        base,
        codigo=900001,
        fecha=date(2026, 11, 18),
        valor=None,
        anotaciones={"valor_mil_cuotapartes": "(**)"},
    )

    [resultado] = _resultados(cliente, "900001")

    assert (resultado["estado"], resultado["fecha"], resultado["valor"]) == (
        "ok",
        "2026-11-17",
        "99.5",
    )


def test_si_nunca_tuvo_valor_sale_sin_valor_con_el_marcador(
    cliente: TestClient, base: psycopg.Connection
):
    nueva_version(
        base,
        codigo=900001,
        fecha=date(2026, 11, 18),
        valor=None,
        anotaciones={"valor_mil_cuotapartes": "(**)"},
        fondo="Fondo Sin Valor - Clase B",
    )

    [resultado] = _resultados(cliente, "900001")

    assert resultado["estado"] == "sin_valor"
    assert resultado["valor"] is None
    assert resultado["fondo"] == "Fondo Sin Valor - Clase B"
    assert resultado["anotaciones"] == {"valor_mil_cuotapartes": "(**)"}


def test_dos_versiones_del_mismo_dia_gana_la_ultima_cargada(
    cliente: TestClient, base: psycopg.Connection
):
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 18), valor=Decimal("100.1"))
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 18), valor=Decimal("100.2"))

    [resultado] = _resultados(cliente, "900001")

    assert resultado["valor"] == "100.2"


def test_un_valor_con_muchos_decimales_vuelve_exacto_y_como_texto(
    cliente: TestClient, base: psycopg.Connection
):
    nueva_version(
        base, codigo=900001, fecha=date(2026, 11, 18), valor=Decimal("1234567.123456789012")
    )

    respuesta = cliente.get("/v1/ultimo", params={"codigos": "900001"})

    assert '"valor":"1234567.123456789012"' in respuesta.text


def test_una_moneda_vacia_o_rara_sale_desconocida(cliente: TestClient, base: psycopg.Connection):
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 18), valor=Decimal("1"), moneda=None)
    nueva_version(base, codigo=900002, fecha=date(2026, 11, 18), valor=Decimal("1"), moneda="EUR")

    resultados = _resultados(cliente, "900001,900002")

    assert [r["moneda"] for r in resultados] == ["desconocida", "desconocida"]


def test_un_codigo_que_no_es_un_numero_sale_invalido_junto_a_los_demas(
    cliente: TestClient, base: psycopg.Connection
):
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 18), valor=Decimal("1"))

    resultados = _resultados(cliente, "abc,900001,-5,99999999999")

    assert [r["estado"] for r in resultados] == ["invalido", "ok", "invalido", "invalido"]
    assert resultados[0]["codigo"] == "abc"


def test_mas_de_cien_codigos_responde_422_en_espanol(cliente: TestClient):
    codigos = ",".join(str(900000 + i) for i in range(101))

    respuesta = cliente.get("/v1/ultimo", params={"codigos": codigos})

    assert respuesta.status_code == 422
    assert respuesta.json() == {"error": "Se pueden pedir hasta 100 códigos por vez, llegaron 101."}


def test_sin_codigos_responde_422_en_espanol(cliente: TestClient):
    respuesta = cliente.get("/v1/ultimo")

    assert respuesta.status_code == 422
    assert respuesta.json() == {
        "error": "Falta el parámetro codigos, por ejemplo ?codigos=1234,5678."
    }


def test_sin_clave_no_devuelve_valores(cliente_sin_clave: TestClient, base: psycopg.Connection):
    nueva_version(base, codigo=900001, fecha=date(2026, 11, 18), valor=Decimal("1"))

    respuesta = cliente_sin_clave.get("/v1/ultimo", params={"codigos": "900001"})

    assert respuesta.status_code == 401


def test_el_modelo_no_deja_armar_un_ok_con_cero_ni_un_sin_valor_con_valor():
    with pytest.raises(ValidationError, match="Regla 3"):
        Resultado(
            codigo="1",
            estado=Estado.OK,
            fecha=date(2026, 11, 18),
            valor=Decimal("0"),
            cada=CADA,
            moneda=Moneda.ARS,
        )
    with pytest.raises(ValidationError, match="Regla 3"):
        Resultado(codigo="1", estado=Estado.SIN_VALOR, valor=Decimal("5"))
    with pytest.raises(ValidationError, match="Regla 5"):
        Resultado(codigo="1", estado=Estado.OK, valor=Decimal("5"), cada=CADA)


def test_el_valor_nunca_sale_en_notacion_cientifica():
    resultado = Resultado(
        codigo="1",
        estado=Estado.OK,
        fecha=date(2026, 11, 18),
        valor=Decimal("1E+3"),
        cada=CADA,
        moneda=Moneda.ARS,
    )

    assert resultado.model_dump(mode="json")["valor"] == "1000"
