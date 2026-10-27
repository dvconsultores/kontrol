# REPORT / EXPORT DOWNLOAD · Mutaciones (2026-10-27)

Herramientas de Claude fuera del árbol (`scratchpad/tools/mutaciones_descarga_ui.py` y `mutaciones_descarga.py`):
- **Frontend:** reemplazo exacto con una sola coincidencia, vitest sobre `src/api`, `src/modules/reportes` y `src/tests`, restauración byte a byte y 0 `.bak`.
- **Backend:** el mismo procedimiento con huella SHA-256, en PostgreSQL de QA y con `PYTHONDONTWRITEBYTECODE=1`.

| TOTAL | KILLED | EQUIVALENT | BEHAVIORALLY_SURVIVING | INVALID |
|---|---|---|---|---|
| 12 | 11 | 1 (U10) | **0** | 0 |

| Mutante | Qué rompe | 1.ª corrida | Final | Prueba que lo mata |
|---|---|---|---|---|
| U01 | No revoca la URL de objeto | MUERTO | MUERTO | DESC-08 |
| U02 | Confía en el nombre sin sanear | MUERTO | MUERTO | DESC-03/04/05/06 |
| U03 | Ignora `Content-Disposition` | MUERTO | MUERTO | DESC-08 |
| U04 | Guarda la respuesta de error como archivo | **SOBREVIVE** | MUERTO | **nueva** ARCH-03 (D-T10) |
| U05 | Descarga sin `Authorization` | **SOBREVIVE** | MUERTO | **nueva** ARCH-02 (D-T10) |
| U06 | Descarga sin contexto de empresa | MUERTO | MUERTO | arquitectura «el cliente central resuelve la empresa» |
| U07 | Anuncia éxito aunque falle la descarga | MUERTO | MUERTO | EXP-05 |
| U08 | El Centro no entrega el archivo tras crear | MUERTO | MUERTO | CR-05, CR-07 |
| U09 | El botón no se bloquea durante la descarga | MUERTO | MUERTO | EXP-06 |
| U10 | Sin la guarda de doble clic | SOBREVIVE | **EQUIVALENTE** | §2 |
| U11 | El botón se vuelve a montar (columnas sin memorizar) | **SOBREVIVE** | MUERTO | **nueva** FOCO-01 (D-T11/D-T12), con el `NotificationProvider` real |
| K01 | Nombre de exportación sin sufijo único (colisión entre empresas) | MUERTO | MUERTO | `test_exportaciones_del_mismo_segundo_no_comparten_archivo` |

**Validez.** Las muertes finales de U04, U05 y U11 se midieron con todas las pruebas verdes sin mutación: 8/8 en Exportaciones, en tres corridas, y 21/21 en el cliente.

Una corrida intermedia mató U10 y U11 solo porque FOCO-01 fallaba sin mutación: el mock de autoridad devolvía un `puede` nuevo en cada render. Esa corrida **se descartó**; una prueba que siempre falla no mata nada.

## 2. U10, equivalente

**Mutación exacta.** En `BotonDescarga` se quita `if (ocupado) return;`.

**Por qué el comportamiento externo es idéntico.** Mientras `ocupado` es verdadero, el botón está `disabled`, y React no despacha `onClick` en un botón deshabilitado. El segundo clic nunca llega a `pulsar`, haya o no guarda.

**Control independiente.** `disabled={ocupado}`. Su propio mutante, U09 (`disabled={false}`), muere con EXP-06.

**Evidencia.** Con U10, EXP-06 sigue viendo una sola llamada a `descargarArchivo`.

## 3. Regresión

Los cambios del ciclo están en el cliente, la página de Exportaciones, el Centro y el nombre del archivo de exportación. No tocan la autorización del backend ni la resolución de autoridad de la UI. La certificación de 02D (91 mutantes: 89 muertos, 2 equivalentes, 0 supervivientes) se mantiene. Su regresión funcional va por las suites completas y las E2E de alcance, lecturas y UI-SCOPE.
