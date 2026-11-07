"""Escaneo de solo lectura de líneas de recepción contradictorias (RCL-H).

Cuenta las líneas de recepción cuyo producto no coincide con el de su línea
de orden, o cuya línea de orden pertenece a otra orden. Agrupa el recuento
por estado de la recepción.

Este script es SOLO LECTURA: no modifica ni repara ninguna fila. No se puede
saber cuál era el producto correcto (el de la recepción o el de la orden),
así que la reparación queda fuera de su alcance.

Uso:
    KONTROL_DB_URL=... resources/backend/.venv/bin/python qa/recepcion_lineas_contradictorias.py

La URL de conexión nunca se imprime.
"""

from __future__ import annotations

import json
import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

CONSULTA = text(
    """
    SELECT r.status AS estado, COUNT(*) AS lineas
    FROM goods_receipt_lines gl
    JOIN goods_receipts r ON r.id = gl.receipt_id
    LEFT JOIN purchase_order_lines ol ON ol.id = gl.order_line_id
    WHERE ol.id IS NULL
       OR ol.order_id <> r.order_id
       OR ol.product_id <> gl.product_id
    GROUP BY r.status
    ORDER BY r.status
    """
)


def contar(conexion: Connection) -> dict[str, int]:
    """Devuelve {estado: número de líneas contradictorias}."""
    filas = conexion.execute(CONSULTA).all()
    return {fila.estado: fila.lineas for fila in filas}


def main() -> int:
    url = os.environ.get("KONTROL_DB_URL")
    if not url:
        print("Falta KONTROL_DB_URL.", file=sys.stderr)
        return 2
    motor = create_engine(url)
    with motor.connect() as conexion:
        if conexion.dialect.name == "postgresql":
            conexion.execute(text("SET TRANSACTION READ ONLY"))
        resultado = contar(conexion)
        conexion.rollback()
    print(
        json.dumps(
            {"por_estado": resultado, "total": sum(resultado.values())},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
