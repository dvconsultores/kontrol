# REGISTRO DE RIESGOS — ARCH-MC-001

## 1. Modelo de amenazas

| Id | Amenaza | Control |
|---|---|---|
| AMC-01 | IDOR entre empresas | 404 sin confirmar existencia · `AC-MC-13/31` |
| AMC-02 | Cabecera de empresa falsificada | Validación en servidor · `AC-MC-13` |
| AMC-03 | Manipulación del almacenamiento del navegador | El cliente no es autoridad · `AC-MC-17` |
| AMC-04 | Contexto obsoleto tras perder acceso | Revalidación por petición · `AC-MC-16` |
| AMC-05 | Escalada por permiso sin alcance | Permiso y alcance separados · `AC-MC-43` |
| AMC-06 | Fuga por caché | La empresa entra en la clave · `AC-MC-96` |
| AMC-07 | Consulta sin acotar | Acotada en el backend · `AC-MC-30` |
| AMC-08 | Asignación masiva de `company_id` | 409 · `AC-MC-34` |
| AMC-09 | Trabajo de fondo en la empresa equivocada | Contexto explícito o fallo · `AC-MC-20` |
| AMC-10 | Vínculo documental entre empresas | 404 · `AC-MC-81` |
| AMC-11 | Pago de A aplicado a factura de B | 409 · `AC-MC-63` |
| AMC-12 | Existencias mezcladas | Separación probada · `AC-MC-64` |
| AMC-13 | Factura emitida por la empresa equivocada | Contexto validado · `AC-MC-55` |
| AMC-14 | Reutilización de número fiscal entre empresas | Series independientes · `AC-MC-50/51` |
| AMC-15 | Informe contaminado | Acotado por empresa · `AC-MC-30` |
| AMC-16 | Auditoría ambigua | Tenant, empresa, usuario, acción, entidad · `FR-MC-040` |
| AMC-17 | Dos pestañas contaminadas | Cabecera por petición · `AC-MC-18` |

## 2. Riesgos de la migración

| Id | Riesgo | Gravedad | Mitigación |
|---|---|---|---|
| R-MC-1 | **Backfill determinista falso**: dar por buena una empresa deducida del recuento actual | **Crítica** | `FR-MC-052`: se decide por intervalo. `AC-MC-71` |
| R-MC-2 | Corrupción fiscal por migrar mal series o libros | **Crítica** | Ola fiscal con especialista; `AC-MC-50..55` |
| R-MC-3 | Mezcla financiera al derivar mal un pago | **Crítica** | Derivación solo por FK obligatoria; conflicto ⇒ MC-C |
| R-MC-4 | Crítico no reconstruible ignorado | **Crítica** | `FR-MC-053`: bloquea, sin valor por defecto |
| R-MC-5 | Pérdida de dato al sobrescribir lo heredado | Alta | `FR-MC-054`: se conserva hasta verificar |
| R-MC-6 | Migración parcial que deja el sistema a medias | Alta | Expandir/contraer con recuperación entre fases |
| R-MC-7 | Derivación incorrecta por FK anulable | Alta | Medido: las 36 derivan por FK obligatoria |
| R-MC-8 | Único mal estrechado que rompe datos válidos | Alta | Revisión una a una; `OQ-MC-01` sin resolver bloquea su tabla |
| R-MC-9 | Regresión de una Spec cerrada | Alta | Revalidación completa de 008, 011, 045, 046 |
| R-MC-10 | Degradación de rendimiento | Media | `EXPLAIN` y compuestos justificados |
| R-MC-11 | Reintroducir la carrera de `/auth/refresh` | Alta | La cabecera **no** toca la sesión; regresión de auth |
| R-MC-12 | Estado obsoleto en el frontend al cambiar de empresa | Media | Invalidación total; `AC-MC-35` |
| R-MC-13 | Duración de la migración sobre datos reales | Media | Por olas, con informe previo |

## 3. El riesgo de no hacerlo

| Id | Riesgo | Gravedad |
|---|---|---|
| R-MC-14 | **La ventana se cierra**: en cuanto un tenant tenga dos empresas y opere, el backfill deja de ser determinista **para siempre** | **Crítica** |
| R-MC-15 | Cada Spec nueva añade tablas al defecto. La 012 aporta nueve en el dominio del precio | **Crítica** |
| R-MC-16 | Libros fiscales inválidos en el primer cliente con dos RIF | **Crítica** |

## 4. Riesgo de gobierno

| Id | Riesgo | Estado |
|---|---|---|
| R-MC-17 | Cerrar con «faltan cinco tablas» o «fiscal después» | **Excluido** por el §227: no se admite deuda interna |
| R-MC-18 | `OQ-MC-01` sin responder | **Controlado**: bloquea unas pocas tablas de catálogo, no el diseño |
