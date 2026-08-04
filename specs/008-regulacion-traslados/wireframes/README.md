# WIREFRAMES — 008-REGULACION-TRASLADOS

| Campo | Valor |
|---|---|
| Iniciativa | 008-regulacion-traslados |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/008-regulacion-traslados/wireframes/README.md` |

> Aplicación de las guías DOC-08 (WF-02 maestro-detalle; WF-05 estados y transiciones). Grids sin scroll horizontal (FR-008-101).

## 1. Organismos y perfiles (WF-02)

- **Autoridades**: lista + detalle (código, nombre, método de validación).
- **Tipos de permiso**: por autoridad (código, nombre, alcance).
- **Registros oficiales**: número, autoridad, fechas, archivo, estado.
- **Perfiles regulatorios**: rubro/operación/origen/destino → documentos requeridos (maestro-detalle).

## 2. Vehículos y conductores

- **Vehículos**: placa, tipo, capacidad, propietario, documentos.
- **Conductores**: tercero, licencia, documentos.
- Asignación a despacho/permiso.

## 3. Permisos y guías (WF-05)

- **Permisos**: lista con número, tipo, vigencia, estado; acciones por estado (registrar, verificar, aprobar uso, usar, expirar, rechazar).
- **Guías**: SICA / SIGESAI / SACS con número, organismo, vigencia, hash y verificación (registro y validación; no fabricación).

## 4. Evaluación del despacho (WF-05)

- **Evaluación**: por línea de despacho; panel de requisitos consolidados.
- **Bloqueos**: faltante/vencido/no coincidencia por línea; estado del despacho (bloqueado/aprobado).
- Acciones: anular bloqueo (auditado), aprobar salida.

## 5. Contingencias y aprobaciones

- **Contingencias**: habilitadas solo con regla oficial versionada (motivo, responsable, vigencia).
- **Aprobaciones**: solicitud con objeto, regla, riesgo, monto, plazo y decisión.

## 6. Navegación

- Sidebar (lucide-react): `Regulatorio` → Organismos y perfiles · Vehículos y conductores · Permisos y guías · Evaluación de despachos · Contingencias.
- Rutas: `/regulatorio/organismos`, `/regulatorio/vehiculos`, `/regulatorio/permisos`, `/regulatorio/evaluacion`, `/regulatorio/contingencias`.
