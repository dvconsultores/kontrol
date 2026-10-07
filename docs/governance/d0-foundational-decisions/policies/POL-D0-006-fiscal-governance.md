# POL-D0-006 — Gobierno fiscal

> Deriva de `ADR-D0-007`. Vinculante para las Specs 014, 039, 040, 041, 042, 043, 056.

## 1. Frontera

El equipo de software decide **el mecanismo**. El profesional tributario decide **el contenido**.
Ningún rol invade al otro.

## 2. Prohibiciones

Ninguna alícuota, porcentaje, unidad tributaria, concepto, mínimo, sustraendo, plazo ni fecha fiscal
puede existir en código, migración, seed o valor por defecto. Todos son **datos** de
`TaxRuleVersion` con fuente legal, Gaceta, artículo, vigencia desde/hasta, versión y estado.

## 3. Ciclo de vida de una regla

```
LEGAL_VALIDATION_REQUIRED ──(profesional identificado)──► VALIDATED ──(vigencia cerrada)──► SUPERSEDED
```

- Toda regla nace en `LEGAL_VALIDATION_REQUIRED`.
- La promoción a `VALIDATED` queda auditada: quién, cuándo, contra qué fuente.
- **No se puede emitir** un documento fiscal aplicando una regla que no esté `VALIDATED` y vigente.
  No hay modo permisivo en producción.
- Una regla derogada no se borra ni se reescribe: se cierra su vigencia. Los documentos emitidos bajo
  ella conservan su snapshot (P4, P5).

## 4. Declaraciones prohibidas

Está prohibido afirmar «KONTROL cumple SENIAT» u «homologado». La homologación del software bajo SNAT/2024/000121 fue derogada (SNAT/2026/00084, G.O. N.º 43.435, 12-08-2026); lo que la Spec 056 produce es una validación de cumplimiento fiscal con evidencia, y así se declara.
Aplica a interfaz, documentación, material comercial y respuestas del producto.

## 5. Organismos externos

KONTROL no fabrica permisos, guías ni certificados (P20). Registra, valida, adjunta y bloquea según
el documento oficial. La integración automática solo se habilita mediante convenio o API oficial
aprobada.

## 6. Pendiente

**LEGAL_VALIDATION_REQUIRED** — las 24 reglas de `D0-fiscal-validation-matrix.md`.
Ninguna puede resolverla el equipo de software.
