# ADR-D0-006 — Arquitectura de la autoridad central de licenciamiento

| Campo | Valor |
|---|---|
| ID | D0-06 |
| Estado | **APPROVED** (arquitectura) · **BUSINESS_DECISION_PENDING** (hospedaje) |
| Fecha | 2026-08-29 |
| Responsable | Arquitecto de seguridad · Arquitecto de infraestructura · Product Owner |
| Extiende | `ADR-005 — Licenciamiento con Firma Asimétrica` (PROPUESTO) · `ADR-002 — Instalación Independiente` |
| Specs afectadas | **004** · 048, 052, 053 |

## Problema

`ADR-005` cerró la **firma** (Ed25519, clave privada solo en la autoridad). Difirió la autoridad
central a la Spec 010, que se implementó como *cliente*: existe el contrato v1, el agente y la
máquina de estados, pero **la autoridad no existe** — no hay servidor, ni proveedor decidido, ni
prueba contra red real.

## Por qué debe decidirse ahora

El licenciamiento es el mecanismo de sostenibilidad comercial del producto. Toda la lógica del
cliente ya está construida contra un contrato que nadie ha implementado del otro lado: si el
contrato cambia al construir el servidor, cambia también cada instalación desplegada.

## Evidencia

- `licensing/service.py:368-386` — `default_sync_client` con `urllib.request` contra `/v1/license/sync`.
- `licensing/service.py:335-342` — máquina de estados `PENDING → FULL_ACCESS → RENEWAL_NOTICE → CRITICAL_RENEWAL_NOTICE → READ_ONLY / SECURITY_SUSPENSION`.
- `core/license.py:106-128` — **las fechas del calendario llegan en el payload firmado**, no están codificadas. Arquitectura correcta, se confirma.
- `specs/010-licenciamiento-central/convergence.md` `CVG-010-01` — servidor central pendiente.

## Arquitectura aprobada

```
INSTALACIÓN DEL CLIENTE (servidor propio, Docker Compose)
   frontend · backend · PostgreSQL · volúmenes · Installation ID
        │
   License Agent  ── verifica firma · aplica modo · tolera desconexión
        │  HTTPS (TLS verificado, solo salida)
        ▼
KONTROL LICENSE AUTHORITY  (infraestructura del propietario)
   contrato · licencia · activación · renovación · revocación · auditoría
   clave privada Ed25519  ── NUNCA sale de aquí
```

> **R-D0-06-1.** La comunicación es **siempre iniciada por la instalación**. La autoridad no abre
> conexiones hacia el cliente ni requiere puertos entrantes en su servidor. Una autoridad que
> pudiera entrar en la instalación del cliente contradiría el Principio 15.

## Operaciones del contrato

| Operación | Dirección | Propósito |
|---|---|---|
| `activate` | cliente → autoridad | Primer registro de la instalación; devuelve licencia firmada |
| `sync` | cliente → autoridad | Confirmación periódica; devuelve licencia vigente o cambio de modo |
| `renew` | cliente → autoridad | Solicitud de renovación con comprobante |
| `revoke` | autoridad → *entregado en el siguiente `sync`* | Revocación; no requiere conexión entrante |
| `replace_installation` | cliente → autoridad | Traslado a servidor nuevo; invalida la instalación anterior |
| `heartbeat` | cliente → autoridad | Señal de vida ligera; detecta clonación |

## Ciclo contractual

Período **1 de abril → 31 de marzo**. Desde el **1 de abril**, aviso de renovación. Desde el
**21 de abril**, aviso crítico. Desde el **1 de mayo** sin renovación confirmada, **`READ_ONLY`**.

> **R-D0-06-2.** Estas fechas viajan **en la licencia firmada**, no en el código. Ya está así
> implementado (`core/license.py`) y se ratifica: permite períodos distintos por contrato sin
> reconstruir la aplicación.
>
> **R-D0-06-3.** En `READ_ONLY` el cliente **conserva acceso completo de consulta y exportación de
> sus datos**. Solo se bloquea la escritura transaccional. El licenciamiento nunca es un mecanismo
> de retención de datos ajenos (P15).

