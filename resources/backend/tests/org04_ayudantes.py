"""Ayudantes para las pruebas de ORG-04 (ocupación de cargos)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from app.modules.documents.models import Document, DocumentType
from app.modules.government.models import (
    GovernmentAct,
    GovernmentEntity,
    GovernmentPosition,
    GovernmentPositionCompetency,
    GovernmentPositionVersion,
    GovernmentStructure,
    GovernmentUnit,
)
from app.shared.clock import hoy_de_negocio
from tests.test_gov_ctl06_hallazgos import _post

O = "/gobierno/ocupacion"  # noqa: E741
ANIO = hoy_de_negocio().year

TZ_CARACAS = UTC


def D(mes: int, dia: int) -> date:
    """Devuelve una fecha del ejercicio en curso."""
    return date(ANIO, mes, dia)


_contador = {"n": 0}


def _codigo(prefijo: str) -> str:
    """Genera un código único para las pruebas."""
    _contador["n"] += 1
    return f"{prefijo}-{_contador['n']:04d}-{uuid.uuid4().hex[:6]}"


@pytest.fixture(scope="module")
def ocupacion(mundo):
    """Siembra empresas A y B con estructuras, unidades y cargos para ORG-04."""
    company_a = mundo.company_a
    company_b = mundo.company_b

    with mundo.factory() as db:
        ente_a = GovernmentEntity(
            company_id=company_a,
            denominacion="Ente activo ORG-04",
            status="ACTIVO",
            nivel_territorial="MUNICIPAL",
            version=1,
            activated_at=datetime.now(UTC),
        )
        db.add(ente_a)
        db.flush()

        estructura_a = GovernmentStructure(
            company_id=company_a,
            entity_id=ente_a.id,
            exercise=ANIO,
            status="VIGENTE",
            version=1,
            published_at=datetime(ANIO, 1, 1, 12, 0, tzinfo=TZ_CARACAS),
        )
        db.add(estructura_a)
        db.flush()

        unidad_raiz = GovernmentUnit(
            company_id=company_a,
            structure_id=estructura_a.id,
            parent_id=None,
            code=_codigo("U-RAIZ"),
            name="Unidad raíz ORG-04",
            unit_type="UNIDAD_ADMINISTRATIVA",
            status="ACTIVA",
            valid_from=D(1, 1),
            version=1,
        )
        db.add(unidad_raiz)
        db.flush()

        unidad_hija = GovernmentUnit(
            company_id=company_a,
            structure_id=estructura_a.id,
            parent_id=unidad_raiz.id,
            code=_codigo("U-HIJA"),
            name="Unidad hija ORG-04",
            unit_type="UNIDAD_ADMINISTRATIVA",
            status="ACTIVA",
            valid_from=D(1, 1),
            version=1,
        )
        db.add(unidad_hija)

        unidad_otra = GovernmentUnit(
            company_id=company_a,
            structure_id=estructura_a.id,
            parent_id=None,
            code=_codigo("U-OTRA"),
            name="Unidad hermana ORG-04",
            unit_type="UNIDAD_ADMINISTRATIVA",
            status="ACTIVA",
            valid_from=D(1, 1),
            version=1,
        )
        db.add(unidad_otra)
        db.flush()

        cargo_emisor = GovernmentPosition(
            company_id=company_a,
            structure_id=estructura_a.id,
            unit_id=unidad_raiz.id,
            code=_codigo("C-EMI"),
            name="Cargo emisor ORG-04",
            status="VIGENTE",
            valid_from=D(1, 1),
            activated_at=datetime.now(UTC),
            version=1,
        )
        db.add(cargo_emisor)
        db.flush()

        ente_b = GovernmentEntity(
            company_id=company_b,
            denominacion="Ente activo ORG-04 B",
            status="ACTIVO",
            nivel_territorial="MUNICIPAL",
            version=1,
            activated_at=datetime.now(UTC),
        )
        db.add(ente_b)
        db.flush()

        estructura_b = GovernmentStructure(
            company_id=company_b,
            entity_id=ente_b.id,
            exercise=ANIO,
            status="VIGENTE",
            version=1,
            published_at=datetime(ANIO, 1, 1, 12, 0, tzinfo=TZ_CARACAS),
        )
        db.add(estructura_b)
        db.flush()

        unidad_b = GovernmentUnit(
            company_id=company_b,
            structure_id=estructura_b.id,
            parent_id=None,
            code=_codigo("U-B"),
            name="Unidad B ORG-04",
            unit_type="UNIDAD_ADMINISTRATIVA",
            status="ACTIVA",
            valid_from=D(1, 1),
            version=1,
        )
        db.add(unidad_b)
        db.flush()

        cargo_b = GovernmentPosition(
            company_id=company_b,
            structure_id=estructura_b.id,
            unit_id=unidad_b.id,
            code=_codigo("C-B"),
            name="Cargo B ORG-04",
            status="VIGENTE",
            valid_from=D(1, 1),
            activated_at=datetime.now(UTC),
            version=1,
        )
        db.add(cargo_b)
        db.flush()

        db.commit()

        return {
            "estructura": str(estructura_a.id),
            "unidad_raiz": str(unidad_raiz.id),
            "unidad_hija": str(unidad_hija.id),
            "unidad_otra": str(unidad_otra.id),
            "cargo_emisor": str(cargo_emisor.id),
            "cargo_b": str(cargo_b.id),
            "estructura_b": str(estructura_b.id),
            "unidad_b": str(unidad_b.id),
        }


def _competencias_y_version(
    db,
    cargo: GovernmentPosition,
    structure_id,
    company_id,
) -> None:
    """Crea las dos competencias y la versión 1 del cargo."""
    for accion_, materia, tipo_limite, monto, moneda in (
        ("FIRMAR", "PRESUPUESTO", "SIN_LIMITE", None, None),
        ("APROBAR", "PRESUPUESTO", "MONTO", "1000.00", "VES"),
    ):
        comp = GovernmentPositionCompetency(
            position_id=cargo.id,
            company_id=company_id,
            action=accion_,
            subject=materia,
            limit_type=tipo_limite,
            limit_amount=monto,
            limit_currency=moneda,
            basis="Fundamento de prueba",
        )
        db.add(comp)

    version = GovernmentPositionVersion(
        position_id=cargo.id,
        structure_id=structure_id,
        company_id=company_id,
        version=1,
        status="VIGENTE",
        snapshot={
            "competencias": [
                {
                    "accion": "FIRMAR",
                    "materia": "PRESUPUESTO",
                    "tipo_limite": "SIN_LIMITE",
                    "monto": None,
                    "moneda": None,
                },
                {
                    "accion": "APROBAR",
                    "materia": "PRESUPUESTO",
                    "tipo_limite": "MONTO",
                    "monto": "1000.00",
                    "moneda": "VES",
                },
            ]
        },
        reason=None,
        actor_id=None,
    )
    db.add(version)


def nuevo_cargo(
    mundo,
    ocupacion,
    unidad="unidad_raiz",
    status="VIGENTE",
    valid_to=None,
    empresa=None,
) -> str:
    """Crea un cargo con sus competencias y versión 1. Devuelve el id."""
    if empresa == mundo.company_b or (isinstance(empresa, str) and empresa == str(mundo.company_b)):
        company_id = mundo.company_b
        structure_id = ocupacion["estructura_b"]
        unit_id = ocupacion["unidad_b"]
    else:
        company_id = empresa if empresa is not None else mundo.company_a
        structure_id = ocupacion["estructura"]
        unit_id = ocupacion[unidad]

    if status == "INACTIVO" and valid_to is None:
        raise AssertionError("Un cargo INACTIVO exige valid_to.")

    with mundo.factory() as db:
        cargo = GovernmentPosition(
            company_id=company_id,
            structure_id=structure_id,
            unit_id=unit_id,
            code=_codigo("C"),
            name=f"Cargo de prueba {_codigo('N')}",
            status=status,
            valid_from=D(1, 1),
            valid_to=valid_to,
            activated_at=None if status == "BORRADOR" else datetime.now(UTC),
            version=1,
        )
        db.add(cargo)
        db.flush()

        _competencias_y_version(db, cargo, structure_id, company_id)
        db.commit()
        return str(cargo.id)


def crear_funcionario(mundo, usuario="ua", empresa=None, nombre=None) -> dict:
    """Crea un funcionario por API y devuelve el detalle."""
    if nombre is None:
        nombre = f"Funcionario {_codigo('F')}"
    numero_documento = f"{uuid.uuid4().int % 10**8:08d}"
    cuerpo_ = {
        "nombre": nombre,
        "tipo_documento": "V",
        "numero_documento": numero_documento,
    }
    r = _post(mundo, f"{O}/funcionarios", usuario, empresa or mundo.company_a, cuerpo_)
    assert r.status_code == 201, r.text
    return r.json()


def acto_eficaz(
    mundo,
    cargo_id,
    fecha=None,
    titularidad="TITULAR",
    medio="PERSONAL",
    status="EFICAZ",
    fecha_eficacia=None,
    empresa=None,
    delegacion=False,
) -> str:
    """Crea y devuelve el id de un acto para las pruebas de ocupación."""
    company_id = empresa if empresa is not None else mundo.company_a
    if fecha is None:
        fecha = D(1, 5)
    if status == "EFICAZ" and fecha_eficacia is None:
        fecha_eficacia = fecha
    if status != "EFICAZ":
        fecha_eficacia = None

    with mundo.factory() as db:
        tipo = db.execute(
            select(DocumentType).where(
                DocumentType.company_id == company_id,
                DocumentType.code == "GOV-ORG04",
            )
        ).scalar_one_or_none()
        if tipo is None:
            tipo = DocumentType(
                company_id=company_id,
                code="GOV-ORG04",
                name="Acto de prueba ORG-04",
            )
            db.add(tipo)
            db.flush()

        doc = Document(
            company_id=company_id,
            document_type_id=tipo.id,
            title="Acto ORG-04",
            status="ACTIVE",
        )
        db.add(doc)
        db.flush()

        numero = uuid.uuid4().hex[:12]
        delegacion_numero = None
        delegacion_fecha = None
        if titularidad == "DELEGACION":
            delegacion_numero = "D-1"
            delegacion_fecha = D(1, 2)
        del delegacion  # parámetro de forma, se admite pero no se usa

        acto = GovernmentAct(
            company_id=company_id,
            tipo="RESOLUCION",
            denominacion_tipo="",
            denominacion_clave="",
            numero=numero,
            numero_clave=numero,
            fecha=fecha,
            lugar="Naguanagua",
            cargo_id=cargo_id,
            competencia_accion="APROBAR",
            competencia_materia="PRESUPUESTO",
            fundamento_competencia="Fundamento de prueba",
            funcionario="Funcionario de prueba",
            titularidad=titularidad,
            caracter="GENERAL",
            asunto="Acto de prueba ORG-04",
            status=status,
            documento_acto_id=doc.id,
            emitido_en=datetime.now(UTC),
            medio=medio,
            referencia_publicacion="Ref. prueba",
            fecha_publicacion_notificacion=fecha,
            fecha_eficacia=fecha_eficacia,
            delegacion_numero=delegacion_numero,
            delegacion_fecha=delegacion_fecha,
        )
        db.add(acto)
        db.commit()
        return str(acto.id)


def cuerpo(funcionario, cargo_id, acto_id, figura="TITULAR", **cambios) -> dict:
    """Devuelve un cuerpo por defecto para POST de asignaciones."""
    datos = {
        "funcionario_id": funcionario["id"],
        "cargo_id": cargo_id,
        "figura": figura,
        "acto_id": acto_id,
        "desde": D(2, 1).isoformat(),
        "fundamento": "Fundamento legal de la asignación de prueba.",
    }
    datos.update(cambios)
    return datos


def post_asignacion(mundo, datos, usuario="ua", empresa=None):
    """POST de asignación y devuelve la respuesta."""
    return _post(mundo, f"{O}/asignaciones", usuario, empresa or mundo.company_a, datos)


def crear(mundo, datos, usuario="ua", empresa=None) -> dict:
    """Crea una asignación y devuelve su detalle."""
    r = post_asignacion(mundo, datos, usuario=usuario, empresa=empresa)
    assert r.status_code == 201, r.text
    return r.json()


def accion(
    mundo,
    asig,
    verbo,
    cuerpo=None,
    usuario="uab",
    empresa=None,
    version=None,
):
    """Ejecuta una acción sobre una asignación."""
    if version is None:
        version = asig.get("version") if isinstance(asig, dict) else None
    asig_id = asig["id"] if isinstance(asig, dict) else asig
    return _post(
        mundo,
        f"{O}/asignaciones/{asig_id}/{verbo}",
        usuario,
        empresa or mundo.company_a,
        cuerpo,
        version=version,
    )


def activa(mundo, datos, usuario="ua", activador="uab", empresa=None) -> dict:
    """Crea y activa una asignación."""
    asig = crear(mundo, datos, usuario=usuario, empresa=empresa)
    r = accion(mundo, asig, "activar", usuario=activador, empresa=empresa)
    assert r.status_code == 200, r.text
    return r.json()


def titular_activo(mundo, ocupacion, cargo_id=None) -> tuple[dict, str]:
    """Crea cargo (si falta), funcionario y acto; activa TITULAR."""
    if cargo_id is None:
        cargo_id = nuevo_cargo(mundo, ocupacion)
    funcionario = crear_funcionario(mundo)
    acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos = cuerpo(funcionario, cargo_id, acto_id, figura="TITULAR")
    asig = activa(mundo, datos)
    return asig, cargo_id
