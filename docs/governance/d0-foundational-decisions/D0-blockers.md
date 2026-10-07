# BLOQUEANTES D0

| ID | Decisión | Descripción | Tipo | Impacto | Acción requerida | Responsable |
|---|---|---|---|---|---|---|
| **BLK-D0-01** | D0-01 | No existe instancia PostgreSQL para desarrollo, CI ni QA | TECHNICAL_BLOCKER | Ninguna Spec puede alcanzar `COMPLETE_100`; el drift real es desconocido | Aprovisionar PG 18.x en `compose.dev` y en CI; ejecutar `upgrade head` y `check` | DevOps · DBA |
| **BLK-D0-02** | D0-07 | Las 24 reglas fiscales carecen de validación profesional | **LEGAL_BLOCKER** | Sin certificación fiscal ni homologación; prohibido declarar cumplimiento | Contratar abogado tributario venezolano y contador público para revisar la matriz | Legal · Fiscal |
| **BLK-D0-03** | D0-02 | Umbrales y niveles de autoridad sin definir | PROCESS_BLOCKER | **No bloquea** el motor; bloquea la implantación en cliente | Definir política de aprobación por proceso | Producto · Compras · Finanzas |
| **BLK-D0-04** | D0-03 | Disparador de reserva y vigencia sin confirmar | PROCESS_BLOCKER | **No bloquea** la Spec 030; el defecto está decidido | Confirmar disparador y duración | Producto · Ventas |
| **BLK-D0-05** | D0-04 | Mapa físico real del almacén sin levantar | PROCESS_BLOCKER | **No bloquea** la Spec 008; bloquea la puesta en marcha del put-away | Levantamiento físico: zonas, pasillos, racks, niveles, posiciones | Almacén · Logística |
| **BLK-D0-06** | D0-05 | Precedencia de precio, límites de descuento y alcance de comisiones sin confirmar | PROCESS_BLOCKER | **No bloquea** la Spec 012; el defecto está propuesto | Confirmar precedencia y límites | Producto · Ventas |
| **BLK-D0-07** | D0-06 | Hospedaje de la autoridad de licencias — **resuelto el 2026-10-07** (servicio del propietario, aislado, agnóstico de proveedor; Fase 1 implementada) | **RESOLVED** | Ya no bloquea la construcción; el cierre de la 004 depende de `CENTRAL-SYNC-AUTHORITY-UNDEFINED` (autenticación de la instalación para sync) | Definir la autenticación de la instalación; desplegar la imagen en la infraestructura del propietario | Producto · Infraestructura |

## Cambio respecto al GAP Analysis

El GAP Analysis registró siete bloqueantes de los cuales **cinco eran de proceso y aparentaban
detener el desarrollo**. Tras D0, cinco de los siete (BLK-D0-03 a BLK-D0-06, y parcialmente el 07)
**ya no bloquean la construcción**: la arquitectura parametrizable está decidida y lo que falta son
datos de implantación.

| | Antes de D0 | Después de D0 |
|---|---:|---:|
| Bloquean escribir Specs | 5 | **0** |
| Bloquean cerrar Specs | 2 | 2 (BLK-D0-01, BLK-D0-02) |
| Bloquean implantar en cliente | 0 | 4 |
| Bloquean el modelo comercial | 1 | 1 (BLK-D0-07) |

Éste es el resultado principal de la fase: **ninguna decisión de proceso pendiente impide ya
comenzar a especificar.**

## Riesgo concentrado

**BLK-D0-02** (legal) y **BLK-D0-07** (custodia de clave) son los dos que no dependen del equipo
técnico y los dos cuyo retraso tiene consecuencias que el software no puede mitigar: uno impide
vender el producto conforme a norma, el otro impide sostener el modelo de licenciamiento.
