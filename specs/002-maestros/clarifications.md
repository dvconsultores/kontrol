# CLARIFICACIONES — 002-MAESTROS

| Campo | Valor |
|---|---|
| Iniciativa | 002-maestros |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Analista funcional senior / Especialista en convergencia |
| Ruta | `specs/002-maestros/clarifications.md` |

## 1. Ambigüedades resueltas

| ID | Tema | Pregunta | Decisión | Responsable | Estado |
|---|---|---|---|---|---|
| CL-002-01 | EAV/JSON para atributos | ¿Se permiten atributos libres por JSON? | **No.** Atributos gobernados con `AttributeDefinition/Applicability/Value`. JSON solo como copia histórica/snapshot (Constitución P8, DOC-01 §8). Los datos críticos (inventario, impuestos, lotes, seriales, regulación) jamás en EAV | Arquitecto de datos | Resuelto |
| CL-002-02 | Plantillas globales | ¿KONTROL provee plantillas globales de rubros/productos? | Sí, como catálogo semilla opcional; la empresa activa, copia o crea las propias. Las plantillas son versionadas | Producto | Resuelto |
| CL-002-03 | Ámbito de la taxonomía | ¿Rubros globales o por empresa? | Mixto: la taxonomía tiene ámbito empresa/global; cada empresa ve los suyos + los globales activos | Arquitecto | Resuelto |
| CL-002-04 | Tercero común vs. tablas separadas | ¿Cliente y proveedor como tablas separadas? | Entidad `Party` común + extensiones por rol (DOC-03 §3) para evitar duplicidad de RIF/direcciones | Arquitecto de datos | Resuelto |
| CL-002-05 | Servicio e inventario | ¿Un servicio puede tener inventario? | No en la modalidad inicial: los servicios no usan lote/serial/almacén; la línea puede facturarse sin afectar inventario (DOC-01 §8) | Producto | Resuelto |
| CL-002-06 | Concepto ISLR en servicios | ¿Porcentaje fijo en el formulario? | No. Referencia a regla ISLR versionada (DOC-04); el motor calcula en el pago (Spec 006/007) | Contador/fiscal | Resuelto |
| CL-002-07 | Perfil fiscal de terceros | ¿El perfil fiscal incluye retenciones? | Sí: perfil de retenciones (IVA/ISLR) versionado; el motor lo aplica en pagos/cobros | Contador | Resuelto |
| CL-002-08 | Aprobación de proveedor | ¿El proveedor requiere aprobación? | Sí: estado de aprobación (bancaria/fiscal) antes de pagar (DOC-04 pantalla 08) | Compras | Resuelto |
| CL-002-09 | Códigos de barras | ¿Único global o por empresa? | Unique por empresa/presentación (controlado), salvo política definida | Arquitecto de datos | Resuelto |
| CL-002-10 | Dependencia con 001 | ¿Se implementa 002 sin 001 certificada? | La implementación requiere 001 certificada (CI/Docker/legal) y autorización expresa; la fase documental no | Producto | Resuelto |

## 2. Supuestos declarados

| ID | Supuesto | Riesgo | Mitigación |
|---|---|---|---|
| SU-002-01 | El catálogo semilla de plantillas es opcional y no reemplaza la configuración de la empresa | Dependencia de contenido inicial | Seeds idempotentes separadas de datos legales |
| SU-002-02 | Los atributos se validan con tipos y catálogos, no con expresiones libres | Complejidad de validación | Restricciones y validadores gobernados |
| SU-002-03 | La duplicidad de RIF se controla por empresa y rol | Un mismo RIF con roles distintos es legítimo | Unique parcial + regla de dominio |

## 3. Ambigüedades que requieren decisión externa (pendientes)

| ID | Tema | Necesario para | Bloquea |
|---|---|---|---|
| CL-002-11 | Alcance del catálogo semilla global (sectores/rubros a incluir) | Contenido inicial | No la fase documental |
| CL-002-12 | Política de atributos obligatorios por rubro (definir conjunto base) | Validaciones de producto | No la fase documental |

## 4. Estado de aprobación

| Elemento | Estado |
|---|---|
| Ambigüedades resueltas | ✔ |
| Supuestos declarados | ✔ |
| Pendientes registrados | ✔ |
| Aprobación | Pendiente |
