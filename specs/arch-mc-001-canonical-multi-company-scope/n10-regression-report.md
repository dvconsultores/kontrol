# N10 — REGRESIÓN Y AUDITORÍA DE SALTOS

## Entorno

| | |
|---|---|
| PostgreSQL | 18.6 · UTC · instalación limpia migrada a `0039` |
| ClamAV | 1.4.3 real |
| Base legada | `kontrol_legacy` sembrada con el fixture hostil en el esquema `0032` |

## Auditoría de saltos

Cada salto, con motivo, responsable y prioridad. Ninguno desconocido.

| Suite | Saltos | Motivo | Responsable | Prioridad |
|---|---:|---|---|---|
| `test_documents_storage.py` | 8 | `KONTROL_S3_ENDPOINT` sin configurar: no hay servicio S3 real en este entorno | Infraestructura | P1 externa |

**Cero saltos desconocidos. Cero P0 escondida.**

### Un salto que N10 convirtió en ejecución

Una primera pasada completa mostró **24** saltos: los 8 de S3 y otros 16 de
`test_mc_preflight.py` con el motivo «no hay base legacy sembrada en este
entorno».

Esos 16 son las pruebas del clasificador de migración de legado. No estaban
saltando por diseño sino porque el entorno efímero había perdido la base
`kontrol_legacy`. Es decir: las pruebas que verifican N4 no se estaban
ejecutando, y su ausencia se leía como un salto legítimo.

Se sembró la base y se ejecutaron. **16 de 16 pasan**, sin saltos.

Que un salto ambiental pueda esconder la verificación de una fase entera es
exactamente el tipo de cosa que §72 obliga a mirar de frente.

## El antivirus, y una decisión de entorno declarada

Las pruebas documentales invocan `clamscan` una vez por subida, y cada
invocación carga el corpus oficial completo —110 MB entre `main.cvd` y
`daily.cvd`— desde cero. Medido: entre 30 y 60 segundos por subida.

Para la pasada completa se usó un corpus reducido con la firma EICAR. **Es el
mismo binario, el mismo subproceso, los mismos códigos de salida y el mismo
análisis de salida**; lo único que cambia es cuántas firmas se cargan, y las
pruebas no afirman nada sobre cobertura de firmas: afirman que un archivo limpio
se entrega, que EICAR se rechaza y que sin analizador el resultado es
`SCAN_FAILED`.

**Y además se ejecutaron con el corpus oficial completo**, por separado, para no
apoyar la afirmación solo en el atajo:

| Prueba | Corpus oficial 110 MB |
|---|---|
| `test_archivo_limpio_se_acepta` | PASS |
| `test_archivo_infectado_se_rechaza_y_no_se_almacena` | PASS |

## Un fallo que fue del instrumento

Con el corpus reducido, `test_archivo_infectado_se_rechaza_y_no_se_almacena`
falló. La detección funcionó —`INFECTED`, subida rechazada con `422
FILE_INFECTED`, ningún binario escrito— y lo que falló fue la última aserción:
la prueba exige que el nombre de la firma contenga `Eicar`, y la firma que yo
había escrito se llamaba `EICAR-Test-Signature`.

La prueba tenía razón y el código tenía razón. El atajo del entorno estaba mal.
Se corrigió el nombre de la firma para que coincida con el oficial y se
reejecutó.

Queda escrito porque es el mismo patrón que N10 persigue: un resultado rojo que
no significaba lo que parecía significar.

## Frontend

| | |
|---|---|
| Vitest | 278 / 278 |
| `tsc -b` | limpio |
| ESLint `--max-warnings 0` | limpio |
| `npm run build` | limpio |

En una de tres ejecuciones apareció un error no reproducible en el desmontaje,
sin prueba fallida. No se reprodujo. Se registra sin presentarlo como aprobado.
