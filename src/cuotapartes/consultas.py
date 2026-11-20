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

from cuotapartes.modelos import (
    CADA,
    Estado,
    EstadoDelServicio,
    Moneda,
    Resultado,
    Serie,
    ValorDelDia,
)

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


MAXIMO_DIAS = 400
_FORMATO_FECHA = "Usá AAAA-MM-DD."


def leer_rango(desde: str | None, hasta: str | None) -> tuple[date, date]:
    if not desde or not hasta:
        raise PedidoInvalido("Faltan las fechas desde y hasta, en formato AAAA-MM-DD.")
    fechas = []
    for nombre, texto in (("desde", desde), ("hasta", hasta)):
        try:
            fechas.append(date.fromisoformat(texto.strip()))
        except ValueError:
            raise PedidoInvalido(
                f"La fecha {nombre} no es válida: {texto}. {_FORMATO_FECHA}"
            ) from None
    inicio, fin = fechas
    if inicio > fin:
        raise PedidoInvalido(f"La fecha desde ({inicio}) es posterior a hasta ({fin}).")
    dias = (fin - inicio).days + 1
    if dias > MAXIMO_DIAS:
        raise PedidoInvalido(f"El rango puede tener hasta {MAXIMO_DIAS} días, pediste {dias}.")
    return inicio, fin


def serie(
    conexion: psycopg.Connection, codigos: list[CodigoPedido], desde: date, hasta: date
) -> list[Serie]:
    numeros = sorted({c.numero for c in codigos if c.numero is not None})

    # Para cada código y fecha vale la última versión cargada. Si esa versión
    # trae un marcador en vez de un número, ese día no tiene valor (C6).
    valores: dict[int, list[ValorDelDia]] = {}
    for codigo, fecha, valor, moneda in conexion.execute(
        """
        select codigo_cafci, fecha, valor_mil_cuotapartes, moneda
        from (
          select distinct on (codigo_cafci, fecha)
                 codigo_cafci, fecha, valor_mil_cuotapartes, moneda
          from cafci.cuotaparte_version
          where codigo_cafci = any(%s) and fecha between %s and %s
          order by codigo_cafci, fecha, id desc
        ) ultima_del_dia
        where valor_mil_cuotapartes > 0
        order by codigo_cafci, fecha
        """,
        (numeros, desde, hasta),
    ):
        valores.setdefault(codigo, []).append(
            ValorDelDia(fecha=fecha, valor=valor, moneda=Moneda.desde_planilla(moneda))
        )

    # Si el código existe, su nombre más reciente y desde cuándo tiene valores (C8).
    existentes: dict[int, tuple[str | None, date | None]] = {
        codigo: (fondo, primera)
        for codigo, fondo, primera in conexion.execute(
            """
            select distinct on (codigo_cafci)
                   codigo_cafci, fondo,
                   min(fecha) filter (where valor_mil_cuotapartes > 0)
                     over (partition by codigo_cafci)
            from cafci.cuotaparte_version
            where codigo_cafci = any(%s)
            order by codigo_cafci, id desc
            """,
            (numeros,),
        )
    }

    series = []
    for codigo in codigos:
        if codigo.numero is None:
            series.append(Serie(codigo=codigo.texto, estado=Estado.INVALIDO))
        elif codigo.numero not in existentes:
            series.append(Serie(codigo=codigo.texto, estado=Estado.NO_ENCONTRADO))
        else:
            fondo, primera = existentes[codigo.numero]
            series.append(
                Serie(
                    codigo=codigo.texto,
                    estado=Estado.OK,
                    fondo=fondo,
                    cada=CADA,
                    datos_desde=primera,
                    valores=valores.get(codigo.numero, []),
                )
            )
    return series


def ultima_planilla(conexion: psycopg.Connection) -> EstadoDelServicio:
    # Una planilla cargada es una descarga con respuesta 200 que trajo fecha de
    # planilla. Las descargas con error o sin archivo no cuentan.
    fila = conexion.execute(
        """
        select fecha_planilla, capturada_en
        from cafci.captura
        where http_status = 200 and fecha_planilla is not null
        order by capturada_en desc, id desc
        limit 1
        """
    ).fetchone()
    if fila is None:
        return EstadoDelServicio(
            fecha_planilla=None, cargada_en=None, aviso="Todavía no se cargó ninguna planilla."
        )
    return EstadoDelServicio(fecha_planilla=fila[0], cargada_en=fila[1])
