# GOV-CTL-04 · mutaciones de negocio (T010, herramienta de Claude `mutar_ctl04.py`)

Método:
- un SEARCH único por mutante → REPLACE;
- purga de `__pycache__` y `PYTHONDONTWRITEBYTECODE=1`;
- restauración verificada por sha256: 15/15 restaurados.

Órdenes:
- backend: `pytest tests/test_gov_ctl04_auditoria.py tests/test_gov_doc02_autoridad_historica.py` sobre PostgreSQL;
- interfaz: `vitest run` del fichero de pruebas del componente mutado.

## Resultado: 15 mutantes · 15 muertos · 0 equivalentes · 0 supervivientes

| ID | Mutación | Resultado | Prueba que lo mata |
|---|---|---|---|
| CTL-M01 | sin filtro de Gobierno (eventos privados en la población) | KILLED | GX-03 (y 2 más) |
| CTL-M02 | sin alcance de empresa en la población | KILLED | GX-03 (y 3 más) |
| CTL-M03 | el detalle admite eventos privados | KILLED | GX-06 |
| CTL-M04 | evidencia sin `safe_details` (claves no autorizadas) | KILLED | GX-05 |
| CTL-M05 | registrar muestra con la capacidad `view` | KILLED | GX-15 |
| CTL-M06 | muestra modificable (disparador sin `RAISE`) | KILLED | GX-13 |
| CTL-M07 | ALEATORIA no reproducible (generador sin semilla) | KILLED | GX-09 |
| CTL-M08 | la población ignora el filtro de proceso (exportar o muestrear sin los filtros) | KILLED | GX-04 (y 2 más) |
| CTL-M09 | CSV con método falso en la cabecera | KILLED | GX-17 (añadida en el ciclo, ver abajo) |
| CTL-M10 | ESPECÍFICA admite eventos fuera de la población | KILLED | GX-08 |
| CTL-M11 | FIND-ORG07-01: DOC-02 vuelve a validar con la competencia de hoy | KILLED | GH-01 (y 2 más) |
| CTL-M12 | registro de muestra sin puerta de capacidad (interfaz) | KILLED | REG-01 |
| CTL-M13 | enlace «Ir al objeto» sin la capacidad del destino (interfaz) | KILLED | EVI-02 |
| CTL-M14 | casillas de selección sin la capacidad `sample` (interfaz) | KILLED | AUD-02 |
| CTL-M15 | enlace al documento vinculado sin `documentos:view` (interfaz, T012) | KILLED | EVI-07 |

## Cómo se llegó a 0 supervivientes

- **CTL-M09** sobrevivió en la primera tanda. La única prueba del CSV (GX-12) exporta una muestra TODAS, y el mutante escribe precisamente «TODAS»: con esos datos no se distinguía del código bueno.
  - Se añadió GX-17, que exporta la muestra ALEATORIA y exige `# metodo: ALEATORIA` y `# semilla: 12345`. Repetido, el mutante muere.
- **CTL-M11** abortó en la primera tanda antes de escribir nada: su SEARCH no era único. Se le dio contexto y en la segunda tanda muere.
- Árbol verificado sin restos de mutantes tras ambas tandas.
