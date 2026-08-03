# WF-09 — Solo Consulta (Modo READ_ONLY)

Patrón de estado de licencia solo consulta (DOC-08 §6, DOC-07).

```text
┌──────────────────────────────────────────────────────────────┐
│ [BANNER: KONTROL está en modo solo consulta · Mi licencia]    │
├──────────────────────────────────────────────────────────────┤
│ Consulta, búsqueda, navegación, reportes y exportación: OK    │
├──────────────────────────────────────────────────────────────┤
│ Botones de escritura deshabilitados con motivo y enlace       │
│ a Mi licencia                                                 │
└──────────────────────────────────────────────────────────────┘
```

Reglas: en READ_ONLY se permite consulta, reportes, exportación autorizada y reimpresión controlada; se bloquea toda escritura en backend, jobs e integraciones; el banner es persistente mientras exista aviso; la pantalla Mi licencia permite cargar comprobante.
