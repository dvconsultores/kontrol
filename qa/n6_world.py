"""Mundo multiempresa de N6 (ARCH-MC-001 §7), definido una sola vez.

Las suites `n6-multicompany.spec.ts` y `n6-a11y-responsive.spec.ts` necesitan
dos empresas del mismo tenant, un tenant ajeno y cuatro usuarios con distinto
alcance. Ese mundo se describía dentro de `qa/n6-multicompany-bootstrap.py`, que
lo escribe en **su propia** base SQLite y la borra al empezar: contra la base
sobre la que corre el E2E ese guion no puede ejecutarse, así que las 25 pruebas
no encontraban a sus usuarios y no abrían sesión.

Aquí queda la definición, sin decidir en qué base se aplica: recibe la sesión y
escribe en la que sea. Las dos vías —la pila SQLite autónoma y la siembra sobre
la base del E2E— la comparten, de modo que no pueden divergir.

Todo es **buscar y, si falta, crear**. Nada se borra, nada se reescribe y
ejecutarlo N veces deja la base igual que ejecutarlo una: la siembra corre antes
de cada suite y una base de QA acumula el trabajo de muchas ejecuciones.
"""

from __future__ import annotations

from typing import Any

import alcance_de_usuario
from sqlalchemy import select
from sqlalchemy.orm import Session

#: Contraseña de QA. No es una credencial real ni abre nada fuera de este mundo.
PASS = "Kontrol2026Segura!"

#: Tenant de QA, el que siembra `qa/pg-e2e-seed.py`.
TENANT_1 = "DEMO"

#: Segunda empresa del tenant de QA.
#:
#: **Es la misma fila que siembra `qa/spec047-e2e-seed.py`**: mismo tenant y
#: mismo código. Antes cada guion la describía a su manera —distinto nombre,
#: distinto RIF— y cuál de las dos quedaba dependía de quién corriera último.
#: La definición vive aquí y los dos la piden, que es la única forma de que no
#: puedan discrepar. El nombre conserva «SEGUNDA» porque las pruebas de N6
#: reconocen la empresa activa por esa palabra.
EMPRESA_B: dict[str, Any] = {
    "code": "D2",
    "legal_name": "SEGUNDA EMPRESA E2E 047 CA",
    "rif": "J-40470470-7",
}

#: Tenant ajeno y su empresa. Existen para comprobar que la frontera de arriba
#: tampoco se cruza (`n6-multicompany.spec.ts:271`).
TENANT_2 = {"code": "DEMO2", "name": "Otro Cliente"}
EMPRESA_C: dict[str, Any] = {
    "code": "E1",
    "legal_name": "TERCERA EMPRESA CA",
    "rif": "J-30303030-3",
}

#: Un tercero identificable en cada empresa. Sin datos distintos, dos listas
#: vacías tampoco se contaminan y el aislamiento quedaría «demostrado» por no
#: haber nada que ver.
TERCERO_A = "SOLO-DE-A"
TERCERO_B = "SOLO-DE-B"


def _tenant(db: Session, code: str):
    from app.modules.organization.models import Tenant

    t = db.execute(select(Tenant).where(Tenant.code == code)).scalars().first()
    if t is None:
        raise RuntimeError(
            f"no existe el tenant {code!r}: ejecute antes qa/pg-e2e-seed.py sobre esta misma base")
    return t


def empresa(db: Session, tenant, *, code: str, legal_name: str, rif: str):
    """La empresa `code` de ese tenant; se crea si falta, se respeta si está.

    Se busca por `(tenant, code)` porque es la identidad lógica de una empresa
    dentro de su tenant. Una empresa ya existente **no se reescribe**: si una
    base de QA lleva datos colgando de ella, cambiarle el nombre o el RIF sería
    reinterpretar lo que ya está escrito.
    """
    from app.modules.organization.models import Company

    c = db.execute(select(Company).where(
        Company.tenant_id == str(tenant.id), Company.code == code)).scalars().first()
    if c is not None:
        return c
    c = Company(tenant_id=str(tenant.id), code=code, legal_name=legal_name, rif=rif,
                legal_type="JURIDICA", functional_currency="VED", status="ACTIVE")
    db.add(c)
    db.flush()
    return c


def _tercero(db: Session, company, marca: str) -> None:
    from app.modules.master_data.models import Party

    ya = db.execute(select(Party).where(
        Party.company_id == str(company.id), Party.code == marca)).scalars().first()
    if ya is not None:
        return
    db.add(Party(company_id=str(company.id), code=marca, name=f"Tercero {marca}",
                 legal_name=f"Tercero {marca}", person_type="JURIDICA",
                 roles=["CLIENTE"], status="ACTIVE"))
    db.flush()


