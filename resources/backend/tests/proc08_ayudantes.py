from datetime import UTC, datetime
from uuid import uuid4

from app.shared.clock import hoy_de_negocio
from tests.org06_guarda import emitir
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_doc08_paquete import _doc_real
from tests.test_gov_proc03_expedientes import E
from tests.test_gov_proc07_evaluacion import (
    _abrir_ofertas,
    _crear_criterios_contrato,
    _crear_matriz,
    _preparar,
)


def evaluacion_concluida(mundo, ocupacion, n=3):
    exp, comision = _preparar(mundo, ocupacion)

    estado = _crear_matriz(mundo, exp)
    estado, matriz_version, criterios = _crear_criterios_contrato(mundo, exp, estado)

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz/bloquear", "ua", mundo.company_a,
              {}, version=matriz_version)
    assert r.status_code == 200, r.text
    estado = r.json()
    assert estado["matriz"]["estado"] == "BLOQUEADA"
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    ofertas = []
    for i in range(1, n + 1):
        doc = _doc_real(mundo, mundo.company_a, None, f"oferta {i}".encode(), f"of{i}")
        r = mundo.post(f"/documentos/{doc}/vinculos", "ua", mundo.company_a, {
            "resource_type": "GovernmentProcurementFile",
            "resource_id": exp["id"],
        })
        assert r.status_code == 200, r.text
        exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
        oferta = _recibir_oferta(mundo, exp, "ua", mundo.company_a, f"Oferente {i}", doc)
        ofertas.append(oferta)
        exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    estado_apertura, exp = _abrir_ofertas(mundo, exp, comision, ofertas)
    matriz_version = estado_apertura["matriz"]["version"]

    estado = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a).json()
    criterios = estado["matriz"]["criterios"]
    secretario = next(m for m in comision["miembros"] if m["funcion"] == "SECRETARIO")["id"]

    for oferta in ofertas:
        for criterio in criterios:
            exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
            estado = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a).json()
            version = estado["matriz"]["version"]
            body = {
                "oferta_id": oferta["id"],
                "criterio_id": criterio["id"],
                "miembro_id": secretario,
                "matriz_version": version,
                "observacion": "Comision",
                "evidencia_documento_id": None,
            }
            if criterio["escala"] == "PUNTAJE":
                body["puntaje"] = "40.00"
            else:
                body["cumple"] = True
            r = _post(mundo, f"{E}/{exp['id']}/evaluacion/resultados", "ua", mundo.company_a,
                      body, version=exp["version"])
            assert r.status_code == 201, r.text

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/concluir", "ua", mundo.company_a,
              {}, version=exp["version"])
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    return exp, comision, ofertas


def _recibir_oferta(mundo, exp, usuario, empresa, oferente_nombre, doc_id=None):
    from tests.test_gov_proc07_evaluacion import crear_funcionario

    funcionario = crear_funcionario(mundo, usuario=usuario, empresa=empresa)
    doc_ids = [doc_id] if doc_id else []
    body = {
        "oferente_nombre": oferente_nombre,
        "oferente_documento": f"J-{uuid4().int % 100000000:08d}-{uuid4().int % 10}",
        "representante": "Representante",
        "tipo_sobre": "UNICO",
        "canal": "MEDIO_ELECTRONICO",
        "recibida_en": datetime.now(UTC).isoformat(),
        "funcionario_id": funcionario["id"],
        "confidencial": True,
        "documento_ids": doc_ids,
    }
    r = _post(mundo, f"{E}/{exp['id']}/ofertas", usuario, empresa, body, version=exp["version"])
    assert r.status_code == 201, r.text
    return r.json()


def recomendar(
    mundo,
    exp,
    comision,
    ofertas,
    resultado="ADJUDICAR",
    opciones=None,
    rechazos=None,
    causal=None,
    firmante_ids=None,
    sustituye_id=None,
    motivo_sustitucion=None,
    esperado=201,
):
    if firmante_ids is None:
        firmante_ids = [m["id"] for m in comision["miembros"]]
    cuerpo = {
        "resultado_recomendado": resultado,
        "motivacion": "Motivación de prueba",
        "examen_legal": "Examen legal",
        "examen_financiero": "Examen financiero",
        "examen_tecnico": "Examen técnico",
        "resultado_matriz": "Resultado matriz",
        "medidas_promocion": "Medidas de promoción",
        "firmante_ids": firmante_ids,
        "opciones": opciones or [],
        "rechazos": rechazos or [],
        "causal_desierta": causal,
    }
    if sustituye_id:
        cuerpo["sustituye_id"] = sustituye_id
    if motivo_sustitucion is not None:
        cuerpo["motivo_sustitucion"] = motivo_sustitucion
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/decision/recomendaciones", "ua", mundo.company_a,
              cuerpo, version=exp["version"])
    assert r.status_code == esperado, r.text
    return r.json() if esperado == 201 else r


