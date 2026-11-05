from itertools import count

from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_tre01_cuentas import HOY, crear_cuenta, cuenta_vigente

P = "/gobierno/tesoreria"
MOTIVO = "Motivo de prueba con longitud suficiente para pasar la validación."

_codigos = count(1001)


def _empresa(empresa, mundo):
    return empresa or mundo.company_a


def _cabeceras(mundo, usuario, empresa, version=None):
    cabeceras = mundo.como(usuario, empresa)
    if version is not None:
        cabeceras["If-Match"] = str(version)
    return cabeceras


def crear_rubro(mundo, tipo, usuario="ua", empresa=None, codigo=None) -> dict:
    empresa = _empresa(empresa, mundo)
    codigo = codigo or f"R{next(_codigos):04d}"
    r = _post(
        mundo,
        f"{P}/rubros",
        usuario,
        empresa,
        {"codigo": codigo, "nombre": f"Rubro {codigo}", "tipo": tipo},
    )
    assert r.status_code == 201, r.text
    return r.json()


def crear_programa(mundo, ejercicio, moneda="VES", mes_inicial=1, usuario="ua", empresa=None) -> dict:
    r = _post(
        mundo,
        f"{P}/programas",
        usuario,
        _empresa(empresa, mundo),
        {"ejercicio": ejercicio, "moneda": moneda, "mes_inicial": mes_inicial},
    )
    assert r.status_code == 201, r.text
    return r.json()


def ver(mundo, programa, usuario="ua", empresa=None, numero_version=None) -> dict:
    ruta = f"{P}/programas/{programa['id']}"
    if numero_version is not None:
        ruta = f"{ruta}?version={numero_version}"
    r = mundo.get(ruta, usuario, _empresa(empresa, mundo))
    assert r.status_code == 200, r.text
    return r.json()


def declarar(mundo, programa, cuenta, monto, usuario="ua", empresa=None) -> dict:
    r = _post(
        mundo,
        f"{P}/programas/{programa['id']}/declaraciones",
        usuario,
        _empresa(empresa, mundo),
        {
            "cuenta_id": cuenta["id"],
            "monto": monto,
            "fecha_corte": HOY.isoformat(),
            "fundamento": MOTIVO,
        },
        version=programa["version"],
    )
    assert r.status_code == 201, r.text
    return r.json()


def linea(mundo, programa, rubro, mes, monto, usuario="ua", empresa=None) -> dict:
    r = _post(
        mundo,
        f"{P}/programas/{programa['id']}/lineas",
        usuario,
        _empresa(empresa, mundo),
        {"rubro_id": rubro["id"], "mes": mes, "monto": monto},
        version=programa["version"],
    )
    assert r.status_code == 201, r.text
    return r.json()


def activar_programa(mundo, programa, usuario="ua", empresa=None) -> dict:
    r = _post(
        mundo,
        f"{P}/programas/{programa['id']}/activar",
        usuario,
        _empresa(empresa, mundo),
        {},
        version=programa["version"],
    )
    assert r.status_code == 200, r.text
    return r.json()


def reprogramar(mundo, programa, usuario="ua", empresa=None) -> dict:
    r = _post(
        mundo,
        f"{P}/programas/{programa['id']}/reprogramar",
        usuario,
        _empresa(empresa, mundo),
        {"motivo": MOTIVO},
        version=programa["version"],
    )
    assert r.status_code == 201, r.text
    return r.json()


def accion(mundo, programa, verbo, cuerpo, usuario="ua", empresa=None, version=None):
    version = programa["version"] if version is None else version
    return _post(
        mundo,
        f"{P}/programas/{programa['id']}/{verbo}",
        usuario,
        _empresa(empresa, mundo),
        cuerpo,
        version=version,
    )


def sin_if_match(mundo, ruta, cuerpo, usuario="ua", empresa=None):
    return _post(mundo, ruta, usuario, _empresa(empresa, mundo), cuerpo)


