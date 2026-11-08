# COMMISSION_STATE_CONTRACT

Ni la ley ni la Ingeniería de Requerimientos fijan una máquina de estados para la comisión. Estos estados solo expresan lo que las fuentes distinguen: una comisión se conforma, se designa por acto y cesa.

| Estado | Significado | Fuente | Se llega por |
|---|---|---|---|
| BORRADOR | En preparación; aún sin efecto | Conformación previa al acto, LCP art. 14 | Registrar |
| VIGENTE | Designada por acto eficaz y publicado | LCP art. 14; RLCP art. 15 | Activar, MFA, otra persona |
| CERRADA | Cesó por fecha o decisión | «permanentes o temporales», LCP art. 14 | Cerrar, MFA |
| DESCARTADA | Borrador abandonado | Sin efecto jurídico | Descartar |

**Situación, calculada a una fecha, no guardada:** FUTURA, EN_VIGOR, VENCIDA (temporal cuya fecha final ya pasó y sigue sin cerrar), CERRADA, BORRADOR, DESCARTADA.

**Inhibición:** DECLARADA → ACEPTADA | RECHAZADA. Fuente: RLCP arts. 18 y 21.3.
