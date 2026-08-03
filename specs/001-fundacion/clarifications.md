# CLARIFICACIONES — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Fecha | 2026-08-03 |
| Responsable | Analista funcional senior / Especialista en convergencia |
| Ruta | `specs/001-fundacion/clarifications.md` |

## 1. Propósito

Registrar preguntas, supuestos, decisiones y ambigüedades resueltas o pendientes durante el flujo Spec Kit de `001-fundacion`. Las ambigüedades no resueltas se convierten en bloqueos en `analysis-report.md`.

## 2. Ambigüedades resueltas

| ID | Tema | Pregunta | Decisión | Responsable | Estado |
|---|---|---|---|---|---|
| CL-01 | Nombre del producto | ¿Usar INNOVA o KONTROL en artefactos nuevos? | Todo artefacto nuevo usa KONTROL. INNOVA solo en documentos fuente históricos | Product Owner | Resuelto |
| CL-02 | Relación Instalación ↔ Tenant ↔ Company | ¿Cuántas empresas por instalación? | Una instalación = un tenant. La licencia define plan monoempresa o multiempresa (límite). Company es la entidad legal dentro del tenant | Arquitecto de datos + Producto | Resuelto (ver data-model) |
| CL-03 | Alcance del licenciamiento central | ¿Se implementa el portal central en 001? | No. El portal central es `010-licenciamiento-central`. En 001 solo subsistema local (verificar/importar/aplicar) | Product Owner | Resuelto |
| CL-04 | Modalidad inicial de facturación | ¿Se emite factura fiscal en 001? | No. La emisión fiscal es de Specs posteriores. En 001 se prepara la infraestructura del núcleo fiscal | Especialista legal | Resuelto |
| CL-05 | Cola y worker | ¿Se incluye Redis/Celery en 001? | No. Requiere ADR y necesidad demostrada. Se difiere | Arquitecto | Resuelto |
| CL-06 | Forma de autenticación | ¿JWT en localStorage o cookies? | Cookies HttpOnly/Secure/SameSite para refresh + access token corto en memoria; CSRF. ADR-004 | Arquitecto de seguridad | Resuelto (ADR-004) |
| CL-07 | Nombres de módulos | ¿Nombres de dominios compartidos? | Backend: `modules/<dominio>`; Frontend: `src/modules/<dominio>`. Dominios de `plan.md` | Arquitecto de software | Resuelto |
| CL-08 | Fecha confiable | ¿Qué autoridad para licencia? | Fecha/hora del servidor (America/Caracas) + última fecha confiable persistida. El navegador nunca decide | Arquitecto de seguridad | Resuelto |
| CL-09 | Estado de alícuotas | ¿Se hardcodean IVA 16/8/0? | No. Se modelan como reglas versionadas con fuente. En 001 solo se prepara la estructura | Especialista legal | Resuelto |
| CL-10 | Rama de trabajo | ¿Dónde se trabaja 001? | Rama `feature/001-fundacion` derivada de `develop` | DevSecOps | Resuelto |
| CL-11 | Versión de PostgreSQL | ¿16 o 18? | Pendiente de `research.md`; propuesta inicial 18.x (DOC-08). No fijar imagen sin evidencia | Arquitecto de datos | Pendiente (CON-01) |
| CL-12 | Versión de Vite | ¿Vite 8 real? | Pendiente de `research.md` | Arquitecto frontend | Pendiente (CON-02) |
| CL-13 | Versión de Python | ¿3.13 compatible? | Pendiente de `research.md` | Arquitecto backend | Pendiente (CON-03) |
| CL-14 | Planes de licencia | ¿Campos del entitlement? | `entitlements`: companies, users, modules, points_of_sale, integrations (por definir en Spec central) | Producto | Parcial — se modela genérico |

## 3. Supuestos asumidos (declarados, no ocultos)

| ID | Supuesto | Riesgo | Mitigación |
|---|---|---|---|
| SU-01 | El corte normativo 2026-08-03 es la base; toda norma fiscal se revalidará antes de producción | Cambio normativo | Matriz normativa con estado `LEGAL_VALIDATION_REQUIRED` |
| SU-02 | La forma libre computarizada es la modalidad inicial sujeta a autorización/homologación | Homologación | No se implementa emisión fiscal en 001 |
| SU-03 | Una instalación Docker = un tenant aislado | Confusión con multiempresa | Documentado en data-model |
| SU-04 | El soporte remoto nunca accede sin autorización expresa del cliente | Privacidad | Política en license-foundation |
| SU-05 | Los PDF de `requerimientos/` se versionan como documentos fuente | Tamaño del repo | Mantener solo documentos fuente; evidencia binaria en carpeta ignorada |

## 4. Ambigüedades que requieren decisión externa (pendientes)

| ID | Tema | Necesario para | Bloquea |
|---|---|---|---|
| CL-11 | Versión PostgreSQL | Fijar imagen Docker | Fijar imagen (no la fase documental) |
| CL-12 | Versión Vite | Fijar lockfile frontend | Fijar lockfile |
| CL-13 | Versión Python | Fijar imagen backend | Fijar imagen |
| CL-14 | Definición de entitlement/plan | Modelo de licencia multiempresa | Especificar límites (se usa genérico) |
| CL-15 | Política de conservación documental (plazos por dominio) | Retención de auditoría/archivos | Configuración de retención (no la fundación) |
| CL-16 | Correo/servidor SMTP para notificaciones | Notificaciones de licencia | Envío real de correo (se difiere) |

## 5. Estado de aprobación

| Elemento | Estado |
|---|---|
| Ambigüedades resueltas | ✔ |
| Supuestos declarados | ✔ |
| Pendientes registrados | ✔ |
| Aprobación | Pendiente |
