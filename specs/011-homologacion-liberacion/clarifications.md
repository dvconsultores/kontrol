# CLARIFICACIONES — 011-HOMOLOGACION-LIBERACION

| Campo | Valor |
|---|---|
| Iniciativa | 011-homologacion-liberacion |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Analista funcional senior / Especialista en convergencia |
| Ruta | `specs/011-homologacion-liberacion/clarifications.md` |

## 1. Ambigüedades resueltas

| ID | Tema | Pregunta | Decisión | Responsable | Estado |
|---|---|---|---|---|---|
| CL-011-01 | Homologación vs. liberación | ¿Son lo mismo? | Son procesos **relacionados pero distintos**: la homologación documenta el acto formal de una versión fiscal; la liberación libera una versión a producción con gates | Arquitecto | Resuelto |
| CL-011-02 | Acto formal | ¿Se fabrica? | **No.** 011 registra la referencia y la evidencia (hash SHA-256); el acto lo emite el proceso externo (abogado/contador/equipo de homologación) | Arquitecto | Resuelto |
| CL-011-03 | "Liberación" | ¿Liberación de lotes? | Es **liberación de versión** (release). No hay evidencia de liberación de lotes de inventario en los DOC | Producto | Resuelto |
| CL-011-04 | Gates | ¿Cuáles iniciales? | tests, seguridad, homologación documentada (aprobada), licencia válida (FULL_ACCESS), respaldo disponible | Arquitecto | Resuelto |
| CL-011-05 | Segregación | ¿Quién evalúa? | Quien crea/somete no aprueba su propia homologación (DOC-01 §5: un usuario no crea y aprueba su propia excepción crítica) | Producto | Resuelto |
| CL-011-06 | Dependencias | ¿Se implementa sin 002-010? | Requiere **001 certificada** y **002-010 implementados** (entitlements y módulos) | Producto | Resuelto |
| CL-011-07 | Núcleo | ¿Módulo nuevo? | Nuevo módulo `app/modules/homologation/` (homologación + liberación) | Arquitecto | Resuelto |
| CL-011-08 | Modalidad fiscal | ¿Qué valores? | Configurable: E-FACTURA, FACTURA_PAPEL, FORMA_LIBRE, MAC, DIGITAL, E-COMPRAS | Producto | Resuelto |

## 2. Supuestos declarados

| ID | Supuesto | Riesgo | Mitigación |
|---|---|---|---|
| SU-011-01 | El acto formal proviene de un proceso externo | Sin acto, no se libera | Regla FR-011-005/012 lo bloquea |
| SU-011-02 | Los gates se verifican en el panel antes de liberar | Gate falso | Registro por gate con quién/cuándo |
| SU-011-03 | La versión fiscal se identifica como string semver | Colisión | Validación de formato y unicidad de versión |
| SU-011-04 | El modo de licencia proviene de 001 | Modo cambiante | Se evalúa en el momento de liberar |
| SU-011-05 | El timeline reutiliza la convención append-only | Pérdida de integridad | Hash encadenado opcional en eventos |

## 3. Ambigüedades que requieren decisión externa (pendientes)

| ID | Tema | Necesario para | Bloquea |
|---|---|---|---|
| CL-011-09 | Integración con CI/CD externo (pipeline de gates) | Automatizar gates | No la fase documental |
| CL-011-10 | Formato oficial del acto formal (documento/expediente) | Plantilla de evidencia | No la fase documental |

## 4. Estado de aprobación

| Elemento | Estado |
|---|---|
| Ambigüedades resueltas | ✔ |
| Supuestos declarados | ✔ |
| Pendientes registrados | ✔ |
| Aprobación | Pendiente |
