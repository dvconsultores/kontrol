# ORG-06 · Plan

## Datos (migración `0077_gov_org06_identidad`, sobre 0076, único head público)
Tablas del `ORG06_FIELD_CONTRACT`. Exclusiones `ex_gov_links_cuenta` y `ex_gov_links_funcionario`; `ex_gov_role_categories`. Disparadores: historia inmutable y vínculos no borrables. Proceso SoD `ORG-06`.

## Capacidades
`gobierno_identidad`: view, manage; activate y revoke con MFA.

## API `/gobierno/identidad`
catalogo, opciones, vinculos (lista, CSV, alta, detalle, edición), activar, descartar, cerrar, revocar, mi-contexto, categorias (lista, alta, retirar), conflictos, politica.

## Servicios
`service_identidad.py` nuevo. `service_sod.py`: `usuarios_equivalentes`, `conflictos_de_categorias`, proceso ORG-06. `service_ocupacion.py`: `ocupaciones_de_funcionario` y maker-checker por actor efectivo. `service_actos.py`: guarda al emitir.

## Frontend
Módulo `gobierno/identidad/`: `VinculosPage`, `NuevoVinculoPage`, `VinculoPage`, `CategoriasPage`, `MiContextoPage`.

## Constitución

| Gate | Resultado |
|---|---|
| Rama única y origin | PASS |
| Claude no escribe código; DeepSeek secuencial | PASS |
| Núcleo compartido sin cambio semántico; solo registros | PASS |
| Egress | PASS |
| Completitud de producto | Exigida |
