# WIREFRAMES — 011-HOMOLOGACION-LIBERACION

| Campo | Valor |
|---|---|
| Iniciativa | 011-homologacion-liberacion |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/011-homologacion-liberacion/wireframes/README.md` |

> Maquetas de referencia para el frontend `src/modules/homologacion/`. Siguen el patrón DataTable/AsyncButton de la app.

## 1. Homologación — registro y evaluación

```
[Homologación ▸ Actos]
+--------------------------------------------------------------+
| Versión fiscal: [____]  Modalidad: [E-FACTURA v]             |
| Acto formal:    [____]  Evidencia SHA-256: [________________]|
| [Registrar (DRAFT)]                                           |
+--------------------------------------------------------------+
| Acto | Versión | Modalidad | Estado | Evaluador | Acciones   |
| ...  | ...     | ...       | ...   | ...       | [Someter]   |
| ...  | ...     | ...       | SUBMITTED | —      | [Aprobar][Rechazar] |
+--------------------------------------------------------------+
```

## 2. Versiones y liberación

```
[Homologación ▸ Versiones]
+--------------------------------------------------------------+
| Versión: [1.1.0]  Changelog: [___________________]           |
| Gates: [x] tests  [x] seguridad  [x] homologación  [x] licencia  [x] respaldo
| [Crear versión]                                               |
+--------------------------------------------------------------+
| Versión | Estado | Homologación | Liberado por | Fecha | Acciones |
| 1.1.0   | CANDIDATE | APROBADA | —            | —     | [Liberar] |
+--------------------------------------------------------------+
```

## 3. Timeline

```
[Homologación ▸ Timeline]
+--------------------------------------------------------------+
| Fecha | Tipo | Evento | Versión/Acto | Usuario              |
+--------------------------------------------------------------+
```

> Nota: los wireframes detallados (HTML/Markdown) se añadirán en la fase de implementación si aplica; la ruta documental los resume aquí.
