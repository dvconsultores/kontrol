# KONTROL — BASELINE ARQUITECTÓNICA

| Campo | Valor |
|---|---|
| Versión | 1.0 |
| Fecha | 2026-08-29 |
| Emitida en | Gate G0 |
| Fundamento | Constitución v1.1 · 29 ADR `APPROVED` · 13 decisiones D0 |
| Naturaleza | **Consolidación. No introduce ninguna decisión nueva.** |

> Referencia obligatoria para toda Spec futura. Una Spec que necesite apartarse de esta baseline
> requiere enmienda del ADR correspondiente, no una excepción local.

---

## 1. Arquitectura general

**Monolito modular** desplegado por contenedores; microservicios descartados como complejidad
prematura. Límites por dominio en código, datos, permisos, eventos, pruebas y documentación.
Estructura `backend/app/modules/<dominio>` y `frontend/src/modules/<dominio>`. Un solo proceso API.
`ADR-001`

**Núcleo fiscal separado** del núcleo administrativo; reglas versionadas y nunca reescritas.
`Constitución P4`

---

## 2. Frontend

React 19 · TypeScript · Vite · Tailwind 4 · TanStack Query · React Router · RHF · Zod.

**Sistema de diseño único y obligatorio**: tokens (color, tipografía Ubuntu, espaciado 4px, radios,
sombras, z-index, breakpoints), componentes compartidos, Lucide React como única librería de iconos.
Ningún módulo resuelve por su cuenta formularios, tablas, botones, loaders, mensajes, modales,
validaciones, estados ni errores. `ADR-006` · `P7` · `P17`

**Política de modales**: prohibidos para crear o editar entidades, matrices, DataTables,
configuraciones extensas, documentos, permisos y procesos complejos. Los formularios complejos usan
ruta y pantalla completa con URL propia. Los modales se reservan para confirmación breve.
`ADR-015` · `P18`

**El frontend no es autoridad** sobre permisos, alcance, licencia, integridad, estados, acciones
permitidas, multiempresa ni reglas fiscales o regulatorias. `P6`

Accesibilidad WCAG 2.2 AA, responsive sin scroll horizontal en tablas. `P11`

---

## 3. Backend

Python 3.13 · FastAPI · Pydantic 2 · SQLAlchemy 2 · Alembic.

Validación de cada operación en backend y base de datos, **deny by default**. `P6`

**Idempotencia y concurrencia**: `Idempotency-Key` en POST críticos con `IdempotencyRecord`;
versión/ETag en PATCH con 409 en conflicto; locks en operaciones transaccionales; correlativos
asignados dentro de la transacción final. Sin doble envío, sin sobrescritura silenciosa, sin
reintentos no idempotentes. `ADR-013` · `P13`

**Documentos generados en backend con ReportLab**; el navegador no produce documentos fiscales
definitivos. Plantillas versionadas, snapshot de servidor, hash y metadatos. `ADR-007`

**Cola y workers diferidos**: sin Redis/Celery en la fundación. Punto de revisión trasladado a las
Specs 048 y 050. `ADR-009`

---

## 4. PostgreSQL

**Fuente de verdad transaccional única.** Ninguna caché reemplaza datos permanentes. `ADR-003`

**Paridad de producción** (`ADR-D0-001` · `P21`): PostgreSQL **18.x** obligatorio en desarrollo
integrado, integración, contrato, E2E, QA, staging y producción. SQLite solo en pruebas unitarias
que no ejerciten el dialecto, con marcador explícito. **Ninguna Spec alcanza `COMPLETE_100` sin
evidencia sobre PostgreSQL.**

| Parámetro | Valor |
|---|---|
| Encoding | UTF8 |
| Timezone del servidor | UTC |
| Rol de aplicación | `kontrol_app`, sin DDL ni superusuario |
| Rol de migración | `kontrol_migrator`, solo entrypoint |
| Extensiones autorizadas | `pgcrypto` (lista blanca cerrada) |
| Aislamiento de pruebas | Transacción con rollback; base por ejecución |

Migraciones Alembic en cadena lineal con head único.

---

## 5. Docker e instalación por cliente

Cada cliente opera una **instalación independiente** en su propio servidor mediante Docker Compose:
frontend, backend, PostgreSQL, volúmenes, `Installation ID` y licencia propios. No se comparten base
de datos, volúmenes, secretos, procesos, archivos, configuración, licencia ni logs. `ADR-002` · `P9`

