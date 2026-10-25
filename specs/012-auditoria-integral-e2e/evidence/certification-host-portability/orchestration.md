# CERTIFICATION-HOST-PORTABILITY — orquestación Claude + DeepSeek (2026-10-25)

Claude diseñó, escribió los encargos, auditó, aplicó y verificó. DeepSeek escribió todo el código, las pruebas, el
fichero fijado y la documentación. Cada encargo pasó el EGRESS (0 secretos y 0 rutas del home; solo URLs públicas de
paquetes y hashes). El relevo íntegro del brief se comprobó en la traza para TP-A1 y TP-A2. Todos los parches se
aplicaron tal cual con el aplicador de una sola coincidencia; los bloques rechazados se omitieron y volvieron a DeepSeek.

| Tarea | Modelo | Resultado de auditoría | Reintentos |
|---|---|---|---|
| TP-A1 pruebas CRP (rojo) | v4-pro | PASS; después REJECT de CRP-09 (dos contextos sobre el mismo `tmp_path`) → r2 PASS | 1 |
| TP-A1-c1 vectores `GIT_*` (cambio de contrato) | v4-flash | PASS | 0 |
| TP-A1-c2 vectores git refinados + CRP-11 (CRLF) | v4-pro | PASS | 0 |
| TP-A1-c3 CRP-12/13 (filtros globales, XDG) | v4-pro | REJECT (directorio de trabajo dentro del repo o sobre un fichero) → REJECT (funciones anidadas) → r2 PASS | 2 |
| TP-A2 pruebas CRQ (rojo) | v4-pro | REJECT (D1 `writestr` con el modo como compresión, D2 cabecera `ar` de 48 bytes, D3 directorio no creado, D4 aserción vacua, D5 elección del artefacto, D6/D7 firmas de dobles —contrato de Claude—, D8 sin `.venv` señuelo, D9 ruff) → r1 PASS → REJECT (`.completo` en el directorio equivocado, espacio `RUN1`) → r2 PASS | 2 |
| TP-1 perfil E2E | v4-pro | PASS (faltaba `"perfil"` en el retorno: el brief no citaba esa línea, error de Claude) | 0 |
| TP-1-c1 `"perfil"` en el retorno | v4-flash | junto con TP-3a-c1 | — |
| TP-2 política de entorno | v4-pro | PASS | 0 |
| TP-2-c1 política git refinada (medido: `GIT_EDITOR`) | v4-flash | PASS | 0 |
| TP-3a fuente fijada + descarga/extracción | v4-pro | PASS | 0 |
| TP-3a-c1 rechazo de `..` (contrato de Claude) + TP-1-c1 | v4-flash | REJECT (formato sin marcadores) → r1 PASS | 1 |
| TP-3a-c2 mypy `extractfile` | v4-flash | PASS | 0 |
| TP-3b etapa, preflight, `pg-provision.sh` | v4-pro | 9/10 PASS; bloque D REJECT (línea en blanco inexistente) → r1 PASS | 1 |
| TP-4 árbol certificado + hash v2 | v4-pro | PASS | 0 |
| TP-4-c1 neutralizar la configuración git | v4-pro | REJECT (SEARCH con la constante nueva; bloques sin ruta) → r1 5/6 PASS; bloque 2 REJECT (el brief daba por contiguas dos líneas, error de Claude) → r2 PASS | 2 |
| TP-4-c2 `excludesFile`/`attributesFile` | v4-flash | PASS | 0 |
| TP-5 ajuste de CRE-10/26/30/32 + F841 | v4-pro | 6/7 PASS; bloque 7 REJECT (fragmento cortado por Claude) → r1 PASS | 1 |
| TP-6 documentación | v4-flash | PASS | 0 |
| TP-5b AIC-01 (literales `.venv` en CRQ, hallado en la suite PostgreSQL) | v4-pro | 3/5 PASS; bloques 4 y 5 REJECT (variable `script` inexistente; SEARCH `parents[2]`, línea que Claude no citó) → r1 PASS | 1 |

**Totales:**
- 29 llamadas;
- 49187 tokens de entrada y 50467 de salida, **$0.0613**;
- 11 rechazos y 11 reintentos (máximo 2 por subtarea, nunca superado);
- Claude escribió 0 líneas de producto, pruebas o QA del repositorio.

Herramientas de Claude, fuera del repositorio y en el scratchpad:
- el aplicador;
- el muestreador de memoria;
- el ejecutor de mutaciones.

Cinco rechazos se debieron a errores de contrato de Claude (TP-1, TP-3a-c1, TP-4-c1 bloque 2, TP-5 bloque 7, TP-5b bloque 5), y se registran como tales.

Hallazgos de diseño durante la implementación, medidos y no supuestos:
- La estación no tiene `gcc` ni `make`: se descartó compilar `btree_gist`.
- El preflight real rechazó `GIT_EDITOR` por el prefijo amplio `GIT_`: se refinó la política.
- La configuración git del anfitrión cambia el árbol (`core.autocrlf`, filtros `clean` globales, `git/ignore` y `git/attributes` de XDG): se neutralizó y lo prueban CRP-11, CRP-12 y CRP-13.
- El primer conjunto de mutaciones dejó vivo P25: hacía falta CRP-12.
