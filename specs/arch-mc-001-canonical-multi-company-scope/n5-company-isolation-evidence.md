# N5 — EVIDENCIA DE AISLAMIENTO ENTRE EMPRESAS

Fecha: 2026-08-31 · PostgreSQL **18.6** en UTC

## 1. Por qué hacía falta un fixture nuevo

Probar el aislamiento con una sola empresa no prueba nada: si el sistema solo
conoce una, no puede confundirla con otra. Hasta ahora las suites demostraban
aislamiento **entre tenants**, que ya funcionaba. Lo que faltaba era el caso que
el Gate multiempresa destapó: dos empresas **del mismo tenant**.

```
T1 ─ Company A ─ Branch A1 ─ Warehouse A1
   └ Company B ─ Branch B1 ─ Warehouse B1
T2 ─ Company C
```

Usuarios: `UA` (solo A) · `UB` (solo B) · `UAB` (A+B) · `UC` (T2).

## 2. Las dos cosas que se comprueban, y por qué son distintas

| Fallo | Pregunta |
|---|---|
| **Fuga** | ¿Puede A leer lo de B? |
| **Mezcla** | ¿Sabe la base de quién es la fila? |

Que la API filtre bien no basta si el dato persistido sigue guardando el tenant:
sería un filtro correcto sobre un dato indistinguible. Por eso hay una prueba que
consulta **PostgreSQL directamente** y comprueba que `parties.company_id` guarda
la empresa y **no** el tenant.

## 3. Resultado

| Comprobación | Resultado |
|---|---|
| Empresa ajena para quien no accede | **404**, sin confirmar que existe |
| Empresa de otro tenant | **404** |
| Varias empresas sin cabecera | **400 `COMPANY_CONTEXT_REQUIRED`** — no se adivina |
| Una sola empresa sin cabecera | Se resuelve sola |
| Cabecera inventada | **404** |
| El dato guarda la empresa, no el tenant | **verificado en la base** |
| Lista de A sin filas de B, y viceversa | **0 intersección** |
| Detalle ajeno | **404** |
| Mutación ajena | **bloqueada** |
| `UAB` alternando contexto | Ve A o B, nunca las dos |
| Empresa en el cuerpo contradiciendo el contexto | El servidor decide |

**13/13.**

## 4. Un defecto que N2 no podía ver

`deactivate_party` desactivaba un tercero **de cualquier empresa**: devolvía 200
al operar desde A sobre una fila de B.

No es que usara el tenant como empresa. Es que **no acotaba en absoluto**. El
barrido de N2 buscaba el patrón `company_id = tenant_id` y esta ruta no lo tenía,
porque no tenía ninguno.

De ahí sale una clase de defecto que N5 tiene que buscar aparte: **la ruta que
nunca comprobó nada**. Un barrido específico encontró 13 candidatas; una era real
en un dominio ya normalizado, y las demás pertenecen a Specs cerradas (§5).

## 5. Dos hallazgos en Specs cerradas — comprobados, no corregidos

Ambos se verificaron **por comportamiento**, no leyendo el código, y quedan
fijados con una prueba que fallará el día que se corrijan.

### 046 · Documental

`_get_document` admite **cualquier empresa del tenant**, no la del contexto.
Comprobado: `UA` lee un documento de la empresa B y recibe **200**.

### 045 · Aprobaciones

Toma la empresa del **cuerpo de la petición** sin contrastarla con el contexto.
Comprobado: operando en A se crea una política que queda guardada en B.

En ambos casos era coherente cuando se escribieron —tenant y empresa eran lo
mismo— y deja de serlo con dos empresas.

**Su corrección pertenece a N9**, junto con el resto de `REM-046-001`. Tocarlas
aquí reabriría dos Specs cerradas sin autorización, y las pruebas que las fijan
existen precisamente para que no se pierdan entre las que sí quedaron
normalizadas.