Volúmenes: `kontrol-db-data`, `kontrol-storage`, `kontrol-license-state`, `kontrol-backups`.
Identidad de instalación persistente ante recreación de contenedores.

**Versionado**: lockfiles e imágenes fijadas; **sin `latest` en producción**; actualizaciones mayores
mediante Spec independiente. `ADR-014` · `P16`

**Observabilidad**: logs JSON con request ID y correlation ID, sin secretos; health checks
`/api/v1/health/live` y `/ready`. OpenTelemetry/Prometheus/Sentry diferidos. `ADR-010`

---

## 6. Autenticación y sesión

Access token de corta duración **en memoria**; refresh token en **cookie HttpOnly/Secure/SameSite**;
CSRF con doble cookie; contraseñas con **Argon2id**. Prohibido almacenar tokens de larga duración en
`localStorage`. Tabla `Session` con hash de refresh, rotación y revocación; cierre en todas las
pestañas. MFA preparado. `ADR-004`

> **Precisión operativa — `REM-AUTH-ROUTE-CRAWL-001`, 2026-08-30.** Como el access
> token vive en memoria, **toda recarga** dispara la restauración de sesión. El
> refresh token es de un solo uso, así que el cliente debe tener **una única
> puerta** de renovación que comparta la petición en vuelo: dos renovaciones
> simultáneas con la misma cookie no pueden prosperar las dos. Del lado del
> servidor, `rotate_session` bloquea la fila de sesión antes de leer su estado;
> sin ese bloqueo la ventana entre comprobar y escribir permitía que ambas
> prosperaran, anulando la detección de token robado.
>
> En una pila local servida por `http://`, `KONTROL_COOKIE_SECURE` debe ir en
> `false`: WebKit rechaza cookies `Secure` desde un origen inseguro. En producción,
> tras HTTPS, va en `true`.

---

## 7. Permisos y multiempresa

Cadena: `Installation/Tenant → Company → Branch → Establishment → Warehouse → Zone → Location`,
con dimensiones analíticas `CostCenter` y `BusinessUnit`. Tenant y company explícitos en cada
agregado; filtros de seguridad en repositorios; RLS como complemento, no sustituto. Archivos, caché
y colas incluyen tenant/company en la clave. `ADR-011` · `ADR-D0-004` · `ADR-D0-013` · `P11`

Matriz de dimensiones obligatorias por tipo de documento en `ADR-D0-013`. Toda dimensión debe
pertenecer a la empresa del documento. Las dimensiones se congelan en el documento.

---

## 8. Auditoría

`AuditEvent` **append-only**: tenant, company, user, action, entity, before/after, request_id,
session, source, reason, evidence y timestamp del servidor. Sin `UPDATE` ni `DELETE` físico.
Timeline consultable con permisos. `ADR-012` · `P5`

**Autoridad única** (`P22`): existe un solo mecanismo de auditoría en la plataforma.

---

## 9. Licenciamiento

Licencias firmadas con **Ed25519**; clave privada exclusiva de la autoridad central; clave pública
distribuida con `kid` versionado y rotación por vigencia. Firma inválida → `SECURITY_SUSPENSION`.
`ADR-005` · `ADR-D0-006`

Comunicación **siempre iniciada por la instalación** sobre HTTPS verificado. Operaciones: `activate`,
`sync`, `renew`, `replace_installation`, `heartbeat`.

Calendario contractual **transportado en la licencia firmada**, no en el código: período 1 abril →
31 marzo; aviso desde el 1 de abril; aviso crítico desde el 21 de abril; `READ_ONLY` desde el 1 de
mayo sin renovación.

En `READ_ONLY` el cliente **conserva consulta y exportación completas**; solo se bloquea la escritura
transaccional. La autoridad recibe únicamente metadatos de licenciamiento y **nunca** datos
comerciales. `P15`

---

## 10. Aprobaciones

**Motor único y transversal.** Ningún módulo implementa aprobación propia. `ADR-D0-002` · `P22`

Entidades: `ApprovalPolicy` (versionada) → `ApprovalRule` → `ApprovalLevel`;
`ApprovalRequest` → `ApprovalStep` → `ApprovalDecision`; `ApprovalDelegation`.

