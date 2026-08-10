# Spec 012 — Plan de Pruebas (test-plan.md)

## Pruebas ejecutadas en esta pasada
| Prueba | Tipo | Resultado |
|---|---|---|
| `pytest` backend | Unit/integración | 190 ✔ |
| `vitest` frontend | Unit | 16 ✔ |
| `tsc -b` / `eslint` | Estático | ✔ |
| Menú→ruta→página→API (script) | Completitud | 51/53 menú, 57/57 rutas, 135/135 API |
| Reproducciones E2E (empresa/sucursal/almacén) | Integración | 200 ✔ |

## Pruebas permanentes a incorporar (puertas, T-08..T-11)
1. **Gate 1/2** — test que falle si el menú referencia una ruta no declarada o una página inexistente (evita el patrón Sucursales).
2. **Gate 3/4** — test que falle si una página llama un endpoint que no existe en OpenAPI (contract).
3. **Gate 6** — E2E de procesos críticos (Playwright): Org completo, Ventas, Compras, Fiscal (emitir→consultar→editar).
4. **Crawler de rutas** — login QA → recorrer menú → sin 404/500/errores de consola (no destructivo).

## Pruebas pendientes (ambiente autorizado)
- Navegadores reales (Safari/Opera/Samsung) + responsive + axe.
- Seguridad (OWASP, tenant isolation, IDOR) en ambiente controlado.
- Backup→restore real; rendimiento con dataset grande.
- Fiscal normativa + inmutabilidad de documentos.
