# D4 · Persistencia entre sesiones
A termina normalmente (rc 0); B es un proceso nuevo.
| Registro | Valor |
|---|---|
| Marcador de A existe tras terminar A | sí |
| B ve el marcador de A | sí |
| `CROSS_RUN_PERSISTENCE` | **YES** |
| Lo exige algún contrato funcional | **NO** (`cleanup-contract.md`: nadie limpia y nadie depende de que sobreviva) |