Reglas vigentes: niveles y umbrales nunca hardcodeados · política versionada con snapshot en la
solicitud · monto evaluado en moneda base con tasa del documento · segregación configurable ·
cuórum configurable · delegación acotada que no elude la segregación · obsolescencia automática si
cambia un campo de la condición · toda decisión auditada.

---

## 11. Inventario y reservas

Saldos **reconstruibles desde movimientos**; nunca se editan directamente. `P5`

`disponible = físico − reservado − bloqueado`. Ningún proceso presenta el físico como disponible.

Disparador de reserva configurable por empresa, **defecto `ORDER_RELEASED`**. Dos operaciones no
pueden reservar la misma unidad: la garantía es de base de datos dentro de la transacción. Toda
reserva tiene vigencia y expira con evento auditado. El consumo ocurre en la **salida física**, no en
la facturación. `ADR-D0-003` · `ADR-013`

**Estados de mercancía** independientes del estado del documento: `ESPERADO`, `RECIBIDO`,
`PENDIENTE_CONFIRMACION`, `CUARENTENA`, `BLOQUEADO`, `DISPONIBLE`, `RESERVADO`, `PICKING`,
`PREPARADO`, `TRANSITO`, `DESPACHADO`, `DEVUELTO`, `RECHAZADO`, `DESECHO`, `VENDIDO`.
Solo `DISPONIBLE` se ofrece a la venta. El paso a `DISPONIBLE` exige liberación formal.
Toda transición es un movimiento, no una edición. `ADR-D0-010`

---

## 12. Almacenes

`Company → Branch → Warehouse → WarehouseZone → Location(aisle, rack, level, position)`.
`Location` es la hoja y la única entidad que las transacciones referencian. `ADR-D0-004`

**KONTROL no define zonas fijas.** `zone_type` es catálogo por empresa.

Estados de ubicación: `ACTIVE`, `INACTIVE`, `BLOCKED`, `MAINTENANCE`, `FULL` (derivado de capacidad).

`location_managed` por almacén: cuando es `true`, todo movimiento exige ubicación. Permite adopción
gradual. La ubicación llega con FK real a recepción, movimiento, saldo, transferencia, conteo,
ajuste, picking, despacho, reserva y devolución.

---

## 13. Archivos y gestión documental

Volúmenes persistentes locales; metadatos y hash SHA-256 en PostgreSQL; sin binarios en la base;
MinIO/S3 diferido. `ADR-008`

Modelo: `DocumentType` · `Attachment` · `AttachmentVersion` · `AttachmentLink` (vinculación
polimórfica). Servicio **único y transversal**: ningún módulo implementa adjuntos propios.
`storage_key` opaca; prohibido derivar lógica de rutas del host. Los adjuntos se versionan, no se
sustituyen. Descarga autorizada por permiso sobre la **entidad vinculada**.
`ADR-D0-008` · `P22`

> **Implementado — `SPEC 046 COMPLETE_100`, 2026-08-30.** La nomenclatura final es
> `DocumentType` · `Document` · `DocumentVersion` · `StoredFile` · `DocumentLink`; la
> semántica y el contrato son los que fija `ADR-D0-008`. La vinculación **no** es
> polimórfica libre: hay un **registro cerrado** de tipos de recurso (19 hoy) y un
> tipo ausente se rechaza. `MinIO/S3` deja de estar diferido en cuanto a código
> —existe `S3CompatibleStorageProvider`— pero permanece
> **`IMPLEMENTED_NOT_VERIFIED`**: el proveedor validado de producción es el
> sistema de archivos. Detalle en `docs/roadmap/046-dependency-closeout.md`.

---

## 14. Unidades, presentaciones y snapshots

`Producto base ≠ unidad de inventario ≠ presentación de compra ≠ de venta ≠ de despacho`.

Toda línea transaccional conserva `item_id`, `uom_id`, `presentation_id`, `quantity`,
`conversion_factor_snapshot`, `base_quantity`, `price`, `currency`. `base_quantity` se calcula al
escribir y **se almacena**; nunca se recalcula desde el maestro vigente. El inventario va siempre en
unidad base. `ADR-D0-009` · `P23`

**Snapshot comercial**: al aprobarse un documento se congelan precio, descuento, política y versión
aplicadas, condición de pago, moneda, tasa y la lista o regla que produjo el precio. Modificar un
maestro nunca altera un documento aprobado. `ADR-D0-005`

