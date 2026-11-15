# Tarjeta de prueba de la dueña · TRE-09 Tasas oficiales BCV (GOV-TRE-011)

**Dónde:** Menú › Gobierno · Tesorería › **Tasas oficiales**. El consumidor está en Gobierno · Presupuesto › Ejercicios presupuestarios › (ejercicio aprobado) › «Compromisos».

**Qué probar:**
1. Registre una tasa: moneda USD, fecha efectiva, valor (p. ej. 905,12345678), referencia oficial del BCV. Queda en **Borrador**.
2. En «Ver …», adjunte la evidencia del BCV (documento) en «Evidencia oficial del BCV».
3. Intente aprobarla con el mismo usuario: el sistema lo impide (quien captura no aprueba). Apruébela con otro usuario que tenga `gobierno_tasas:approve`; se le pedirá MFA.
4. Compruebe en la tabla «1 USD = … VES», la fuente BCV, la versión, quién capturó y quién aprobó; en el detalle, la huella de la evidencia y la historia de versiones.
5. Corrija la tasa con «Corregir con una nueva versión» (valor, referencia y motivo) y apruébela con otro usuario: la anterior queda **Sustituida** y la historia muestra las dos versiones.
6. En un ejercicio aprobado, registre un compromiso con una autoridad cuyo límite esté en USD. Antes de confirmar verá:
   - la moneda de la operación y la del límite;
   - la **tasa oficial utilizada**, su fecha y su fuente;
   - el resultado de la comparación en VES.

   Al registrarlo, la tabla y el PDF conservan esa tasa.
7. Anule la tasa (con motivo) e intente otro compromiso con esa autoridad: queda **bloqueado** con el aviso «No hay tasa oficial BCV aprobada…».

**Reglas que verá aplicadas:**
- VES es el código canónico. Un ejercicio heredado en VED se compara 1:1, sin tasa.
- Los ejercicios nuevos guardan VES.
- No se elige la tasa a mano: se usa la aprobada más reciente con fecha efectiva menor o igual a la fecha de la operación.
- Una operación registrada nunca se recalcula.

**Fuera de este ciclo:** integración con PROC-08 y CNT-01 (DEFERRED), captura automática desde el sitio del BCV y reportes (NOT_APPLICABLE).

OWNER_ACCEPTED = NO (solo la dueña lo concede).