def _usuario(db: Session, tenant, username: str, empresas: list[str]):
    """Usuario de QA con **alcance declarado**.

    El alcance es el punto del ejercicio, no un adorno: `ua` opera en una
    empresa, `ub` en la otra y `uab` en las dos, y eso es lo que las pruebas
    comprueban. Declararlo tiene además un efecto que conviene decir en voz
    alta: sin ninguna fila en `user_scopes` el servidor admite **todas** las
    empresas del tenant (`app/core/company_context.py:82`), así que el conjunto
    de empresas del usuario dependería de cuántas haya en la base en ese
    momento, y la prueba pasaría o fallaría según lo que hubiera sembrado otro.

    Quien lo escribe es `qa/alcance_de_usuario.py`, que es la única autoridad
    del repositorio para conceder acceso a una empresa.

    `must_change_password` va en falso porque estas cuentas no son de nadie:
    nunca habrá quien cambie esa contraseña, y dejar sembrado un cambio
    pendiente que no ocurrirá describe mal el mundo. Conviene decir lo que se
    midió: ponerlo en verdadero **no** tumba la suite —las 25 pruebas siguen
    pasando—, así que esto es exactitud del dato sembrado, no un apaño para que
    algo pase.
    """
    from app.modules.identity_access import service as identity_service
    from app.modules.identity_access.models import User, UserRole
    from app.modules.setup.api import _bootstrap_roles

    u = db.execute(select(User).where(
        User.tenant_id == str(tenant.id), User.username == username)).scalars().first()
    if u is None:
        u = identity_service.create_user(
            db, tenant_id=str(tenant.id), username=username, email=f"{username}@qa.test",
            password=PASS, must_change_password=False, created_by=None)
        db.flush()

    rol = _bootstrap_roles(db, str(tenant.id), str(u.id))
    tiene_rol = db.execute(select(UserRole).where(
        UserRole.user_id == str(u.id), UserRole.role_id == str(rol.id))).scalars().first()
    if tiene_rol is None:
        db.add(UserRole(user_id=str(u.id), role_id=str(rol.id), company_id=None))

    db.flush()
    alcance_de_usuario.declarar(db, tenant_code=tenant.code, username=username, empresas=empresas)
    return u


def sembrar(db: Session, *, tenant_code: str = TENANT_1) -> dict[str, str]:
    """Deja el mundo de N6 en la base de `db` y devuelve sus identificadores.

    ```
      T1 (DEMO) ─ Empresa A (D1) ─ tercero SOLO-DE-A
                └ Empresa B (D2) ─ tercero SOLO-DE-B
      T2 (DEMO2) ─ Empresa C (E1)
      ua → A · ub → B · uab → A+B · uc → C
    ```

    No se siembran sucursales ni almacenes: ninguna de las 25 pruebas de N6 los
    ejercita, y añadir estructura que nadie mira a una base compartida solo
    puede estorbar a las suites que sí cuentan almacenes.
    """
    from app.modules.organization.models import Company, Installation, Tenant

    t1 = _tenant(db, tenant_code)
    ca = db.execute(select(Company).where(Company.tenant_id == str(t1.id))
                    .order_by(Company.created_at)).scalars().first()
    if ca is None:
        raise RuntimeError(
            f"el tenant {tenant_code!r} no tiene ninguna empresa: ejecute antes qa/pg-e2e-seed.py")
    cb = empresa(db, t1, **EMPRESA_B)

    t2 = db.execute(select(Tenant).where(Tenant.code == TENANT_2["code"])).scalars().first()
    if t2 is None:
        inst = db.execute(select(Installation).limit(1)).scalars().one()
        t2 = Tenant(installation_id=str(inst.id), code=TENANT_2["code"], name=TENANT_2["name"],
                    plan="MONO_COMPANY", status="ACTIVE")
        db.add(t2)
        db.flush()
    cc = empresa(db, t2, **EMPRESA_C)

    _tercero(db, ca, TERCERO_A)
    _tercero(db, cb, TERCERO_B)

    _usuario(db, t1, "ua", [str(ca.id)])
    _usuario(db, t1, "ub", [str(cb.id)])
    _usuario(db, t1, "uab", [str(ca.id), str(cb.id)])
    _usuario(db, t2, "uc", [str(cc.id)])

    db.commit()
    # Los nombres viajan con los identificadores por el mismo motivo que ellos:
    # la empresa A es la que ya hubiera en el tenant, y se llama distinto según
    # quién sembró la base —«Demo C.A.» en la del E2E, otra cosa en la pila
    # SQLite—. Una prueba que escriba ese nombre a mano comprueba qué guion
    # corrió, no qué empresa está activa.
    return {"empresa_a": str(ca.id), "empresa_b": str(cb.id), "empresa_c": str(cc.id),
            "tenant_1": str(t1.id), "tenant_2": str(t2.id),
            "nombre_a": ca.legal_name, "nombre_b": cb.legal_name, "nombre_c": cc.legal_name,
            "tercero_a": TERCERO_A, "tercero_b": TERCERO_B}
