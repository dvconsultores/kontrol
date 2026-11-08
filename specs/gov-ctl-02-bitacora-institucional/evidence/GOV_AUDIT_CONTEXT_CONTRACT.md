# GOV_AUDIT_CONTEXT_CONTRACT

Columnas de `audit_events` que responden a GOV-CTL-003:

| Dato | Dónde | Regla |
|---|---|---|
| Autor técnico | `user_id` | Existente |
| Sesión | `session_id` | Para eventos de Gobierno, de la sesión viva de la petición |
| IP | `ip` | Para eventos de Gobierno, del cliente de la petición |
| Instante | `event_time` | Existente |
| Correlación | `request_id` | Existente |
| Ente | `company_id` y `institutional_context.ente` | Existente, más nombre |
| Actor efectivo | `institutional_context.funcionario` | Sin documento |
| Cargo, unidad, figura, ejerce | `institutional_context.ocupaciones[]` | Todas las vigentes a la fecha |
| Autoridad | `ocupaciones[].autoridad[]` | Acción y materia |
| Rol y categoría | `institutional_context.roles[]`, `.categorias[]` | A la fecha |

```
institutional_context = NULL            evento no de Gobierno, sin usuario o sin ente, o anterior a CTL-02
{
  "version": 1,
  "estado": "CON_IDENTIDAD" | "SIN_VINCULO",
  "fecha": "AAAA-MM-DD",
  "ente": {"id", "nombre"} | null,
  "vinculo": {"id", "codigo"} | null,
  "funcionario": {"id", "nombre"} | null,
  "ocupaciones": [{"cargo_id", "cargo", "cargo_codigo", "unidad_id", "unidad", "figura", "figura_etiqueta", "ejerce", "autoridad": [{"accion", "materia"}]}],
  "roles": [{"id", "codigo", "nombre"}],
  "categorias": ["..."],
  "tiene_autoridad": bool,
  "motivo_sin_autoridad": str | null
}
```

**Clasificación de eventos.** `BUSINESS_COMMIT` → ÉXITO, `REJECTION` → RECHAZO, `SECURITY_DENIAL` → DENEGACIÓN, según el catálogo cerrado. Gobierno: 104 confirmaciones y 3 rechazos, además de los eventos de autenticación.

**Consultas sensibles.** Actos, cargos, estructura, matriz de autoridad, notificaciones, hallazgos, asignaciones, vínculos, muestra y paquete: 10 salidas de datos, todas con evento propio. No se audita cada GET.
