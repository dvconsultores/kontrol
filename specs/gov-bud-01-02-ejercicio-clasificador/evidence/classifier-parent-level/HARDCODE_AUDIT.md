# Auditoría de hardcode · BUD-02-CLASSIFIER-PARENT-LEVEL

**Búsqueda (§36):**
- en el diff del backend: `level`, `nivel`, `parent`, `padre`, `tipo`, `codigo` y `classifier`;
- en el diff, además: nombres de entes, ONAPRE y códigos literales de partidas;
- en `service_presupuesto.py`: comparaciones `nivel == 1`.

| Hallazgo | Clasificación | Estado |
|---|---|---|
| `NIVEL_RAIZ_PARTIDA = 1` | Raíz definida por BUD12-06 y por el CHECK `nivel BETWEEN 1 AND 12` de la base. Es un contrato del modelo, no una política del ente | Constante única, usada por la regla y por sus mensajes |
| `validar_padre_partida` | Regla estructural: mismo clasificador, mismo tipo, nivel N-1. Sin códigos, prefijos ni catálogos | Autoridad única (CLASSIFIER_PARENT_AUTHORITIES=1) |
| `nivel_orden == 1` (`service_presupuesto.py:617`) | Raíz de las categorías programáticas de BUD-01, otro árbol con su propia regla (BUD12-05). No es de este ciclo | Sin cambio |
| Códigos de partida, edición ONAPRE o nombres de entes en el código | — | Ninguno: cada ente carga su clasificador (alta o CSV) con la profundidad que necesite, hasta 12 niveles |
| Frontend | Sin cambio. «Código superior» sigue siendo texto libre y el backend es la autoridad | — |

**Resultado:** ZERO_INSTITUTIONAL_HARDCODE=1 · NATIONAL_REUSABLE_PRODUCT=1.
