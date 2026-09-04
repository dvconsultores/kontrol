# SPEC 020 · SELLO DE EVIDENCIA POSTERIOR AL CIERRE

> 2026-09-04. Cierra la evidencia que se perdió cuando el entorno desapareció con el reinicio de la
> máquina. **No reabre la Spec funcionalmente.** Prueba el código exacto de `7dc1fe1` más el
> checkpoint documental `e2f5e81`, que no toca código.
>
> Cambios de código de producto en este sello: **0**.

## Por qué hizo falta

El checkpoint de la 020 declaró backend 920 · 912 · 8 · 0 y una e2e con 16 fallos ajenos. Dos de esas
cifras nunca se vieron completas: la regresión de backend quedó truncada al corregir el guardia
`test_n9_resourcekinds.py`, y la e2e se detuvo en 229 de 258. El sello las mide de nuevo, enteras.

## Entorno reconstruido

| Componente | Estado |
|---|---|
| PostgreSQL | **18.6** (Debian 18.6-1.pgdg12+2), puerto 55438 |
| Sockets | **solo TCP**: la ruta del socket Unix del scratchpad excede los 107 bytes que admite el sistema |
| Zona horaria del clúster | **UTC** — ver §«El único fallo de backend» |
| ClamAV | **1.4.3**, con firma mínima EICAR en `.ndb`, verificada: detecta el fichero de prueba |
| Bases | `kmc`, `kinstall`, `ke2e`, `kontrol_legacy` (sembrada con `qa/n4-legacy-hostile-seed.py`) |
| Alembic | cabeza única `0045_spec020_incidents` |
| Pila e2e | `ke2e` migrada y sembrada con `qa/pg-e2e-seed.py`; arnés N6 sobre su propia base |

## Backend

| Corrida | Total | Pasadas | Saltadas | Fallos |
|---|---:|---:|---:|---:|
| Primera (clúster en `Europe/Amsterdam`) | 920 | 911 | 8 | **1** |
| **Segunda (clúster en UTC)** | **920** | **912** | **8** | **0** |

Coincide exactamente con la línea base declarada.

### El único fallo de backend, y por qué no era uno

`test_licensing_central.py::TestSincronizacion::test_sync_success_records_run_snapshot_and_event`.

```
assert datetime(2026, 8, 4, 14, 0, tz=UTC) == datetime(2026, 8, 4, 12, 0, tz=UTC)
```

El valor guardado era `2026-08-04 14:00+02:00`, que **es** las `12:00 UTC`: el mismo instante. La
prueba compara con `state.last_reliable_date.replace(tzinfo=UTC)`, y `replace` **sobrescribe** la
zona en vez de convertir, convirtiendo `14:00+02:00` en `14:00 UTC`. Solo pasa si el clúster está en
UTC.

Mi clúster nuevo heredó la zona del sistema. El de la línea base estaba en UTC.

| Clasificación | `TEST_DEFECT` latente, revelado por `EXTERNAL_ENVIRONMENT` |
|---|---|
| Dueño | Spec 004 (licenciamiento). Ajeno a la 020 |
| Acción en este sello | **Ninguna sobre el código.** Se alineó el clúster a UTC, que es el entorno de la línea base |
| Deuda registrada | La prueba debería usar `astimezone(UTC)`. Corregirla es de su dueño, no de este sello |

## Suites dirigidas

| Suite | Casos | Resultado |
|---|---:|---|
| Spec 020 — incidencias, arquitectura y migración `0045` | 47 | **PASS** |
| Spec 019 — recepción, arquitectura y migración `0044` | 40 | **PASS** |

## Frontend

285/285 · `tsc -b` limpio · ESLint limpio · `build` correcto.

## E2E — completa, en tres navegadores

| Pila | Ejecuciones | Pasadas | Fallos |
|---|---:|---:|---:|
| Principal (14 suites × 3) | 222 | 157 | 65 |
| Arnés N6 (2 suites × 3, base propia) | 75 | **75** | **0** |
| **Total** | **297** | **232** | **65** |

Ninguna corrida truncada. Las dos suites del arnés N6 —`n6-a11y-responsive` y `n6-multicompany`—
no comparten pila con el resto: entran con el usuario `uab`, que solo existe en la base del arnés.
En la corrida principal producían 36 fallos por pila equivocada; en la suya pasan las 75.

**Corregido de la corrida anterior:** faltaba `KONTROL_E2E_USER`, y por eso 120 pruebas se saltaron
en vez de ejecutarse. Con las credenciales completas, las pasadas subieron de 83 a 157.

## Clasificación de los 65 fallos

Reproducidos contra una copia limpia del árbol anterior a la Spec 020 (`409b945`), servida en el
puerto 5174 contra el mismo backend, con las mismas credenciales.

| Clasificación | Casos |
|---|---:|
| `NEW_REGRESSION_SPEC020` | **0** |
| `PREEXISTING_REPRODUCED` | **65** |
| `EXTERNAL_ENVIRONMENT` | 36 (arnés N6 en pila ajena; pasan en la suya) + 1 (zona horaria del clúster) |
| `TEST_DEFECT` | 1 (el de zona horaria, ya descrito) |
| `UNKNOWN` | **0** |

El árbol anterior falla **77** en esas mismas siete suites; HEAD falla **65**. Es decir: la 020 no
solo no rompió nada, sino que **13 casos que fallaban antes ahora pasan**, casi todos de
accesibilidad. Es el efecto del arreglo de los quince `aria-label` que la propia 020 destapó.

Un caso —`firefox › documents.spec.ts › un formato no admitido se rechaza con un mensaje
accionable`— no apareció en la corrida de la base y sí en la de HEAD. Se comprobó por separado:
falla **2 de 2** en el árbol anterior, con el mismo error que su caso vecino (el botón «Desactivar»
que no aparece). Era preexistente e intermitente; aquella corrida lo pasó por azar. Atribuirlo sin
reproducirlo habría sido justo el defecto que este sello viene a evitar.

Dueños de los 65: Spec 046 (documentos, 31), Spec 008 (almacenes, 21), Spec 011 (unidades, 7),
Spec 045 (aprobaciones, 6).

## Aislamiento multiempresa — con prueba válida

| Evidencia usada | Por qué vale |
|---|---|
| `test_spec020_incidents.py` (24 casos) | Arnés `mundo` sobre PostgreSQL: dos tenants, tres empresas, usuarios `ua`/`ub`/`uab`/`uc`. El cruce devuelve 404, no 403 |
| `test_n9_resourcekinds.py` (`ReceiptIncident`) | Siembra una incidencia real por empresa y comprueba el vínculo documental dentro y fuera de la empresa y del tenant |

**No se usa como evidencia** el caso `approvals.spec.ts › multiempresa: no se ven solicitudes de otra
empresa`. Consulta `/approvals/inbox?company_id=empresa-inexistente` y afirma `total === 0`, pero el
endpoint no declara ese parámetro: la empresa viene del `CompanyContext`. El filtro se ignora y la
aserción pasa siempre que la bandeja esté vacía. Es un **falso verde** y está registrado como tal.
Además, hoy ni siquiera está verde: es uno de los 65 preexistentes.

## Veredicto

`SPEC 020 — COMPLETE / CONVERGED / EVIDENCE SEALED`

Regresiones nuevas: 0. Fallos inesperados: 0. `UNKNOWN`: 0. Código de producto tocado: 0.
