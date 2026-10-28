# BUSINESS CIVIL DATE (03) — orquestación Claude + DeepSeek (2026-10-28)

**Reparto del trabajo.**

Claude:
- midió OBS-TIME-01, tzdata en V6R (capa OCI verificada por digest) y los inventarios temporales (AST del backend, barrido del frontend);
- encargó y verificó la investigación normativa con fuentes primarias;
- diseñó el modelo (ADR-020) y escribió los encargos, pasando el EGRESS antes de cada llamada;
- auditó cada parche, aplicó tal cual y midió rojo y verde;
- escribió ADR-020, el delta y la evidencia, que son artefactos de diseño.

DeepSeek escribió todo el código de producto, todas las pruebas (pytest, vitest y Playwright), la prueba del arnés de QA y la documentación de contratos. **Implementadas por Claude: 0.**

Retoques de formato automáticos, permitidos por OD-ORCH-01:
- `ruff --fix` en `test_business_civil_date_documents.py` (orden de imports, I001);
- `ruff --fix` en `test_business_civil_date_reports.py` (import sin uso, F401).

| Tarea | Contenido | Modelo | Auditoría | Reintentos |
|---|---|---|---|---|
| C03-T01 | Núcleo backend: zona constante, límites, período, validador de configuración | pro, pro, flash | c0: aserción vacía en VECTOR-03 (`not (a <= b < b)`) → r1 PASS; la prueba de diciembre detectó `fin_mes = 12` → r2 PASS | 2 |
| C03-T02 | Tasas en Caracas y normalización a UTC | pro (1 transporte + 2) | La primera llamada llegó con `rates.py` recortado por el puente y sin bloques (fallo de transporte, aparte); c0: try/except muerto y sin cobertura SQLite → r1 PASS | 1 (+1 transporte) |
| C03-T03 | Costura `instante_actual()` + vencimiento documental | flash | PASS | 0 |
| C03-T04 | Estado de cuenta en fecha de negocio | pro | c0: helper no literal con `datetime.now(UTC).date()` y E402 → r1 PASS | 1 |
| C03-T05 | Sesión de PostgreSQL en UTC + invariancia | pro | PASS | 0 |
| C03-T06 | Período del reporte gerencial y declaración en libros fiscales | pro | PASS | 0 |
| C03-T06b | Adaptación de `test_export_auditada` (antes pasaba porque el período se ignoraba) | flash | PASS | 0 |
| C03-T07 | Resumen de la suite con salto de reloj | flash | c0: SEARCH sin coincidencia (el puente envió un extracto sin una línea) → r1 PASS | 1 |
| C03-T08 | Núcleo frontend | pro, pro, flash | c0 contradecía DATE-13 (**el encargo de Claude**) y DATE-03 consagraba la zona del navegador → r1: tipos sin estrechar (tsc) → r2 PASS | 2 |
| C03-T09 | 14 pantallas `toLocale*` → Caracas | flash | PASS | 0 |
| C03-T10 | 8 pantallas `slice(0, 10)` → día de Caracas | flash | PASS | 0 |
| C03-T11 | 8 pantallas con hora cortada o ISO crudo → formateador central | flash | PASS | 0 |
| C03-T13 | Entradas de Delegaciones, Tasas y Recepciones | pro | PASS | 0 |
| C03-T14 | Período en el Centro y aviso en Libros | pro | PASS | 0 |
| C03-T15 | Guarda de arquitectura temporal | flash | c0: la segunda prueba nunca encontraba el módulo y la lista blanca no casaba → r1 PASS | 1 |
| C03-T16 | BUSINESS-DATE-E2E + adaptación de `auditoria-fecha` | pro, pro, flash | c0: no compilaba y comparaba con una consulta filtrada (**en parte, el encargo de Claude**) → r1: 2 símbolos sin uso → r2 PASS | 2 |
| C03-T17 | Contratos de API de 009, 007 y 006 | flash | PASS | 0 |

**Coste del ciclo:**
- 28 llamadas facturadas (15 pro, 13 flash);
- 146 050 tokens de entrada y 68 071 de salida;
- **0,0920 USD**.

Una llamada adicional (T02, la primera del puente relanzado) falló en la validación de entrada antes de llegar al modelo y no se facturó.

**Reintentos semánticos: 10. Rechazos: 10. Fallos de transporte: 1. Tareas que agotaron 2 reintentos: T01, T08 y T16, todas en verde al final.**

Atribuibles a Claude, 3:
- T08 c0: el encargo pedía «—» para valores inválidos, contra la decisión DATE-13;
- T02 c0, en parte: el encargo no pedía cobertura SQLite;
- T16 c0, en parte: el encargo indicaba la consulta filtrada.

También de Claude: no vio en la auditoría de T01 r1 el defecto de diciembre (lo cazó la prueba) y aplicó por error un bloque de producto junto a las pruebas en T14, de modo que el rojo de LIB-01 no se midió.

**EGRESS.** EGRESS_OK antes de cada llamada. Ningún encargo llevó tokens, contraseñas, rutas personales ni datos reales. Las fuentes normativas citadas son públicas.

**Lecciones (guardadas en memoria):**
- pedir al puente los ficheros íntegros o tramos con líneas exactas: los extractos reconstruidos omiten líneas;
- buscar aserciones vacías del tipo `not (a <= b < b)`;
- antes de redactar un encargo, comprobar que no contradice una decisión ratificada de un delta anterior (DATE-13).
