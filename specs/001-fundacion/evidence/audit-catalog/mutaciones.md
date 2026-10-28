# Mutaciones del ciclo 04 (catálogo de auditoría)

**Procedimiento.** Herramienta `tools/mutaciones_auditoria.py`:
- cada mutación es un reemplazo exacto y único;
- pytest dirigido en PostgreSQL y SQLite (muere si cae en cualquiera de los dos) y vitest dirigido;
- `__pycache__` se purga y el fichero se restaura byte a byte, comprobándolo.

| Mutante | Estado | Matada por |
|---|---|---|
| A01 `record_audit` sin validar el catálogo | MUERTO | REC-01 |
| A02 par desconocido aceptado | MUERTO | CAT-02 |
| A03 evento LEGACY emitible | MUERTO | CAT-03 |
| A04 evento de empresa sin empresa | MUERTO | CAT-04 |
| A05 evento de tenant con empresa | MUERTO | CAT-05 |
| A06 detalle con claves libres | MUERTO | CAT-07 |
| A07 `token` permitido en el detalle | MUERTO | CAT-08[token] |
| A08 sin correlación automática | MUERTO | REC-07 |
| A09 frontera de rechazo sin commit | MUERTO | SCAN-01 |
| A10 se omite el evento de rechazo | MUERTO | SCAN-01 |
| A11 la firma de la amenaza vuelve a la respuesta | MUERTO | SCAN-01 |
| A12 sin trigger de `UPDATE` (PG) | MUERTO | IMM-01 |
| A13 sin trigger de `DELETE` (PG) | MUERTO | IMM-02 |
| A14 sin trigger de `UPDATE` (SQLite) | MUERTO | IMM-01 (SQLite) |
| A15 sin trigger de `DELETE` (SQLite) | MUERTO | IMM-02 (SQLite) |
| A16 eventos de tenant para cualquier auditor | MUERTO | AF-05 |
| A17 el filtro `company_id` se ignora | MUERTO | AF-04 |
| A18 `hasta` incluye el inicio del día siguiente | MUERTO | AF-01 |
| A19 `desde` con el día UTC | MUERTO | AF-01 |
| A20 orden de desempate invertido | MUERTO | AF-09 |
| A21 documentos vuelven a emitir sin empresa | MUERTO | CTX-01 |
| A22 lectura sin proyección segura | MUERTO | AF-07 |
| F01 caída del analizador anunciada como malware | MUERTO | documentos.test |
| F02 la pantalla vuelve a enviar `q` | MUERTO | FIL-05 y ENV-01 |

**TOTAL 24 · KILLED 24 · EQUIVALENT 0 · BEHAVIORAL 0 · INVALID 0.**

Las campañas anteriores se informan por separado y no se suman:

| Campaña | TOTAL | KILLED | EQUIVALENT | BEHAVIORAL |
|---|---|---|---|---|
| 02D | 91 | 89 | 2 | 0 |
| 02E | 12 | 11 | 1 | 0 |
| 03 | 35 | 35 | 0 | 0 |
