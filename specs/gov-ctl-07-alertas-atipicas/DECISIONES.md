# CTL-07 · Decisiones

`MATERIAL_DECISION_REQUIRED=0`. Son decisiones de diseño dentro del requisito, con precedente en ciclos cerrados.

| ID | Decisión | Por qué |
|---|---|---|
| OD-CTL07-01 | Las alertas se **derivan** al consultar, sobre datos reales. Solo se persiste la revisión humana | No se duplica la información de PROC-03, PROC-06 ni de la auditoría. La alerta no muta nada (no hay acusación automática) |
| OD-CTL07-02 | Duplicidad = mismo `unidad_id` y mismo objeto normalizado (minúsculas, sin acentos, espacios colapsados), en expedientes no `DESCARTADO`. Una alerta por par, con clave `DUPLICIDAD:<id menor>:<id mayor>` | Es un criterio exacto, sin umbrales ni similitud difusa, que no exige una decisión de la dueña. Con el par, la clave es estable aunque llegue un tercer expediente |
| OD-CTL07-03 | Proveedor relacionado = documento normalizado de la oferta igual a `tipo_documento + numero_documento` del funcionario, normalizados con la misma regla que PROC-06 (mayúsculas, sin espacios ni guiones). Clave `PROVEEDOR_RELACIONADO:<oferta>:<funcionario>` | Es la coincidencia de identidad que el producto puede probar. Sin el maestro de proveedores (D-GOV-03), el parentesco o la participación societaria no se pueden detectar, y se dice así en la pantalla |
| OD-CTL07-04 | Autoaprobación = cada evento `GOV_SOD_CONFLICT_BLOCKED` o `GOV_SOD_ROLE_CONFLICT_BLOCKED` del ente. Clave `AUTOAPROBACION:<evento>` | En Gobierno la autoaprobación nunca llega a ejecutarse: la SoD la bloquea. La señal atípica es el **intento**, que ya queda auditado |
| OD-CTL07-05 | Fraccionamiento: **no disponible**. Ni la oferta ni la adjudicación registran monto (OBS-PROC08-MONTO-01), y los umbrales de modalidad en U.T. dependen de N38, de clase C | Sin monto, la alerta sería una conjetura. Precedente: PROC-11 publicó la función `PAGADOR` como no disponible, con su requisito habilitante |
| OD-CTL07-06 | Override frecuente: **no disponible**. En Gobierno no hay overrides: SoD (CTL-01, PROC-11) y el techo de autoridad (CTL-03) bloquean sin excepción | No se crea un mecanismo de excepción para tener algo que contar |
| OD-CTL07-07 | Revisión única e inmutable por alerta (`UNIQUE(company_id, clave)` y disparador), con resultado `SIN_OBSERVACION` o `REQUIERE_SEGUIMIENTO`, observación de 10 a 2000 caracteres y el resumen visto | Es evidencia de Control Interno. El seguimiento real se hace en CTL-06 (hallazgo), que ya existe |
| OD-CTL07-08 | Capacidades nuevas: `gobierno_alertas:view` (STANDARD) y `gobierno_alertas:review` (SENSITIVE, con MFA). Se conceden a FUNCIONAL_COMPLETO, como en 0070 | Separan consultar de revisar, igual que `gobierno_hallazgos:verify`. No son técnicas: ADMIN no las recibe (CTL-03) |
| OD-CTL07-09 | No hay autorrevisión: si el usuario es sujeto de la alerta (su funcionario vinculado en proveedor relacionado, o es el actor del intento en autoaprobación), 409 `GOV_ALERT_SELF_REVIEW` | Es un conflicto de interés evidente (N23) |
| OD-CTL07-10 | Las revisiones rechazadas no se auditan: son errores de validación o de estado, como en las demás pantallas de Gobierno. El éxito emite `GOV_ATYPICAL_ALERT_REVIEWED` | Es la convención del catálogo |
| OD-CTL07-11 | Si una alerta revisada deja de detectarse (por ejemplo, porque descartan un expediente), su revisión se conserva y sigue visible como «Revisada · ya no se detecta» | No se pierde evidencia |
