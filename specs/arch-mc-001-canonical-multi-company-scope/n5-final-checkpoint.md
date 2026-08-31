# N5 — CHECKPOINT DE NORMALIZACIÓN DE DOMINIOS

Fecha: 2026-08-31 · PostgreSQL **18.6** en UTC · ClamAV 1.4.3

## 1. Qué se hizo aquí

N2 ya había convertido 234 puntos de `actor.tenant_id` a `ctx.company_id`. Lo que
faltaba —y es lo que N5 aporta— es **demostrarlo con dos empresas del mismo
tenant**, que es el único escenario donde el defecto se manifiesta.

Hasta ahora todas las suites probaban aislamiento **entre tenants**, que ya
funcionaba. Con una sola empresa por tenant, un sistema que confunde tenant con
empresa pasa todas las pruebas.

## 2. El fixture que faltaba

```
T1 ─ Company A ─ Branch A1 ─ Warehouse A1
   └ Company B ─ Branch B1 ─ Warehouse B1
T2 ─ Company C
```

`UA` (solo A) · `UB` (solo B) · `UAB` (A+B) · `UC` (T2).

## 3. Dos defectos reales encontrados

### 3.1 El rol global concedía acceso a todas las empresas

`accessible_company_ids` mezclaba dos cosas distintas: `UserScope`, que dice **en
qué empresas puede operar** un usuario, y `UserRole.company_id`, que dice **dónde
vale un rol**. Un rol con `company_id` nulo significa «este rol sirve en
cualquier empresa donde el usuario opere», no «el usuario opera en todas».

Consecuencia: cualquiera con un rol global veía las dos empresas. Era el mismo
defecto que esta remediación corrige en los datos, trasladado a la autorización.

Corregido: `UserScope` es la autoridad de acceso. Sin ningún alcance declarado se
admiten todas las del tenant, que es el caso del administrador que instala.

### 3.2 Una ruta que no acotaba en absoluto

`deactivate_party` desactivaba un tercero **de cualquier empresa**: 200 al operar
desde A sobre una fila de B.

N2 no pudo verlo. Buscaba el patrón `company_id = tenant_id` y esta ruta no lo
tenía, porque no tenía ninguno. **Nunca comprobó nada.**

De ahí sale una clase de defecto propia, que N5 buscó aparte: «rutas que cargan
una entidad de empresa sin comprobar la empresa». El barrido encontró 13; una
era real en dominio normalizado, y las otras 12 están en Specs cerradas.

## 4. Dos hallazgos diferidos a N9 — comprobados, no corregidos

Verificados **por comportamiento**, no leyendo código, y fijados con pruebas que
fallarán el día que se corrijan.

| Spec | Hallazgo | Evidencia |
|---|---|---|
| **046** | `_get_document` admite cualquier empresa del tenant | `UA` lee un documento de B y recibe **200** |
| **045** | Toma la empresa del cuerpo sin contrastar el contexto | Operando en A, la política se guarda en B |

Era coherente cuando se escribieron: tenant y empresa eran lo mismo. Deja de
serlo con dos empresas.

Su corrección pertenece a **N9**. Tocarlas aquí reabriría dos Specs `COMPLETE_100`
sin autorización.

## 5. Lo que se comprueba, y por qué son dos cosas

| Fallo | Pregunta | Resultado |
|---|---|---|
| **Fuga** | ¿Puede A leer lo de B? | **0** |
| **Mezcla** | ¿Sabe la base de quién es la fila? | **0** |

La segunda no se puede sustituir por la primera. Que la API filtre bien no
significa nada si el dato persistido guarda el tenant: sería un filtro correcto
sobre un dato indistinguible. Por eso hay una prueba que consulta PostgreSQL y
verifica que `parties.company_id` guarda la empresa y **no** el tenant.

## 6. Un fixture que codificaba el supuesto viejo

`test_audit_integration` creaba una segunda empresa a mitad de flujo y seguía
operando sin decir en cuál. El rechazo con `COMPANY_CONTEXT_REQUIRED` es
**correcto**: en cuanto hay dos, «¿en cuál?» es una pregunta real.

Corregido declarando la empresa. No es relajar la prueba: es que la prueba
reconozca lo que ella misma acababa de crear.

## 7. Estado por dominio

Ver `n5-domain-normalization-matrix.md`. Resumen:

| Estado | Dominios |
|---|---|
| `FUNCTIONALLY_NORMALIZED` | master_data, organization |
| `NORMALIZED_PENDING_AB_PROOF` | purchasing, inventory, sales, treasury, fiscal, regulatory, reporting |
| `DEFERRED_TO_N9` | approvals, documents |

**Sobre la honestidad de esta tabla:** los siete `PENDING_AB_PROOF` escriben y
leen la empresa real —comparten el mismo `CompanyContext` y pasaron por los 234
puntos de N2— pero no tienen todavía una prueba A/B **de su dominio**. Marcarlos
como probados sería exactamente el error que este proyecto viene corrigiendo:
afirmar por construcción lo que no se ha verificado.

Es la misma lección de `REM-046-001`, donde 19 tipos estaban registrados y solo
uno probado.

## 8. Qué falta para `N5 COMPLETE`

| Pendiente | Alcance |
|---|---|
| Prueba A/B por dominio: compras, inventario, ventas, CxC, CxP, tesorería, fiscal, regulatorio | 7 dominios |
| Fiscal A/B: configuración, series, rangos de control, documentos, libros, retenciones | P0 |
| Bloqueo de operaciones entre empresas: aplicación de pagos, transferencias de stock | — |
| Eventos y auditoría con la empresa real, verificado en base | — |

No es trabajo de diseño: el camino está y el fixture también. Es escribir las
pruebas por dominio y corregir lo que destapen, como destaparon las dos de §3.
