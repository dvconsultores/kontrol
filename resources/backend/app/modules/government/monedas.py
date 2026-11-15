"""Códigos de moneda para las tasas oficiales BCV de Gobierno (TRE-09).

El código canónico de Gobierno para la moneda nacional es VES.
El código VED fue de uso interno durante la reconversión monetaria y no
sustituyó a VES. VED -> VES es una normalización de código (factor 1), no una
conversión cambiaria.
"""

MONEDA_CANONICA = "VES"


def canonical_currency(codigo: str | None) -> str:
    """Normaliza un código de moneda al código canónico de Gobierno.

    ``None`` o una cadena vacía se normalizan a ``""``. ``VED`` se normaliza a
    ``VES``. El resto se devuelve en mayúsculas y sin espacios.
    """
    if not codigo:
        return ""
    c = codigo.strip().upper()
    if c == "VED":
        return "VES"
    return c
