# REMEDIACIÓN DE SEGURIDAD — SPEC 045

`SECURITY REMEDIATION UNDER ARCH-MC-001` · No se ejecuta `/speckit.converge 045`.

## 1. Defecto

`P0 SECURITY — CLIENT_OVERRIDES_COMPANY_CONTEXT`

Operando en la empresa A y declarando la empresa B en el cuerpo, la política
quedaba guardada en B. **El cliente elegía en qué empresa escribir.**

## 2. Reproducción, antes del arreglo

```
POST /approvals/policies      contexto: empresa A
{"company_id": <empresa B>, "code": "POL-CRUZADA", ...}
→ 201  ·  approval_policies.company_id = <empresa B>
```

Verificado consultando PostgreSQL, no la respuesta de la API.

## 3. Dos cosas peores que lo reportado

La reproducción destapó dos hechos que el informe original no recogía.

**El cruce era también entre tenants.** Un usuario del tenant T2 declaró una
empresa de T1 y la política se creó allí. No era una fuga entre empresas
hermanas: era escritura desde fuera de la instalación del cliente.

**`GET /policies` no filtraba por empresa en absoluto.** El parámetro
`company_id` era opcional; sin él, la ruta devolvía las políticas de todas las
empresas de todos los tenants. El aislamiento dependía de que el cliente
pidiera bien.

## 4. Causa

045 se escribió cuando cada tenant tenía una sola empresa. En ese mundo, tomar
la empresa del cuerpo y tomarla del token daban el mismo resultado siempre, así
que la diferencia no era observable. Dejó de serlo con dos empresas.

No hay políticas legítimamente globales o de tenant: las ocho entidades del
módulo declaran alcance `COMPANY`. Por eso la corrección no necesita distinguir
casos.

## 5. Corrección

Un único punto decide la empresa:

```python
def _empresa(ctx: CompanyContext, declarada: str | None) -> str:
    if declarada is not None and declarada != ctx.company_id:
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    return ctx.company_id
```

`company_id` se conserva en los cuerpos por compatibilidad, pero pasa a ser
opcional y **contradecir el contexto es un error, no una preferencia**. Los
listados se acotan por el contexto en lugar de por un parámetro del cliente, y
los cargadores por id —política, solicitud, delegación— responden 404 ante una
entidad de otra empresa: confirmar que existe ya sería enumerar configuración
ajena.

Catorce rutas reciben ahora el contexto validado.

## 6. Verificación

| Caso | Resultado |
|---|---|
| Contexto A + cuerpo A | **PASS** |
| Contexto A + cuerpo B | **BLOCKED** (404) |
| Contexto B sin empresa en el cuerpo | Se guarda en B |
| Listados de A y B | Sin intersección |
| Detalle y activación de una política ajena | **BLOCKED** |
| Escritura desde T2 hacia T1 | **BLOCKED** |

Incluye la prueba positiva —la política legítima se crea y queda en su
empresa—, sin la cual el bloqueo podría deberse a que nada funciona.

## 7. Alcance

No se rehace 045. No se toca el motor de aprobaciones, ni la segregación de
funciones, ni los flujos. Solo la propiedad de la empresa y sus pruebas.

**Regresión de 045: sin fallos.**

Una prueba existente cambió: `test_inbox_isolated_by_company` pedía la bandeja
de «otra-empresa» por parámetro y comprobaba que viniera vacía. Eso demostraba
poco —el aislamiento dependía de que el cliente pidiera bien—. Ahora comprueba
que declarar otra empresa no cambie la respuesta y que una empresa inventada en
la cabecera se rechace, en vez de devolver una bandeja vacía y tranquilizadora.
Es una aserción más estricta, no más laxa.

## 8. Estado

**`CLOSED`** en cuanto a la vulnerabilidad.

Spec 045 permanece `COMPLETE_100` con la remediación integrada.
