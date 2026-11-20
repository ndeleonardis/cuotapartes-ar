"""Modelos de respuesta. Son la guarda de tres reglas de la constitución:

- Regla 3: un resultado `ok` siempre trae un valor mayor que 0, y los demás
  estados nunca traen valor. No hay forma de devolver un 0.
- Regla 4: el valor es Decimal y viaja como texto, sin notación científica.
- Regla 5: un valor `ok` siempre trae su fecha y su moneda.
"""

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, field_serializer, model_validator

CADA = 1000  # La CAFCI publica el valor cada 1.000 cuotapartes.


class Estado(StrEnum):
    OK = "ok"
    NO_ENCONTRADO = "no_encontrado"
    SIN_VALOR = "sin_valor"
    INVALIDO = "invalido"


class Moneda(StrEnum):
    ARS = "ARS"
    USD = "USD"
    DESCONOCIDA = "desconocida"

    @classmethod
    def desde_planilla(cls, texto: str | None) -> "Moneda":
        """Nunca adivina: lo que no es ARS ni USD queda como desconocida."""
        limpio = (texto or "").strip().upper()
        return cls(limpio) if limpio in (cls.ARS, cls.USD) else cls.DESCONOCIDA


class Resultado(BaseModel):
    codigo: str
    estado: Estado
    fondo: str | None = None
    fecha: date | None = None
    valor: Decimal | None = None
    cada: int | None = None
    moneda: Moneda | None = None
    anotaciones: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _reglas_3_y_5(self) -> "Resultado":
        if self.estado == Estado.OK:
            if self.valor is None or self.valor <= 0:
                raise ValueError("Regla 3: un resultado ok necesita un valor mayor que 0")
            if self.fecha is None or self.moneda is None or self.cada != CADA:
                raise ValueError("Regla 5: un resultado ok necesita fecha, moneda y cada")
        elif self.valor is not None:
            raise ValueError("Regla 3: solo un resultado ok lleva valor")
        return self

    @field_serializer("valor")
    def _valor_como_texto(self, valor: Decimal | None) -> str | None:
        return None if valor is None else format(valor, "f")


class RespuestaUltimo(BaseModel):
    resultados: list[Resultado]