## Seguridad

| Aspecto | Decisión |
|---|---|
| Algoritmo | Ed25519 (ratifica ADR-005) |
| Clave privada | Solo en la autoridad; nunca en imagen, repositorio ni instalación |
| Clave pública | Distribuida con la instalación, identificada por `kid` |
| Rotación | Por `kid`: la instalación acepta varias claves públicas vigentes; la retirada de una clave es un evento con vigencia, no un corte |
| Payload | Incluye `installation_id`; una licencia de otra instalación se rechaza (ya implementado) |
| Integridad | Hash canónico del payload; firma inválida → `SECURITY_SUSPENSION` |
| Reloj | Tolerancia offline anclada a `last_reliable_date` monótona: retrasar el reloj del servidor no extiende la licencia |
| Transporte | TLS con verificación de certificado obligatoria; sin modo inseguro |

## Privacidad — límite duro

> **R-D0-06-4.** La autoridad recibe **exclusivamente**: `installation_id`, versión del producto,
> estado de licencia, marca temporal, huella de entorno no identificable y métricas de volumen
> agregadas si el contrato lo exige.
>
> **R-D0-06-5.** La autoridad **no recibe y no puede solicitar**: facturas, clientes, proveedores,
> inventario, importes, usuarios, correos ni ningún dato comercial. Cualquier campo nuevo del
> contrato que transporte datos de negocio es una violación del Principio 15 y exige enmienda de
> este ADR.

## Hospedaje — decisión empresarial

**No se recomienda ni se inventa proveedor.** Requisitos técnicos que cualquier opción debe cumplir:

TLS con certificado válido y renovación automática · disponibilidad suficiente para no bloquear
renovaciones (la tolerancia offline mitiga caídas cortas) · almacenamiento cifrado de la clave
privada con custodia y respaldo · registro de auditoría de emisión y revocación · respaldo con
recuperación probada · aislamiento del entorno de emisión.

**Riesgo:** perder la clave privada invalida la capacidad de emitir y renovar **todas** las
licencias. La custodia de esa clave es el activo más crítico del modelo comercial.

Ver OQ-07 — **BUSINESS_DECISION_PENDING**.

## Impacto

| Dimensión | Impacto |
|---|---|
| Frontend | Ninguno (las pantallas existen) |
| Backend | Cliente ya implementado; falta prueba contra servidor real y rotación por `kid` |
| Base de datos | Ninguno |
| Integraciones | **Alto** — es la única integración externa real del producto |
| QA | Pruebas contra servidor de pruebas; manipulación de reloj; firma inválida; expiración |
| Seguridad | Custodia de clave, rotación, TLS |
| Fiscal | Ninguno |

## Migración / compatibilidad

**`NO_MIGRATION`** en el cliente. El contrato v1 se conserva; la rotación por `kid` es aditiva.

## Criterios de aceptación

- [ ] Instalación limpia activa contra la autoridad y recibe licencia firmada válida.
- [ ] Licencia de otra instalación rechazada.
- [ ] Firma inválida → `SECURITY_SUSPENSION` con evento.
- [ ] Retrasar el reloj no extiende la tolerancia offline.
- [ ] Rotación de `kid` sin interrumpir instalaciones vigentes.
- [ ] En `READ_ONLY` la consulta y la exportación siguen funcionando.
- [ ] Auditoría del contrato demuestra que no viaja ningún dato de negocio.

## Estado final

**APPROVED** para la arquitectura, el contrato, la seguridad y la privacidad.
**BUSINESS_DECISION_PENDING** para el hospedaje.
Clasificación de cierre: **BUSINESS_DECISION_PENDING**.
