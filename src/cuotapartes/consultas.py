"""Las consultas a la base `mercado` y las reglas para leer la planilla guardada.

- `cuotaparte_version` puede tener varias filas del mismo código y la misma
  fecha (cambios de market share, relanzadas). Para cada código y fecha vale la
  de mayor id.
- La fecha que importa es la de la fila, no la de la descarga.
- Si la planilla trajo un marcador de texto en vez de un número, el valor quedó
  nulo y el texto está en `anotaciones`.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

import psycopg

from cuotapartes.modelos import CADA, Estado, Moneda, Resultado

MAXIMO_CODIGOS = 100
_MAXIMO_INT4 = 2_147_483_647


class PedidoInvalido(Exception):
    """El pedido está mal armado. Se responde 422 con este mensaje."""


@dataclass(frozen=True)
class CodigoPedido:
    texto: str
    numero: int | None  # None si el texto no es un código válido


def leer_codigos(parametro: str | None) -> list[CodigoPedido]:
    if parametro is None or not parametro.strip():
        raise PedidoInvalido("Falta el parámetro codigos, por ejemplo ?codigos=1234,5678.")
    textos = [t.strip() for t in parametro.split(",")]
    if len(textos) > MAXIMO_CODIGOS:
        raise PedidoInvalido(
            f"Se pueden pedir hasta {MAXIMO_CODIGOS} códigos por vez, llegaron {len(textos)}."
        )
    codigos = []
    for texto in textos:
        valido = texto.isascii() and texto.isdigit() and 0 < int(texto) <= _MAXIMO_INT4
        codigos.append(CodigoPedido(texto, int(texto) if valido else None))
    return codigos


def _no_encontrado(codigo: str) -> Resultado:
    return Resultado(codigo=codigo, estado=Estado.NO_ENCONTRADO)


def _invalido(codigo: str) -> Resultado:
    return Resultado(codigo=codigo, estado=Estado.INVALIDO)


def _ok(codigo: str, fondo: str | None, fecha: date, valor: Decimal, moneda: str | None):
    return Resultado(
        codigo=codigo,
        estado=Estado.OK,
        fondo=fondo,
        fecha=fecha,
        valor=valor,
        cada=CADA,
        moneda=Moneda.desde_planilla(moneda),
    )


def ultimo_valor(conexion: psycopg.Connection, codigos: list[CodigoPedido]) -> list[Resultado]:
    numeros = sorted({c.numero for c in codigos if c.numero is not None})

    # El último valor numérico de cada código: la mayor fecha y, en esa fecha,
    # la versión de mayor id (C1, C4).
    con_valor: dict[int, tuple[Any, ...]] = {
        fila[0]: fila
        for fila in conexion.execute(
            """
            select distinct on (codigo_cafci)
                   codigo_cafci, fondo, fecha, valor_mil_cuotapartes, moneda
            from cafci.cuotaparte_version
            where codigo_cafci = any(%s)
              and valor_mil_cuotapartes > 0
              and fecha is not null
            order by codigo_cafci, fecha desc, id desc
            """,
            (numeros,),
        )
    }
    # La última versión de cada código, tenga valor o no: dice si el código
    # existe y, si nunca tuvo valor, qué marcador trajo (C3, C4).
    ultima_version: dict[int, tuple[Any, ...]] = {
        fila[0]: fila
        for fila in conexion.execute(
            """
            select distinct on (codigo_cafci) codigo_cafci, fondo, anotaciones
            from cafci.cuotaparte_version
            where codigo_cafci = any(%s)
            order by codigo_cafci, id desc
            """,
            (numeros,),
        )
    }

    resultados = []
    for codigo in codigos:
        if codigo.numero is None:
            resultados.append(_invalido(codigo.texto))
        elif codigo.numero in con_valor:
            _, fondo, fecha, valor, moneda = con_valor[codigo.numero]
            resultados.append(_ok(codigo.texto, fondo, fecha, valor, moneda))
        elif codigo.numero in ultima_version:
            _, fondo, anotaciones = ultima_version[codigo.numero]
            resultados.append(
                Resultado(
                    codigo=codigo.texto,
                    estado=Estado.SIN_VALOR,
                    fondo=fondo,
                    anotaciones=anotaciones,
                )
            )
        else:
            resultados.append(_no_encontrado(codigo.texto))
    return resultados
