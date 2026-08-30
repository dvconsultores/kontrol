# CRITERIOS DE ACEPTACIÓN — ARCH-MC-001

Fixture obligatorio en todos: tenant `T1` con empresas **A** y **B**; tenant `T2`
con empresa **C**. Usuarios: `UA` (solo A), `UB` (solo B), `UAB` (A+B), `UC` (T2).

## Semántica canónica

| Id | Criterio |
|---|---|
| AC-MC-01 | Toda columna `company_id` tiene FK a `companies`; toda `tenant_id`, a `tenants`. Verificado **en PostgreSQL**, no en metadatos del ORM |
| AC-MC-02 | Los 166 modelos declaran alcance; `test_all_persistent_models_have_declared_scope` pasa |
| AC-MC-03 | Ninguna entidad derivada depende de una FK anulable |
| AC-MC-04 | `grep` de `company_id=actor.tenant_id` en entidades de empresa devuelve **0** |

## Contexto de empresa

| Id | Criterio |
|---|---|
| AC-MC-10 | Con cabecera válida, el contexto se resuelve y la operación ocurre en esa empresa |
| AC-MC-11 | `UA` con una sola empresa y sin cabecera: se resuelve sola |
| AC-MC-12 | `UAB` sin cabecera: **400 `COMPANY_CONTEXT_REQUIRED`**. No se adivina |
| AC-MC-13 | `UA` pidiendo la empresa B: **404**, sin confirmar existencia |
| AC-MC-14 | `UC` pidiendo A: **404** |
| AC-MC-15 | Empresa desactivada: **409 `COMPANY_INACTIVE`** |
| AC-MC-16 | `UAB` pierde acceso a B con la sesión viva: la siguiente operación en B da **404** |
| AC-MC-17 | Manipular el valor guardado en el navegador **no** da acceso |
| AC-MC-18 | Dos pestañas en A y B operan sin contaminarse |
| AC-MC-19 | Cerrar sesión limpia contexto, pista y cachés |
| AC-MC-20 | Un trabajo sin contexto explícito **falla**; no toma uno por defecto |

## Autoridad de consulta y escritura

| Id | Criterio |
|---|---|
| AC-MC-30 | Un listado con contexto A **no** contiene filas de B, y viceversa |
| AC-MC-31 | Leer por id un recurso de B con contexto A: **404** |
| AC-MC-32 | Modificar un recurso de B con contexto A: bloqueado |
| AC-MC-33 | Borrar un recurso de B con contexto A: bloqueado |
| AC-MC-34 | Enviar `company_id` de B en el cuerpo con contexto A: **409 `COMPANY_MISMATCH`** |
| AC-MC-35 | `UAB` cambia de A a B: ve solo B, sin restos de A |
| AC-MC-36 | Nunca se permite T1 → T2: el aislamiento previo se mantiene |

## Licencia y acceso

| Id | Criterio |
|---|---|
| AC-MC-40 | Con la licencia limitada a una empresa, crear la segunda: **409 `COMPANY_LIMIT_REACHED`** |
| AC-MC-41 | Con derechos para varias, la segunda se crea y opera de forma independiente |
| AC-MC-42 | Pertenecer al tenant **no** concede acceso a todas sus empresas |
| AC-MC-43 | `ventas:view` en A no habilita ventas de B |
| AC-MC-44 | El alcance por sucursal sigue vigente dentro de la empresa |

## Fiscal — máxima prioridad

| Id | Criterio |
|---|---|
| AC-MC-50 | A y B tienen series de numeración independientes; no colisionan |
| AC-MC-51 | Un rango de números de control de A **no** puede consumirse desde B |
| AC-MC-52 | El libro de ventas de A no contiene documentos de B |
| AC-MC-53 | El libro de compras de A no contiene documentos de B |
| AC-MC-54 | Una retención conserva la empresa agente; no se reconstruye por el contexto actual |
| AC-MC-55 | Una factura reimpresa muestra su empresa emisora, no la activa |

## Dominios

| Id | Criterio |
|---|---|
| AC-MC-60 | Órdenes de compra de A y B separadas; ambas pueden llevar el número 100 |
| AC-MC-61 | Recepción cuya orden es de A y cuyo almacén es de B: **bloqueada** |
| AC-MC-62 | Facturas de proveedor y obligaciones separadas por empresa |
| AC-MC-63 | Un pago de A no se aplica a una factura de B: **409 `CROSS_COMPANY_OPERATION`** |
| AC-MC-64 | Mismo producto, almacenes de A y B: existencias **no** se mezclan |
| AC-MC-65 | Transferencia entre almacenes de A y B: bloqueada como intercompany |
| AC-MC-66 | Pedidos y facturas de venta separados |
| AC-MC-67 | Cuentas bancarias y movimientos separados |
| AC-MC-68 | Permisos y documentos regulatorios pertenecen a la empresa correcta |
| AC-MC-69 | Los costos no se mezclan entre empresas |

## Migración

| Id | Criterio |
|---|---|
| AC-MC-70 | El informe previo se ejecuta **sin escribir** y detalla por tabla y clase |
| AC-MC-71 | MC-A se decide por el intervalo, no por el número de empresas de hoy |
| AC-MC-72 | Una fila MC-C no se rellena automáticamente |
| AC-MC-73 | Un MC-E **detiene** la migración final, sin escrituras destructivas parciales |
| AC-MC-74 | El valor heredado se conserva hasta verificar |
| AC-MC-75 | La resolución manual registra quién, cuándo, evidencia, valor anterior y nuevo |
| AC-MC-76 | Tras migrar: importes, cantidades, bases imponibles y números **idénticos** |
| AC-MC-77 | Base vacía → `alembic upgrade head` sin error |
| AC-MC-78 | Fixture anterior a la normalización migra con su informe |
| AC-MC-79 | Ninguna columna de transición sobrevive a N8 |

## Spec 046

| Id | Criterio |
|---|---|
| AC-MC-80 | `ResourceKind` declara alcance y resolutor **explícitos** |
| AC-MC-81 | Los **19** tipos registrados se prueban: entidad de la empresa activa → vínculo; de otra → 404 |
| AC-MC-82 | Las 4 entradas de `REM-046-001` quedan registradas y probadas |
| AC-MC-83 | `STILL_BLOCKED_BY_046` = **0** para toda entidad existente |
| AC-MC-84 | La integración 045 → 046 con versión congelada sigue pasando |

## Plataforma

| Id | Criterio |
|---|---|
| AC-MC-90 | Toda la aceptación sobre **PostgreSQL 18.x** |
| AC-MC-91 | Regresión global con **0 fallos**; ningún escenario multiempresa omitido |
| AC-MC-92 | Selector sin violaciones serias de WCAG 2.2 AA, operable con teclado |
| AC-MC-93 | Sin desbordamiento horizontal entre 320 y 1440 |
| AC-MC-94 | Cross-browser en Chromium, Firefox y WebKit |
| AC-MC-95 | Acotar por empresa no degrada el plan: `EXPLAIN` en las tablas grandes |
| AC-MC-96 | Toda caché de empresa lleva la empresa en su clave |
| AC-MC-97 | Las claves de idempotencia no colisionan entre empresas |
