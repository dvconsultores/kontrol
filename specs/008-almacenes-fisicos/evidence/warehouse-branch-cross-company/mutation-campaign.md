# Mutaciones (GOOD→PASS · MUTATED→FAIL · RESTORED→PASS; juego: branch_scope + integrity + structure; SQLite **y** PostgreSQL)
| Id | Mutación | Resultado |
|---|---|---|
| M01 | sin validación en el alta | KILLED (B-02/03/04/12/15, O01-06) |
| M02 | sin validación en el PATCH | KILLED (B-07/08/15) |
| M03 | compara el tenant en vez de la empresa | KILLED (B-02/04/07/12/15) |
| M04 | solo comprueba que exista | KILLED |
| M05 | comparación invertida | KILLED |
| M06 | código distinto | KILLED |
| M07 | mensaje distinto | KILLED (B-02/04, O01-06) |
| M08 | ajena e inexistente distinguibles (oráculo) | KILLED |
| M09 | `null` rechazado | KILLED |
| M10 | el PATCH valida siempre (sin `model_fields_set`) | KILLED (B-15) |
| M11 | el PATCH valida después de mutar | KILLED (B-15 orden; superviviente en la primera pasada → B02b) |
| M12 | el alta valida antes de `COMPANY_NOT_FOUND` | KILLED (B-16; superviviente en la primera pasada → B02b) |
MEANINGFUL 12 · KILLED 12 · SURVIVED 0 · EQUIVALENT 0 · RESTORED 100 % (fichero idéntico a GOOD).
Se revalidó la campaña de OBS-01 sobre el producto final: 15 KILLED, 1 EQUIVALENT (M11, la misma justificación) y restauración
idéntica. M02 de OBS-01 sigue muerta por O01-14.
