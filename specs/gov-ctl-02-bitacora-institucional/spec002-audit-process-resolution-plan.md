# Plan · CTL-02-AUDIT-PROCESS-RESOLUTION

## Constitution gate

- P2: la autorización de implement es la del encargo, que nombra la iniciativa.
- Sin migración, sin cambios de seguridad ni de permisos y sin datos reales.
- La única decisión material (el alcance de CTL-04) la resolvió la dueña (OD-PR-01).
- **Resultado:** PASS.

## Contrato

```python
# app/modules/government/procesos.py
MODULOS: tuple[ModuloGobierno, ...]          # codigo, nombre
PROCESOS: tuple[ProcesoGobierno, ...]        # codigo, nombre, owner_specs; .modulo = prefijo
resolver_proceso(action, entity_type) -> ProcesoResuelto
    # clase: PROCESS_EVENT | AUTH_EVENT | PLATFORM_EVENT | SYSTEM_EVENT
    # codigo, nombre, modulo, modulo_nombre: str | None
    # fuente: CATALOGO_DE_EVENTOS | SIN_REGISTRO
es_proceso(codigo) -> bool                   # validación de filtros (CTL-04)
nombre_de(codigo) -> str | None
owner_specs_de(codigo) -> tuple[str, ...]
proceso_de_owner_spec(owner_spec) -> ProcesoGobierno | None
```

- **API de la bitácora:** `BitacoraEvento.modulo` y `BitacoraEvento.modulo_nombre`, opcionales.

## Cambios

1. `procesos.py`, nuevo: el registro de los 39 procesos y la función de resolución.
2. `service_auditoria.py`: se elimina `PROCESOS`. `_proceso_de`, el orden de las acciones, la condición de proceso, la validación del filtro y el catálogo de filtros pasan a la autoridad.
3. `service_bitacora.py` y `schemas_bitacora.py`: `_resumen` resuelve con la autoridad y expone el módulo. `ACCIONES_AUTENTICACION` pasa a la autoridad.
4. `service_sod_eventos.py`, `service_reporte_control.py`, `service_rendicion.py` y `api_rendicion.py`: nombres y lista de procesos desde la autoridad.
5. Frontend: el tipo `BitacoraEvento`, la línea «Módulo · Proceso» de la lista y la fila «Módulo» del detalle.
6. Pruebas:
   - `test_gov_ctl02_procesos.py`;
   - GX02 de CTL-04 compara contra la autoridad;
   - Vitest `BitacoraProcesoModulo.test.tsx`;
   - E2E `gobierno-bitacora-procesos.spec.ts`.

## Riesgos

- **Cambio de contrato esperado:** el catálogo de filtros de CTL-04 pasa de 19 a 39 procesos (GX02).
- **Nombres de proceso nuevos visibles para la dueña:** se revisan en la tarjeta UAT.
