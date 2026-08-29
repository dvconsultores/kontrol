# PLAN DE PRUEBAS — SPEC 045

**Motor obligatorio: PostgreSQL** (P21). Los casos de concurrencia y de restricción son
inejecutables en SQLite: ignora `SELECT … FOR UPDATE` y difiere en constraints.

## 1. Unidad — `pytest`

| Grupo | Casos |
|---|---|
| `ConditionEvaluator` | Cada operador; combinación `AND`; ausencia de dato → error; varias reglas acumulan niveles |
| Normalización de moneda | Equivalente en base con tasa snapshot; moneda base = moneda documento; tasa ausente |
| `FingerprintService` | Determinismo; cambio en campo de condición altera; cambio ajeno no altera; `fingerprint_fields` registrado |
| `ActorResolver` | Por rol, por usuario, por alcance; con delegación vigente, vencida y revocada; exclusión por segregación |
| Cuórum | `ANY`, `ALL`, `N_OF_M`; una negativa cierra en todos |
| Máquina de estados | Transiciones válidas; prohibición de salir de terminal; INV-01..INV-08 |

## 2. Integración API — `pytest` + TestClient

| Grupo | Casos |
|---|---|
| Políticas | Crear, versionar, activar, cerrar; solapamiento rechazado; edición solo en `DRAFT` |
| Evaluación | `evaluate` sin efectos secundarios; sin regla aplicable; condición no evaluable |
| Solicitud | Crear; idempotencia; snapshot congelado; elegibles congelados |
| Resolución | Aprobar, rechazar, devolver, cancelar; motivo obligatorio; avance de nivel |
| Obsolescencia | Marcado automático; resolución rechazada |
| Delegación | Crear, ejercer, revocar; herencia de restricciones |
| Permisos | 401 sin sesión; 403 sin permiso; 403 sin elegibilidad; `allowed_actions` correcto |
| Alcance | Solicitud de otra empresa → 404 (IDOR) |

## 3. Concurrencia — **solo PostgreSQL**

| Caso | Resultado esperado |
|---|---|
| Dos decisiones simultáneas sobre el mismo paso | 1 registrada, 1 × 409 |
| Dos activaciones de política solapada | 1 activa, 1 × 409 |
| Decisión mientras el documento cambia | Solicitud `OBSOLETE`; decisión rechazada |
| Doble creación de solicitud | 1 sola solicitud |
| Cuórum `N_OF_M` con N decisiones simultáneas | Cuórum exacto, sin sobrepasar |

## 4. Contrato

- OpenAPI ↔ llamadas del frontend (puertas G1-G4 de `audit-completeness.test.ts`).
- Códigos de error del contrato presentes y con la semántica documentada.
- `allowed_actions` presente en toda respuesta de solicitud y paso.

## 5. E2E — Playwright

| Escenario | Pasos |
|---|---|
| Ciclo favorable | Configurar política → crear orden que supera umbral → verificar bloqueo → aprobar en 2 niveles → la orden avanza |
| Devolución | Solicitar → devolver con motivo → documento editable → corregir → reenviar → aprobar |
| Segregación | El creador no ve acciones y recibe 403 por API |
| Bandeja transversal | Solicitudes de 4 dominios visibles en una lista |
| Obsolescencia | Cambiar el documento durante la revisión → aviso de solicitud obsoleta |

## 6. Accesibilidad y responsive

- axe WCAG 2.2 AA en políticas, edición de política, bandeja, historial y delegaciones.
- 5 rutas × 6 viewports (320…1920), 0 scroll horizontal.
- Operación completa solo con teclado en la bandeja.

## 7. Regresión de la migración

Para cada uno de los cuatro dominios: la batería existente debe pasar **sin cambios de expectativa**
tras redirigir al motor. Un cambio de comportamiento observable es un fallo de migración, no una
mejora.

| Dominio | Suite existente |
|---|---|
| Compras | `test_purchasing.py` |
| Ventas | `test_sales.py` |
| Inventario | `test_inventory.py` |
| Regulatorio | `test_regulatory.py` |
| Procesos | `test_process_flows.py`, E2E in-process 20/20 |

## 8. Rendimiento

`evaluate` ≤ 50 ms P95 con política de 10 reglas y 3 niveles sobre dataset representativo
(NFR-045-01). Verificación de N+1 en la bandeja con 1.000 solicitudes.

## 9. Criterio de salida

- Toda la suite verde **sobre PostgreSQL**.
- Los 24 criterios de aceptación cubiertos.
- Concurrencia y obsolescencia probadas, no razonadas.
- Búsqueda de lógica de aprobación fuera del motor: 0 coincidencias.
- Búsqueda de valores de negocio literales en `approvals`: 0 coincidencias.
