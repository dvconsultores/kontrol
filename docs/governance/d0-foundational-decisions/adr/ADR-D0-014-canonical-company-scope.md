# ADR-D0-014 — Alcance canónico tenant / empresa / sucursal

| Campo | Valor |
|---|---|
| ID | D0-14 |
| Estado | **PROPUESTO** — pendiente del Gate documental |
| Fecha | 2026-08-31 |
| Origen | `GATE-MULTICOMPANY-SCOPE.md` · `REM-046-001.md` |
| Specs afectadas | **ARCH-MC-001** (propietaria) · todas las de negocio |

## Problema

107 tablas tienen una columna `company_id`. Solo 17 tienen FK a `companies`. Las
otras 90 guardan el `tenant_id`. Cien puntos del código escriben
`company_id = actor.tenant_id` y setenta y cinco leen comparándolo con el tenant.

El sistema permite crear una segunda empresa aunque el plan lo prohíba, y a
partir de ahí las dos comparten toda la información de negocio: terceros,
compras, existencias, ventas, bancos y —lo más grave— series fiscales, números de
control del SENIAT y libros.

Cada empresa es un RIF distinto. Esto no produce un modelo confuso: produce
libros inválidos.

## Decisión

### 1. Significado, sin excepciones

`tenant_id` → `Tenant.id`. `company_id` → `Company.id`. `branch_id` →
`Branch.id`. **Ninguna columna nombra una entidad y almacena otra.**

### 2. Toda entidad declara su alcance

`GLOBAL` · `INSTALLATION` · `TENANT` · `COMPANY` · `BRANCH` · `DERIVED`.
No existe `UNKNOWN`. Las 166 tablas quedan clasificadas: 133 de empresa, 14 del
tenant, 16 de instalación, 3 globales.

### 3. Derivar es válido; adivinar no

Una entidad `DERIVED` alcanza su empresa por una ruta **obligatoria,
determinista y persistente**. Una FK anulable no es una ruta. Medido: las 36
derivadas cumplen la condición.

### 4. El objetivo no es una columna en cada tabla

Es que 133 entidades determinen su empresa sin ambigüedad. Duplicar `company_id`
en una línea cuya cabecera ya lo tiene crea la posibilidad de que difieran.

### 5. El contexto viaja por cabecera

`X-Kontrol-Company` por petición, **validada en el servidor**. El cliente
propone; el servidor decide. Elegida sobre sesión, token y ruta porque es la
única que permite dos pestañas en empresas distintas sin tocar la rotación de
sesión ya remediada.

### 6. La licencia limita el uso, no el esquema

El modelo es multiempresa siempre. El plan limita cuántas empresas se crean y
operan, y **el backend lo impone**.

### 7. El histórico no se inventa

Clasificación `MC-A`..`MC-E`. El determinismo se demuestra sobre el intervalo en
que la fila pudo crearse, no sobre el número de empresas de hoy. Un crítico no
reconstruible **detiene** la migración.

### 8. Regla para lo que venga

> Ninguna entidad persistente nueva introduce `tenant_id`, `company_id` o
> `branch_id` sin declarar su alcance, su autoridad y su ruta.
>
> Ningún servicio asigna `actor.tenant_id` a una propiedad llamada `company_id`.

Ambas se comprueban con pruebas de arquitectura que fallan en construcción.

## Alternativas

**A. Declarar el alcance en `ResourceKind` de la Spec 046.** Quince líneas.
Descartada: haría funcionar el registro documental sobre una arquitectura que
sigue sin distinguir empresas. Los libros seguirían mezclados.

**B. Imponer una empresa por tenant y renombrar la columna.** Más barata y
también correcta. Descartada por **decisión de producto**: KONTROL es
multiempresa por tenant.

**C. Normalización canónica.** ← **ELEGIDA**

## Consecuencias

| Dimensión | Impacto |
|---|---|
| Base de datos | 133 entidades con empresa determinable; FK reales; 13 únicos revisados |
| Backend | `CompanyContext`; 100 escrituras y 75 lecturas reescritas; 276 operaciones acotadas |
| Frontend | Selector, cabecera, invalidación al cambiar |
| Migración | Por olas, expandir/contraer, con informe previo y aborto |
| Specs cerradas | 008 sin cambio · 045 regresión · 011 adaptación de contrato · 046 reconvergencia |
| Spec 012 | **Bloqueada** hasta que esto cierre |

## Urgencia

Mientras cada tenant tenga una sola empresa, el backfill es determinista. En
cuanto uno tenga dos y opere con ambas, deja de serlo **para siempre**. No es que
el dato se pierda: nunca se captura.

## Estado

**PROPUESTO.** Requiere aprobación en el Gate documental de ARCH-MC-001.
