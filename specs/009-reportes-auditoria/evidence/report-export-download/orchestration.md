# REPORT / EXPORT DOWNLOAD — orquestación Claude + DeepSeek (2026-10-27)

**Reparto del trabajo.**

Claude:
- descubrió y midió: la matriz de descargas, el transporte, el contrato y la causa raíz;
- re-diagnosticó las tres causas que los reintentos no resolvían: la colisión de nombres, el remontaje por `flexRender` y el mock de autoridad inestable;
- diseñó, escribió los encargos y pasó el EGRESS antes de cada llamada;
- auditó en copia, aplicó tal cual y verificó.

DeepSeek escribió todo el código de producto, todas las pruebas (vitest, pytest y E2E) y la documentación del contrato. **Implementadas por Claude: 0.**

| Tarea | Contenido | Modelo | Auditoría | Reintentos |
|---|---|---|---|---|
| D-T01 | E2E DOWNLOAD-E2E-01..09 en rojo | pro / flash | c0: falta el import de `readFileSync` → r1 PASS | 1 |
| D-T02 | `responseType: "archivo"` + `src/api/descargas.ts` + DESC-01..09 | pro / flash | Cliente y pruebas PASS; módulo c0 con `eslint-disable` → r1 PASS | 1 |
| D-T03 | Exportaciones con la primitiva | pro / flash | c0: dos `=======` por bloque y una línea redundante → r1 PASS; r2: EXP-06 sigue fallando → agotada, **reclasificada** en D-T09 tras re-diagnóstico | 2 + reclasificación |
| D-T04 | El Centro entrega el archivo | pro | Producto PASS; prueba c0 (`await` en función no async, POST sin simular, `.click()`) → r1 PASS | 1 |
| D-T05 | Nombre de exportación único (EXPORT-FILE-NAME-COLLISION) + prueba con reloj congelado | pro | PASS (rojo atribuible antes de aplicar el producto) | 0 |
| D-T06 | E2E: buscar la fila paginando + patrón de nombre nuevo | pro | PASS | 0 |
| D-T07 | Guardas de arquitectura (`blob`/`archivo`; ninguna URL `/api/v1/` fuera del cliente) | flash | PASS | 0 |
| D-T08 | Contrato de la descarga (Spec 009) | flash | PASS. **Claude lo rechazó por error**: confundió el escapado JSON con barras literales. El reintento salió idéntico y se descartó | 1 (descartado) |
| D-T09 | Botón estable (`BotonDescarga`, `useCallback`, `useMemo`) + EXP-06/07 | pro | PASS | 0 |
| D-T10 | ARCH-01..03 del cliente | pro / flash | c0: `unknown` sin tipo y `.text()` en jsdom → r1: Blob de jsdom en `Response` (**el encargo de Claude** pedía Blob) → r2 PASS | 2 |
| D-T11 | FOCO-01 con proveedor real | pro / flash | c0: `ApiError` inventado, import sin uso y docstring ajeno → r1: el proveedor no pinta avisos (**el encargo de Claude**) → r2 PASS de formato, pero la prueba fallaba sin mutación → agotada, **reclasificada** en D-T12 | 2 + reclasificación |
| D-T12 | Mock de autoridad estable (`vi.hoisted`) | flash | PASS | 0 |

**Coste del ciclo:**
- 22 llamadas (13 pro, 9 flash);
- 62 712 tokens de entrada y 40 023 de salida;
- **0,0513 USD**;
- todas terminaron en `stop`.

Además hubo dos delegaciones que el ejecutor rechazó sin llamar a DeepSeek. Claude las lanzó antes de que su encargo existiera en disco. Lección: un encargo se escribe y se verifica ANTES de lanzar su delegación, nunca en la misma tanda.

**Rechazos (AUDIT_REJECT): 11.** D-T01 1, D-T02 1, D-T03 2, D-T04 1, D-T08 1, D-T10 2 y D-T11 3; el último de D-T11, sobre la prueba en base, se resolvió con la reclasificación.
- **Atribuibles a Claude: 4.** D-T08 (rechazo erróneo), D-T10 r1 (Blob en el encargo), D-T11 r1 (proveedor sin visor) y D-T06, que nace de un encargo de E2E que suponía la fila en la primera página.
- **Reclasificaciones tras agotar reintentos: 2** (D-T03 → D-T09, D-T11 → D-T12), las dos con causa raíz medida por Claude.

**EGRESS.** EGRESS_OK antes de cada llamada. Ningún encargo llevó tokens reales, contraseñas, rutas personales ni datos reales: las palabras «Bearer» y «Authorization» aparecen como texto a buscar, y el token de las pruebas es ficticio («tok-prueba»).

**Lecciones:**
- Probar contra `flexRender`: una columna `cell` reconstruida en cada render es un componente nuevo y remonta la celda.
- Para probar estabilidad de foco, el mock del contexto debe ser tan estable como el real, y la prueba debe pintar el visor de avisos real.
- En jsdom, `new Response(new Blob(...))` convierte el Blob en texto; los cuerpos de prueba van como texto.
- Un nombre de archivo con resolución de segundos, en un directorio común, es una fuga entre empresas.
