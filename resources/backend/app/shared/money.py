"""Dinero en la frontera pública: texto decimal exacto (Spec 038 · FLOAT-038-A).

Un número JSON no puede ser autoridad monetaria. `json.loads` lo convierte en
`float` antes de que nadie lo valide, y JavaScript ya lo había hecho antes de
enviarlo: `1234567890123456.78` llega como `1234567890123456.8` y PostgreSQL
guarda `1234567890123456.80`. Convertir a `Decimal` después no repara nada. Por
eso el importe viaja como **texto** y se convierte a `Decimal` una sola vez, aquí.

La escala y la precisión no se escriben a mano: se leen de la columna donde el
importe se va a guardar. Lo que no cabe se **rechaza**; no se redondea
(`OQ-FLOAT-038-A-02`). Redondear sería elegir entre dos números, y el mismo
módulo ya lo hacía de dos formas: PostgreSQL lleva `0.005` a `0.01` y `_money`
a `0.00`.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Annotated, Any

from pydantic import Field, PlainValidator, WithJsonSchema
from sqlalchemy import Numeric


def _escala_y_enteros(tipo: Numeric) -> tuple[int, int]:
    if tipo.precision is None or tipo.scale is None:
        raise TypeError("La columna monetaria debe declarar precisión y escala")
    return tipo.scale, tipo.precision - tipo.scale


def _patron(escala: int, *, con_signo: bool, exacto: bool) -> str:
    fraccion = "" if escala == 0 else (rf"\.[0-9]{{{escala}}}" if exacto else rf"(\.[0-9]{{1,{escala}}})?")
    return rf"^{'-?' if con_signo else ''}[0-9]+{fraccion}$"


def texto_decimal(tipo: Numeric, *, positivo: bool, admite_cero: bool = False) -> Any:
    """Tipo de **entrada**: texto decimal que cabe en `tipo`, convertido a `Decimal`.

    Solo acepta `str`. Un número, aunque parezca inofensivo, ya perdió
    exactitud antes de llegar. `positivo` exige un importe mayor que cero y
    prohíbe el signo; sin él, se admite `-`. `admite_cero`, junto a `positivo`,
    deja pasar también el cero: es la regla `≥ 0` del conteo de caja (FLOAT-038-B).
    """
    escala, enteros = _escala_y_enteros(tipo)
    lexico = re.compile(r"-?[0-9]+(?:\.[0-9]+)?" if not positivo else r"[0-9]+(?:\.[0-9]+)?")

    def validar(valor: object) -> Decimal:
        if not isinstance(valor, str):
            raise ValueError('el importe se envía como texto decimal, por ejemplo "1234.56"')
        if not lexico.fullmatch(valor):
            raise ValueError("el importe no es un texto decimal válido (sin exponente, espacios ni separadores)")
        importe = Decimal(valor)
        exponente = importe.as_tuple().exponent
        if isinstance(exponente, int) and -exponente > escala:
            raise ValueError(f"el importe admite como máximo {escala} decimales")
        if importe.adjusted() >= enteros:
            raise ValueError(f"el importe admite como máximo {enteros} dígitos enteros")
        if positivo and importe <= 0 and not (admite_cero and importe == 0):
            raise ValueError("el importe debe ser mayor que cero")
        return importe

    limite = (", mayor o igual que cero" if admite_cero else ", mayor que cero") if positivo else ""
    esquema = {
        "type": "string",
        "pattern": _patron(escala, con_signo=not positivo, exacto=False),
        "description": (
            f"Importe decimal exacto en texto: hasta {enteros} dígitos enteros y {escala} decimales"
            f"{limite}. Un número JSON se rechaza."
        ),
        "examples": ["1234.56"],
    }
    return Annotated[Decimal, PlainValidator(validar), WithJsonSchema(esquema)]


def texto_de_salida(tipo: Numeric) -> Any:
    """Tipo de **salida**: el importe ya formateado como texto con la escala de `tipo`."""
    escala, enteros = _escala_y_enteros(tipo)
    return Annotated[str, Field(
        pattern=_patron(escala, con_signo=True, exacto=True),
        description=f"Importe decimal exacto en texto, con {escala} decimales.",
        examples=["1234.56"],
    )]
