"""Arnés hostil reutilizable de aislamiento multi-tenant/empresa para pruebas backend.

Mundo generado:
- Tenant TA creado vía initialize: empresas A1 y A2, admin_a (ADMIN + FUNCIONAL_COMPLETO).
- Tenant TB manual: empresas B1 y B2, admin_b (ADMIN + FUNCIONAL_COMPLETO).
- Actores: a1_op (TA, FUNCIONAL, alcance A1), a12_op (TA, FUNCIONAL, alcance A1+A2),
  a1_consulta (TA, R_ISO_CONSULTA_TA, alcance A1), a1_aud (TA, R_ISO_AUDIT_TA, alcance A1),
  a_aud_t (TA, R_ISO_AUDIT_TA, sin alcance = todas), admin_a (TA, sin alcance),
  b1_op (TB, FUNCIONAL, alcance B1), admin_b (TB, sin alcance).
- Centinelas: cadenas "ZZ<clave_empresa><hex>" sembradas por ORM en code/name/lot/serial/reference
  de cada recurso y registradas en `centinelas` solo cuando realmente se persisten en una columna.
- Contrato público: `MundoHostil` (pedir/cabeceras/fugas/huella/contar/empresas_visibles),
  `CasoHostil` y `ejecutar_caso` (verifica estado, código, no fugas, huella inmutable y auditoría),
  más `DIMENSIONES` y `tablas_de_empresa`.

Extensión a ente/unidad/autoridad (sin implementar Gobierno): añadir la dimensión a `DIMENSIONES`,
crear sus modelos/recetas en el mundo (p. ej. un Ente por tenant y unidades por empresa), sembrar
centinelas en sus columnas y ampliar `recursos`/`centinelas` y, si procede, `empresas_visibles`/`fugas`.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core import clock
from app.core.company_context import COMPANY_HEADER
from app.core.database import Base, get_db, init_models
from app.core.scope import Scope, declared_scope
from app.modules.documents.models import DocumentCategory, DocumentType
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Role, UserRole, UserScope
from app.modules.inventory.models import InventoryLot, MovementType, ProductSerial
from app.modules.master_data.models import (
    CatalogItem,
    Customer,
    Party,
    Product,
    ProfileVersion,
    Supplier,
    TaxonomyNode,
    UnitOfMeasure,
)
from app.modules.organization.models import Branch, Company, Installation, Tenant, Warehouse
from app.modules.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    Payment,
    PurchaseOrder,
    PurchaseOrderLine,
    ReceiptIncident,
)
from app.modules.setup.api import SetupRequest, _bootstrap_roles, initialize
from app.modules.treasury.models import (
    BankTransaction,
    Cashbox,
    FinancialAccount,
    FinancialBank,
    PaymentMethod,
    TreasuryInstrument,
)
from tests.conftest import make_engine

CLAVE = "Kx9!" + secrets.token_urlsafe(16)
PG = os.environ.get("KONTROL_TEST_DB_URL", "")
DIMENSIONES: tuple[str, ...] = ("tenant", "company")


@dataclass(frozen=True)
class Actor:
    username: str
    tenant: str
    user_id: str


@dataclass
class MundoHostil:
    client: TestClient
    factory: sessionmaker
    tenants: dict[str, str]
    empresas: dict[str, str]
    tenant_de_empresa: dict[str, str]
    actores: dict[str, Actor]
    recursos: dict[str, dict[str, str]]
    centinelas: dict[str, set[str]]
    _tokens: dict[str, str]

    def cabeceras(self, actor: str, empresa: str | None = None) -> dict[str, str]:
        token = self._tokens[actor]
        cabeceras = {"Authorization": f"Bearer {token}"}
        if empresa is not None:
            cabeceras[COMPANY_HEADER] = empresa
        return cabeceras

    def pedir(
        self,
        actor: str,
        metodo: str,
        ruta: str,
        *,
        empresa: str | None = None,
        json: object | None = None,
        params: dict | None = None,
    ) -> httpx.Response:
        return self.client.request(
            metodo,
            f"/api/v1{ruta}",
            headers=self.cabeceras(actor, empresa),
            json=json,
            params=params,
        )

    def refrescar_reautenticacion(self, actor: str) -> None:
        """Renueva la reautenticación de las sesiones del actor (REAUTH_MAX_AGE = 300 s).

        Un barrido largo supera la ventana; el usuario real la renovaría confirmando su identidad.
        Se sella con el reloj de la aplicación, el mismo que usa el servidor.
        """
        with self.factory() as db:
            db.execute(
                text("UPDATE sessions SET reauth_at = :ahora WHERE user_id = :usuario"),
                {"ahora": clock.now(), "usuario": self.actores[actor].user_id},
            )
            db.commit()

    def empresas_visibles(self, actor: str) -> set[str]:
        actor_datos = self.actores[actor]
        tenant = actor_datos.tenant
        with self.factory() as db:
            alcances = db.execute(
                select(UserScope.company_id).where(UserScope.user_id == actor_datos.user_id)
            ).scalars().all()
        if not alcances:
            return {empresa for empresa, t in self.tenant_de_empresa.items() if t == tenant}
        alcances_set = set(alcances)
        return {clave for clave, emp_id in self.empresas.items() if emp_id in alcances_set}

    def fugas(self, actor: str, texto: str) -> list[str]:
        visibles = self.empresas_visibles(actor)
        fugas: list[str] = []
        for empresa, centinelas in self.centinelas.items():
            if empresa in visibles:
                continue
            for centinela in centinelas:
                if centinela in texto:
                    fugas.append(centinela)
        return fugas

    def huella(self, tablas: list[str] | None = None) -> dict[str, tuple[int, str]]:
        if tablas is None:
            tablas = tablas_de_empresa()
        resultado: dict[str, tuple[int, str]] = {}
        for tabla in tablas:
            if tabla not in Base.metadata.tables:
                raise ValueError(f"Tabla no válida: {tabla}")
            nombre = Base.metadata.tables[tabla].name
            with self.factory() as db:
                fila = db.execute(
                    text(
                        f"SELECT count(*), md5(coalesce(string_agg(t::text, '|' ORDER BY t::text), '')) "
                        f"FROM {nombre} t"
                    )
                ).one()
            resultado[tabla] = (int(fila[0]), str(fila[1]))
        return resultado

    def contar(self, tabla: str, **igual: str) -> int:
        if tabla not in Base.metadata.tables:
            raise ValueError(f"Tabla no válida: {tabla}")
        columnas = Base.metadata.tables[tabla].c
        condiciones: list[str] = []
        valores: dict[str, Any] = {}
        for idx, (columna, valor) in enumerate(igual.items()):
            if columna not in columnas:
                raise ValueError(f"Columna no válida en {tabla}: {columna}")
            parametro = f"p{idx}"
            condiciones.append(f"{columna} = :{parametro}")
            valores[parametro] = valor
        nombre = Base.metadata.tables[tabla].name
        consulta = f"SELECT count(*) FROM {nombre}"
        if condiciones:
            consulta += " WHERE " + " AND ".join(condiciones)
        with self.factory() as db:
            return int(db.execute(text(consulta), valores).scalar_one())


@dataclass
class CasoHostil:
    nombre: str
    actor: str
    metodo: str
    ruta: str
    empresa_activa: str | None = None
    json: object | None = None
    params: dict | None = None
    estado: int | tuple[int, ...] = 404
    codigo: str | None = None
    tablas_inmutables: list[str] | None = None
    auditoria: str | None = None


def tablas_de_empresa() -> list[str]:
    tablas: list[str] = []
    for mapper in Base.registry.mappers:
        if declared_scope(mapper.class_) is Scope.COMPANY:
            tablas.append(mapper.local_table.name)
    for nombre in ("roles", "user_roles", "user_scopes"):
        if nombre not in tablas:
            tablas.append(nombre)
    return sorted(tablas)


def _auditoria_del_actor(mundo: MundoHostil, user_id: str) -> int:
    with mundo.factory() as db:
        return int(
            db.execute(
                text(
                    "SELECT count(*) FROM audit_events WHERE user_id = :uid "
                    "AND action NOT LIKE 'LOGIN%' AND action NOT LIKE 'SESSION%' "
                    "AND action NOT LIKE 'MFA%'"
                ),
                {"uid": user_id},
            ).scalar_one()
        )


def ejecutar_caso(mundo: MundoHostil, caso: CasoHostil) -> httpx.Response:
    actor_datos = mundo.actores[caso.actor]
    user_id = actor_datos.user_id
    huella_antes = mundo.huella(caso.tablas_inmutables)
    auditoria_antes = _auditoria_del_actor(mundo, user_id)

    respuesta = mundo.pedir(
        caso.actor,
        caso.metodo,
        caso.ruta,
        empresa=caso.empresa_activa,
        json=caso.json,
        params=caso.params,
    )

    estados = caso.estado if isinstance(caso.estado, tuple) else (caso.estado,)
    assert respuesta.status_code in estados, (
        f"{caso.nombre}: estado {respuesta.status_code} no está en {estados}; texto={respuesta.text}"
    )

    if caso.codigo is not None:
        cuerpo = respuesta.json()
        assert cuerpo.get("code") == caso.codigo, (
            f"{caso.nombre}: código {cuerpo.get('code')} != {caso.codigo}; texto={respuesta.text}"
        )

    fugas = mundo.fugas(caso.actor, respuesta.text)
    assert not fugas, f"{caso.nombre}: fugas de centinelas detectadas: {fugas}"

    huella_despues = mundo.huella(caso.tablas_inmutables)
    assert huella_antes == huella_despues, (
        f"{caso.nombre}: las tablas inmutables cambiaron: antes={huella_antes}, después={huella_despues}"
    )

    auditoria_despues = _auditoria_del_actor(mundo, user_id)
    delta = auditoria_despues - auditoria_antes

    if caso.auditoria is None:
        assert delta == 0, (
            f"{caso.nombre}: se esperaban 0 eventos de auditoría nuevos, se detectaron {delta}"
        )
    else:
        assert delta == 1, (
            f"{caso.nombre}: se esperaba 1 evento de auditoría, se detectaron {delta}"
        )
        with mundo.factory() as db:
            accion = db.execute(
                text(
                    "SELECT action FROM audit_events WHERE user_id = :uid "
                    "AND action NOT LIKE 'LOGIN%' AND action NOT LIKE 'SESSION%' "
                    "AND action NOT LIKE 'MFA%' "
                    "ORDER BY event_time DESC, id DESC LIMIT 1"
                ),
                {"uid": user_id},
            ).scalar_one()
        assert accion == caso.auditoria, (
            f"{caso.nombre}: acción de auditoría {accion} != {caso.auditoria}"
        )

    return respuesta


@pytest.fixture(scope="module")
def mundo_hostil() -> MundoHostil:
    if "postgresql" not in PG:
        pytest.skip("El aislamiento hostil se certifica sobre PostgreSQL (P21)")

    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    import app.core.database as dm
    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]

    db = factory()
    try:
        r = initialize(
            db,
            SetupRequest(
                tenant_code="TA",
                tenant_name="Tenant A",
                company_code="A1",
                company_legal_name="Empresa A1 CA",
                company_rif="J-10000001-1",
                admin_username="admin_a",
                admin_password=CLAVE,
            ),
        )
        tenant_a_id = str(r["tenant_id"])
        company_a1_id = str(r["company_id"])
        admin_a_id = str(r["admin_user_id"])

        company_a2 = Company(
            tenant_id=tenant_a_id,
            code="A2",
            legal_name="Empresa A2 CA",
            rif="J-10000002-2",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add(company_a2)
        db.flush()
        company_a2_id = str(company_a2.id)

        instalacion = db.query(Installation).first()
        tenant_b = Tenant(
            installation_id=str(instalacion.id),
            code="TB",
            name="Tenant B",
            plan="MONO_COMPANY",
            status="ACTIVE",
        )
        db.add(tenant_b)
        db.flush()
        tenant_b_id = str(tenant_b.id)

        company_b1 = Company(
            tenant_id=tenant_b_id,
            code="B1",
            legal_name="Empresa B1 CA",
            rif="J-20000001-1",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add(company_b1)
        db.flush()
        company_b1_id = str(company_b1.id)

        company_b2 = Company(
            tenant_id=tenant_b_id,
            code="B2",
            legal_name="Empresa B2 CA",
            rif="J-20000002-2",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add(company_b2)
        db.flush()
        company_b2_id = str(company_b2.id)

        admin_b = identity_service.create_user(
            db,
            tenant_id=tenant_b_id,
            username="admin_b",
            email=None,
            password=CLAVE,
            must_change_password=False,
            created_by=None,
        )
        admin_b_id = str(admin_b.id)

        rol_admin_tb = _bootstrap_roles(db, tenant_b_id, admin_b_id)

        rol_funcional = db.execute(
            select(Role).where(
                Role.code == "FUNCIONAL_COMPLETO",
                Role.company_id.is_(None),
                Role.protected.is_(True),
            )
        ).scalars().one()

        db.add_all(
            [
                UserRole(user_id=admin_a_id, role_id=str(rol_funcional.id), company_id=None),
                UserRole(user_id=admin_b_id, role_id=str(rol_admin_tb.id), company_id=None),
                UserRole(user_id=admin_b_id, role_id=str(rol_funcional.id), company_id=None),
            ]
        )
        db.flush()

        dict_empresas = {
            "A1": company_a1_id,
            "A2": company_a2_id,
            "B1": company_b1_id,
            "B2": company_b2_id,
        }
        tenant_de_empresa = {
            "A1": "TA",
            "A2": "TA",
            "B1": "TB",
            "B2": "TB",
        }

        for clave_empresa, empresa_id in dict_empresas.items():
            branch = Branch(
                company_id=empresa_id,
                code=f"S{clave_empresa}",
                name=f"Sucursal {clave_empresa}",
                status="ACTIVE",
            )
            db.add(branch)
        db.flush()

        for tenant_code, tenant_id, actor_admin in (
            ("TA", tenant_a_id, admin_a_id),
            ("TB", tenant_b_id, admin_b_id),
        ):
            identity_service.create_role(
                db,
                tenant_id=tenant_id,
                code=f"R_ISO_CONSULTA_{tenant_code}",
                name=f"Consulta aislamiento {tenant_code}",
                company_id=None,
                permissions=["inventario:view"],
                actor=actor_admin,
            )
            identity_service.create_role(
                db,
                tenant_id=tenant_id,
                code=f"R_ISO_AUDIT_{tenant_code}",
                name=f"Auditoría aislamiento {tenant_code}",
                company_id=None,
                permissions=["audit:view"],
                actor=actor_admin,
            )

        rol_consulta_ta = db.execute(
            select(Role).where(Role.code == "R_ISO_CONSULTA_TA", Role.company_id.is_(None))
        ).scalars().one()
        rol_audit_ta = db.execute(
            select(Role).where(Role.code == "R_ISO_AUDIT_TA", Role.company_id.is_(None))
        ).scalars().one()


        actores: dict[str, Actor] = {
            "admin_a": Actor("admin_a", "TA", admin_a_id),
            "admin_b": Actor("admin_b", "TB", admin_b_id),
        }

        def crear_usuario(
            username: str,
            tenant_id: str,
            tenant_code: str,
            roles: list[Role],
            empresas: list[str] | None = None,
        ) -> None:
            usuario = identity_service.create_user(
                db,
                tenant_id=tenant_id,
                username=username,
                email=None,
                password=CLAVE,
                must_change_password=False,
                created_by=None,
            )
            user_id = str(usuario.id)
            actores[username] = Actor(username, tenant_code, user_id)
            for rol in roles:
                db.add(UserRole(user_id=user_id, role_id=str(rol.id), company_id=None))
            if empresas is not None:
                for empresa_id in empresas:
                    db.add(UserScope(user_id=user_id, company_id=empresa_id))
            db.flush()

        crear_usuario(
            "a1_op",
            tenant_a_id,
            "TA",
            [rol_funcional],
            [company_a1_id],
        )
        crear_usuario(
            "a12_op",
            tenant_a_id,
            "TA",
            [rol_funcional],
            [company_a1_id, company_a2_id],
        )
        crear_usuario(
            "a1_consulta",
            tenant_a_id,
            "TA",
            [rol_consulta_ta],
            [company_a1_id],
        )
        crear_usuario(
            "a1_aud",
            tenant_a_id,
            "TA",
            [rol_audit_ta],
            [company_a1_id],
        )
        crear_usuario(
            "a_aud_t",
            tenant_a_id,
            "TA",
            [rol_audit_ta],
            None,
        )
        crear_usuario(
            "b1_op",
            tenant_b_id,
            "TB",
            [rol_funcional],
            [company_b1_id],
        )

        recursos: dict[str, dict[str, str]] = {}
        centinelas: dict[str, set[str]] = {}

        for clave_empresa, empresa_id in dict_empresas.items():
            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            centinelas[clave_empresa] = set()
            recursos[clave_empresa] = {}

            party = Party(company_id=empresa_id, code=sent, name=sent)
            db.add(party)
            db.flush()
            party_id = str(party.id)
            recursos[clave_empresa]["party"] = party_id
            centinelas[clave_empresa].add(sent)

            supplier = Supplier(party_id=party_id)
            db.add(supplier)
            db.flush()
            recursos[clave_empresa]["supplier"] = str(supplier.id)

            customer = Customer(party_id=party_id)
            db.add(customer)
            db.flush()
            recursos[clave_empresa]["customer"] = str(customer.id)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            item = CatalogItem(company_id=empresa_id, item_type="PRODUCT", code=sent, name=sent)
            db.add(item)
            db.flush()
            item_id = str(item.id)
            recursos[clave_empresa]["product"] = item_id
            centinelas[clave_empresa].add(sent)

            product = Product(item_id=item_id)
            db.add(product)
            db.flush()

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            unidad = UnitOfMeasure(
                company_id=empresa_id,
                symbol=sent[:16],
                code=sent,
                name=sent,
            )
            db.add(unidad)
            db.flush()
            recursos[clave_empresa]["unit"] = str(unidad.id)
            centinelas[clave_empresa].add(sent)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            taxonomia = TaxonomyNode(
                company_id=empresa_id,
                level="CATEGORY",
                code=sent,
                name=sent,
            )
            db.add(taxonomia)
            db.flush()
            recursos[clave_empresa]["taxonomy"] = str(taxonomia.id)
            centinelas[clave_empresa].add(sent)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            perfil = ProfileVersion(
                company_id=empresa_id,
                profile_type="INVENTORY",
                code=sent,
                name=sent,
            )
            db.add(perfil)
            db.flush()
            recursos[clave_empresa]["profile"] = str(perfil.id)
            centinelas[clave_empresa].add(sent)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            lote = InventoryLot(
                company_id=empresa_id,
                product_id=item_id,
                lot_number=sent,
            )
            db.add(lote)
            db.flush()
            recursos[clave_empresa]["lot"] = str(lote.id)
            centinelas[clave_empresa].add(sent)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            serial = ProductSerial(
                company_id=empresa_id,
                product_id=item_id,
                serial=sent,
            )
            db.add(serial)
            db.flush()
            recursos[clave_empresa]["serial"] = str(serial.id)
            centinelas[clave_empresa].add(sent)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            tipo_movimiento = MovementType(
                company_id=empresa_id,
                direction="IN",
                code=sent,
                name=sent,
            )
            db.add(tipo_movimiento)
            db.flush()
            recursos[clave_empresa]["movement_type"] = str(tipo_movimiento.id)
            centinelas[clave_empresa].add(sent)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            almacen = Warehouse(
                company_id=empresa_id,
                code=sent,
                name=sent,
            )
            db.add(almacen)
            db.flush()
            almacen_id = str(almacen.id)
            recursos[clave_empresa]["warehouse"] = almacen_id
            centinelas[clave_empresa].add(sent)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            categoria_doc = DocumentCategory(
                company_id=empresa_id,
                code=sent,
                name=sent,
            )
            db.add(categoria_doc)
            db.flush()
            categoria_doc_id = str(categoria_doc.id)
            recursos[clave_empresa]["doc_category"] = categoria_doc_id
            centinelas[clave_empresa].add(sent)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            tipo_doc = DocumentType(
                company_id=empresa_id,
                code=sent,
                name=sent,
                category_id=categoria_doc_id,
            )
            db.add(tipo_doc)
            db.flush()
            recursos[clave_empresa]["doc_type"] = str(tipo_doc.id)
            centinelas[clave_empresa].add(sent)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            orden = PurchaseOrder(
                company_id=empresa_id,
                supplier_id=party_id,
                code=sent,
            )
            db.add(orden)
            db.flush()
            orden_id = str(orden.id)
            recursos[clave_empresa]["purchase_order"] = orden_id
            centinelas[clave_empresa].add(sent)

            linea_orden = PurchaseOrderLine(
                order_id=orden_id,
                product_id=item_id,
                quantity_ordered=1,
                unit_price=1,
            )
            db.add(linea_orden)
            db.flush()
            linea_orden_id = str(linea_orden.id)
            recursos[clave_empresa]["po_line"] = linea_orden_id

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            recepcion = GoodsReceipt(
                company_id=empresa_id,
                order_id=orden_id,
                warehouse_id=almacen_id,
                code=sent,
            )
            db.add(recepcion)
            db.flush()
            recepcion_id = str(recepcion.id)
            recursos[clave_empresa]["receipt"] = recepcion_id
            centinelas[clave_empresa].add(sent)

            linea_recepcion = GoodsReceiptLine(
                receipt_id=recepcion_id,
                order_line_id=linea_orden_id,
                product_id=item_id,
                quantity_received=1,
            )
            db.add(linea_recepcion)
            db.flush()
            recursos[clave_empresa]["receipt_line"] = str(linea_recepcion.id)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            incidencia = ReceiptIncident(
                company_id=empresa_id,
                receipt_id=recepcion_id,
                incident_type="DIFERENCIA_DOCUMENTAL",
                code=sent,
            )
            db.add(incidencia)
            db.flush()
            recursos[clave_empresa]["incident"] = str(incidencia.id)
            centinelas[clave_empresa].add(sent)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            banco = FinancialBank(
                company_id=empresa_id,
                code=sent,
                name=sent,
            )
            db.add(banco)
            db.flush()
            banco_id = str(banco.id)
            centinelas[clave_empresa].add(sent)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            cuenta = FinancialAccount(
                company_id=empresa_id,
                bank_id=banco_id,
                code=sent,
                name=sent,
            )
            db.add(cuenta)
            db.flush()
            cuenta_id = str(cuenta.id)
            recursos[clave_empresa]["bank_account"] = cuenta_id
            centinelas[clave_empresa].add(sent)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            transaccion = BankTransaction(
                company_id=empresa_id,
                account_id=cuenta_id,
                amount=1,
                reference=sent,
            )
            db.add(transaccion)
            db.flush()
            recursos[clave_empresa]["bank_transaction"] = str(transaccion.id)
            centinelas[clave_empresa].add(sent)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            metodo_pago = PaymentMethod(
                company_id=empresa_id,
                code=sent,
                name=sent,
            )
            db.add(metodo_pago)
            db.flush()
            metodo_pago_id = str(metodo_pago.id)
            centinelas[clave_empresa].add(sent)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            instrumento = TreasuryInstrument(
                company_id=empresa_id,
                method_id=metodo_pago_id,
                code=sent,
                name=sent,
            )
            db.add(instrumento)
            db.flush()
            recursos[clave_empresa]["instrument"] = str(instrumento.id)
            centinelas[clave_empresa].add(sent)

            pago = Payment(
                company_id=empresa_id,
                party_id=party_id,
                amount=1,
            )
            db.add(pago)
            db.flush()
            recursos[clave_empresa]["payment"] = str(pago.id)

            sent = "ZZ" + clave_empresa + secrets.token_hex(4).upper()
            caja = Cashbox(
                company_id=empresa_id,
                code=sent,
                name=sent,
            )
            db.add(caja)
            db.flush()
            recursos[clave_empresa]["cashbox"] = str(caja.id)
            centinelas[clave_empresa].add(sent)

            sucursal = db.execute(
                select(Branch).where(
                    Branch.company_id == empresa_id,
                    Branch.code == f"S{clave_empresa}",
                )
            ).scalars().one()
            recursos[clave_empresa]["branch"] = str(sucursal.id)

        db.commit()

        from app.main import create_app

        app = create_app()

        def _db():
            d = factory()
            try:
                yield d
            finally:
                d.close()

        app.dependency_overrides[get_db] = _db
        client = TestClient(app)

        tokens: dict[str, str] = {}
        for username, actor in actores.items():
            tenant_code = actor.tenant
            respuesta = login_completo(
                client,
                "/api/v1/auth/login",
                json={"tenant_code": tenant_code, "username": username, "password": CLAVE},
            )
            assert respuesta.status_code == 200, f"login {username}: {respuesta.status_code} {respuesta.text}"
            tokens[username] = respuesta.json()["access_token"]

        return MundoHostil(
            client=client,
            factory=factory,
            tenants={"TA": tenant_a_id, "TB": tenant_b_id},
            empresas=dict_empresas,
            tenant_de_empresa=tenant_de_empresa,
            actores=actores,
            recursos=recursos,
            centinelas=centinelas,
            _tokens=tokens,
        )
    finally:
        db.close()