def post_recomendacion_cruda(mundo, exp, cuerpo, usuario="ua", version=None):
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    return _post(
        mundo,
        f"{E}/{exp['id']}/decision/recomendaciones",
        usuario,
        mundo.company_a,
        cuerpo,
        version=version or exp["version"],
    )


def cargo_contrataciones(mundo, ocupacion):
    from tests.org04_ayudantes import _codigo

    with mundo.factory() as db:
        from app.modules.government.models import (
            GovernmentPosition,
            GovernmentPositionCompetency,
            GovernmentPositionVersion,
        )

        cargo = GovernmentPosition(
            company_id=mundo.company_a,
            structure_id=ocupacion["estructura"],
            unit_id=ocupacion["unidad_raiz"],
            code=_codigo("C"),
            name=f"Cargo de prueba {_codigo('N')}",
            status="VIGENTE",
            valid_from=datetime(2024, 1, 1),
            activated_at=datetime.now(UTC),
            version=1,
        )
        db.add(cargo)
        db.flush()

        comp = GovernmentPositionCompetency(
            position_id=cargo.id,
            company_id=mundo.company_a,
            action="APROBAR",
            subject="CONTRATACIONES",
            limit_type="SIN_LIMITE",
            limit_amount=None,
            limit_currency=None,
            basis="Fundamento de prueba",
        )
        db.add(comp)

        version = GovernmentPositionVersion(
            position_id=cargo.id,
            structure_id=ocupacion["estructura"],
            company_id=mundo.company_a,
            version=1,
            status="VIGENTE",
            snapshot={
                "competencias": [
                    {
                        "accion": "APROBAR",
                        "materia": "CONTRATACIONES",
                        "tipo_limite": "SIN_LIMITE",
                        "monto": None,
                        "moneda": None,
                    }
                ]
            },
            reason=None,
            actor_id=None,
        )
        db.add(version)
        db.commit()
        return str(cargo.id)


def acto_decision(mundo, cargo_id, caracter="PARTICULAR", emitido=True):
    from tests.org04_ayudantes import _codigo

    cuerpo = {
        "tipo": "RESOLUCION",
        "numero": f"DA-{_codigo('A')}",
        "fecha": hoy_de_negocio().isoformat(),
        "lugar": "Caracas",
        "cargo_id": cargo_id,
        "competencia": {"accion": "APROBAR", "materia": "CONTRATACIONES"},
        "fundamento_competencia": "Reglamento interno, art. 12",
        "funcionario": "Ana Pérez",
        "titularidad": "TITULAR",
        "caracter": caracter,
        "destinatario": "Proveedor Ejemplo, C.A.",
        "asunto": "Adjudicación de servicio",
        "hechos": "Hechos de prueba",
        "fundamentos": "Fundamentos de prueba",
        "decision": "Decisión de prueba",
    }
    r = _post(mundo, "/gobierno/actos", "ua", mundo.company_a, cuerpo)
    assert r.status_code == 201, r.text
    acto = r.json()
    if emitido:
        r_emitir = emitir(mundo, acto, "ua")
        assert r_emitir.status_code == 200, r_emitir.text
    return mundo.get(f"/gobierno/actos/{acto['id']}", "ua", mundo.company_a).json()


def acto_sin_competencia(mundo, ocupacion):
    from tests.org04_ayudantes import nuevo_cargo
    from tests.org06_guarda import acto_borrador

    cargo_id = nuevo_cargo(mundo, ocupacion)
    acto = acto_borrador(mundo, cargo_id, accion="APROBAR", materia="PRESUPUESTO")
    r = emitir(mundo, acto, "ua")
    assert r.status_code == 200, r.text
    return mundo.get(f"/gobierno/actos/{acto['id']}", "ua", mundo.company_a).json()


def acto_de_otro_ente(mundo, ocupacion):
    from tests.org04_ayudantes import _codigo, nuevo_cargo

    cargo_id = nuevo_cargo(mundo, ocupacion, empresa=mundo.company_b)
    cuerpo = {
        "tipo": "RESOLUCION",
        "numero": f"DA-{_codigo('A')}",
        "fecha": hoy_de_negocio().isoformat(),
        "lugar": "Valencia",
        "cargo_id": cargo_id,
        "competencia": {"accion": "APROBAR", "materia": "PRESUPUESTO"},
        "fundamento_competencia": "Reglamento interno, art. 12",
        "funcionario": "Otro ente",
        "titularidad": "TITULAR",
        "caracter": "PARTICULAR",
        "destinatario": "Proveedor Ejemplo, C.A.",
        "asunto": "Adjudicación de servicio",
        "hechos": "Hechos de prueba",
        "fundamentos": "Fundamentos de prueba",
        "decision": "Decisión de prueba",
    }
    r = _post(mundo, "/gobierno/actos", "ub", mundo.company_b, cuerpo)
    assert r.status_code == 201, r.text
    return r.json()
