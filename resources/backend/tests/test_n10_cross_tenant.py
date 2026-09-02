"""El tenant como frontera, no como suposición (ARCH-MC-001, N10).

ARCH-MC-001 se ocupó de que la empresa fuera una frontera real. N10 comprobó la
de arriba, y en identidad no lo era: tres rutas de `users` y `roles` operaban
sobre la instalación entera.

No llevan cabecera de empresa y hacen bien en no llevarla —son de tenant—, pero
«de tenant» tiene que significar algo en la consulta. En estas no significaba
nada: ni un filtro, ni una comprobación.
"""

from __future__ import annotations

pytest_plugins = ("tests.conftest_multicompany",)

BLOQUEO = (403, 404)


def _usuarios(mundo, usuario, tenant):
    r = mundo.client.get("/api/v1/users",
                         headers={"Authorization": f"Bearer {mundo.token(usuario, tenant)}"})
    assert r.status_code == 200, r.text
    return r.json()


def test_la_lista_de_usuarios_no_cruza_el_tenant(mundo):
    """`select(User)` sin `where`: el administrador de T1 veía a los de T2.

    Devuelve nombre, correo, último acceso y roles. No es un listado incompleto:
    es el censo de la instalación entregado a quien solo administra su tenant.
    """
    nombres_t1 = {u["username"] for u in _usuarios(mundo, "ua", "T1")}
    assert "uc" not in nombres_t1, (
        f"T1 vio al usuario de T2 en su listado: {sorted(nombres_t1)}")

    nombres_t2 = {u["username"] for u in _usuarios(mundo, "uc", "T2")}
    assert "ua" not in nombres_t2 and "ub" not in nombres_t2, (
        f"T2 vio usuarios de T1: {sorted(nombres_t2)}")


def _id_de(mundo, usuario, tenant, buscado):
    for u in _usuarios(mundo, usuario, tenant):
        if u["username"] == buscado:
            return u["id"]
    return None


def test_no_se_asigna_un_rol_a_un_usuario_de_otro_tenant(mundo):
    """`get_user` busca por id y no mira el tenant de quien pregunta."""
    uc_id = _id_de(mundo, "uc", "T2", "uc")
    assert uc_id, "no se pudo localizar al usuario de T2 desde su propio tenant"

    roles = mundo.client.get("/api/v1/roles",
                             headers={"Authorization": f"Bearer {mundo.token('ua', 'T1')}"})
    assert roles.status_code == 200, roles.text
    rol = roles.json()["items"][0]["id"]

    r = mundo.client.post(
        f"/api/v1/users/{uc_id}/roles",
        headers={"Authorization": f"Bearer {mundo.token('ua', 'T1')}"},
        json={"role_id": rol})
    assert r.status_code in BLOQUEO, (
        f"T1 asignó un rol a un usuario de T2: {r.status_code} {r.text}")


def test_no_se_retira_un_rol_a_un_usuario_de_otro_tenant(mundo):
    """La retirada tenía el mismo agujero que la asignación."""
    uc_id = _id_de(mundo, "uc", "T2", "uc")
    assert uc_id
    roles_de_uc = _usuarios(mundo, "uc", "T2")
    suyos = next(u["roles"] for u in roles_de_uc if u["id"] == uc_id)
    assert suyos, "el usuario de T2 no tenía ningún rol que retirar"

    r = mundo.client.delete(
        f"/api/v1/users/{uc_id}/roles/{suyos[0]['id']}",
        headers={"Authorization": f"Bearer {mundo.token('ua', 'T1')}"})
    assert r.status_code in BLOQUEO, (
        f"T1 retiró un rol a un usuario de T2: {r.status_code} {r.text}")


def test_una_asignacion_no_apunta_a_una_empresa_de_otro_tenant(mundo):
    """`company_id` llegaba del cuerpo y nadie comprobaba de quién era."""
    ua_id = _id_de(mundo, "ua", "T1", "ua")
    assert ua_id
    roles = mundo.client.get("/api/v1/roles",
                             headers={"Authorization": f"Bearer {mundo.token('ua', 'T1')}"})
    rol = roles.json()["items"][0]["id"]
    r = mundo.client.post(
        f"/api/v1/users/{ua_id}/roles",
        headers={"Authorization": f"Bearer {mundo.token('ua', 'T1')}"},
        json={"role_id": rol, "company_id": mundo.company_c})
    assert r.status_code in BLOQUEO, (
        f"T1 asignó un rol acotado a la empresa de T2: {r.status_code} {r.text}")