**Snapshot fiscal**: cada documento conserva la regla fiscal aplicada con su versión y vigencia.
`ADR-D0-007` · `P4`

---

## 15. Reglas comerciales

Maestros: `PriceList`, `PriceListItem`, `PriceRule`, `DiscountPolicy`, `PaymentTerm`, `CreditPolicy`,
`CommercialZone`. Comisiones como capacidad futura reservada. Ningún dato comercial es texto libre.

Precedencia de precio **declarativa, versionada y configurable**, con orden por defecto documentado.
Un empate irresoluble se reporta como error de configuración. Superar el límite de descuento genera
solicitud de aprobación, no bloqueo. Condición de pago y política de crédito son entidades distintas.
`ADR-D0-005` · `P8`

---

## 16. Facturación y confirmación

**Vínculo pedido → factura**: `SalesInvoice.order_id` y `SalesInvoiceLine.order_line_id` nullable en
esquema, obligatorios cuando la factura deriva de pedido. Facturación directa admitida con permiso y
política, marcada `origin = DIRECT`. La cantidad facturada no puede exceder la autorizada; el control
resiste concurrencia. Anular devuelve saldo facturable; la nota de crédito no. `ADR-D0-011`

**Confirmación independiente**: entidad y evento distintos del picking, que comparan el pedido
original contra la mercancía preparada (producto, SKU, cantidad, presentación, condición).
Máquina de estados `RESERVED → PREPARING → PREPARED → CONFIRMED → READY_FOR_BILLING → INVOICED →
DISPATCHED → CLOSED`. No conforme genera incidencia y exige reconfirmación completa.
Segregación configurable con **defecto restrictivo**. `ADR-D0-012`

**Inmutabilidad**: los documentos fiscales emitidos no se editan ni se eliminan; se corrigen por nota,
anulación o reverso vinculado. `P4` · `P5`

---

## 17. Gobierno fiscal

El software decide **el mecanismo**; el profesional tributario decide **el contenido**.

Ninguna alícuota, porcentaje, unidad tributaria, concepto, mínimo, sustraendo ni fecha fiscal puede
existir en código, migración, seed o valor por defecto. Todos son datos de `TaxRuleVersion` con
fuente legal, Gaceta, artículo, vigencia y estado. `ADR-D0-007` · `P8` · `P19`

Toda regla nace en `LEGAL_VALIDATION_REQUIRED`; solo un profesional identificado la promueve a
`VALIDATED`, con auditoría. **No se emite documento fiscal con regla no validada.** Derogar cierra
vigencia sin reescribir. Prohibido declarar cumplimiento u homologación sin acto formal.

KONTROL no fabrica permisos, guías ni certificados de organismos externos. `P20`

---

## 18. Pruebas

Toda evidencia sobre PostgreSQL. `P21`

Niveles: unit · integración · contrato (puertas menú↔ruta↔API) · E2E · accesibilidad (axe WCAG 2.2 AA) ·
responsive · cross-browser · idempotencia y concurrencia · seguridad · migraciones · rendimiento ·
backup y restore.

Ninguna función se declara terminada sin pruebas y evidencia. La ausencia de error técnico no
equivale a calidad de producto. `P10`

---

## 19. Seguridad

Deny by default en backend y base de datos. Aislamiento multiempresa verificable con pruebas
negativas. RBAC con permiso por acción y alcance. Lockout ante fuerza bruta. CSP y HSTS en nginx.
Secretos fuera del código y de los logs. Dependencias con lockfile y revisión de CVE.
`P6` · `P9` · `ADR-004` · `ADR-011` · `ADR-014`

---

## 20. Lo que esta baseline NO decide

Por diseño, quedan fuera y corresponden a otras instancias:

| Ámbito | Quién decide |
|---|---|
| Umbrales y niveles de aprobación | Cada empresa (configuración) |
| Disparador y vigencia de reserva | Cada empresa (configuración) |
| Zonificación física del almacén | Cada empresa (configuración) |
| Precedencia final, límites de descuento, comisiones | Producto y Ventas |
| Alícuotas, conceptos y matrices oficiales | Abogado tributario y contador público |
| Hospedaje de la autoridad de licencias | Producto e Infraestructura |