def patch_con_version(mundo, ruta, cuerpo, version, usuario="ua", empresa=None):
    cabeceras = _cabeceras(mundo, usuario, _empresa(empresa, mundo), version)
    return mundo.client.patch(f"/api/v1{ruta}", headers=cabeceras, json=cuerpo)


def delete_con_version(mundo, ruta, version, usuario="ua", empresa=None):
    cabeceras = _cabeceras(mundo, usuario, _empresa(empresa, mundo), version)
    return mundo.client.delete(f"/api/v1{ruta}", headers=cabeceras)


def cuenta_en_estado(mundo, cargo_id, estado, moneda="VES", usuario="ua", empresa=None) -> dict:
    empresa = _empresa(empresa, mundo)
    if estado == "BORRADOR":
        return crear_cuenta(mundo, usuario=usuario, empresa=empresa, moneda=moneda)
    if estado == "VIGENTE":
        return cuenta_vigente(mundo, cargo_id, usuario=usuario, empresa=empresa, moneda=moneda)
    cuenta = cuenta_vigente(mundo, cargo_id, usuario=usuario, empresa=empresa, moneda=moneda)
    if estado == "INACTIVA":
        r = _post(
            mundo,
            f"{P}/cuentas/{cuenta['id']}/inactivar",
            usuario,
            empresa,
            {"motivo": MOTIVO},
            version=cuenta["version"],
        )
    elif estado == "CERRADA":
        r = _post(
            mundo,
            f"{P}/cuentas/{cuenta['id']}/cerrar",
            usuario,
            empresa,
            {"motivo": MOTIVO, "fecha_cierre": HOY.isoformat()},
            version=cuenta["version"],
        )
    else:
        raise ValueError(f"Estado no soportado: {estado}")
    assert r.status_code == 200, r.text
    return r.json()


def programa_listo(mundo, cargo_id, ejercicio, moneda="VES", usuario="ua", empresa=None) -> dict:
    cuenta = cuenta_vigente(mundo, cargo_id, usuario=usuario, empresa=empresa, moneda=moneda)
    programa = crear_programa(mundo, ejercicio, moneda=moneda, usuario=usuario, empresa=empresa)
    rubro_ingreso = crear_rubro(mundo, "INGRESO", usuario=usuario, empresa=empresa)
    programa = declarar(mundo, programa, cuenta, "1000.00", usuario=usuario, empresa=empresa)
    return linea(mundo, programa, rubro_ingreso, 1, "500.00", usuario=usuario, empresa=empresa)


def programa_vigente(mundo, cargo_id, ejercicio, moneda="VES", usuario="ua", empresa=None) -> dict:
    programa = programa_listo(mundo, cargo_id, ejercicio, moneda=moneda, usuario=usuario, empresa=empresa)
    return activar_programa(mundo, programa, usuario=usuario, empresa=empresa)


def fijar_hoy(monkeypatch, fecha) -> None:
    monkeypatch.setattr(
        "app.modules.government.service_caja.hoy_de_negocio",
        lambda: fecha,
    )


def regla_sod_vigente(mundo, accion_a, accion_b, nombre, proceso="TRE-02") -> dict:
    r = _post(
        mundo,
        "/gobierno/sod/reglas",
        "ua",
        mundo.company_a,
        {
            "proceso": proceso,
            "accion_a": accion_a,
            "accion_b": accion_b,
            "nombre": nombre,
            "descripcion": "Descripción suficiente para la regla.",
            "vigente_desde": HOY.isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    regla = r.json()
    r = _post(
        mundo,
        f"/gobierno/sod/reglas/{regla['id']}/activar",
        "ua",
        mundo.company_a,
        {},
        version=regla["version"],
    )
    assert r.status_code == 200, r.text
    return r.json()


def cerrar_regla(mundo, regla) -> dict:
    r = _post(
        mundo,
        f"/gobierno/sod/reglas/{regla['id']}/cerrar",
        "ua",
        mundo.company_a,
        {"motivo": MOTIVO},
        version=regla["version"],
    )
    assert r.status_code == 200, r.text
    return r.json()
