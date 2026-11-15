# Tarjeta de prueba de la dueña · CNT-04 Supervisor / responsable del contrato

**Dónde está:** Menú › Gobierno · Contratos › Contratos y órdenes › (un contrato **formalizado**) › sección «Supervisor / responsable del contrato».

**Qué necesita antes de empezar:**
- un contrato formalizado (CNT-01);
- al menos dos funcionarios con una ocupación vigente (Gobierno › Ocupación de cargos: titular, encargado, suplente o en comisión);
- actos de designación **eficaces** (DOC-02), emitidos por un cargo con la competencia **Aprobar sobre Contrataciones**, que es la autoridad que adjudica.

| # | Paso | Resultado esperado |
|---|---|---|
| 1 | Abra el contrato formalizado y baje hasta «Supervisor / responsable del contrato» | Dice «Sin supervisor designado» |
| 2 | Pulse «Nueva designación» | Aparece el formulario con la fecha efectiva de hoy |
| 3 | Elija el funcionario | Solo aparecen funcionarios con ocupación vigente. Si tiene una sola, queda elegida y se ven «Cargo: …» y «Unidad: …» |
| 4 | Elija el acto de designación | Solo aparecen actos eficaces de un cargo con Aprobar sobre Contrataciones |
| 5 | Pulse «Formalizar designación» y confirme (le pedirá MFA si su sesión no lo tiene) | «Designación SUP-01 registrada.». El bloque «Supervisor vigente» muestra funcionario, cargo, unidad, figura, desde, acto y emisor |
| 6 | Revise «Historial de supervisores» | SUP-01 · Vigente · En ejercicio |
| 7 | Pulse «Sustituir supervisor», ponga una fecha efectiva futura (por ejemplo, dentro de 7 días), elija otro funcionario y **otro** acto | Exige «Motivo del cambio» |
| 8 | Escriba el motivo y formalice | «Designación SUP-02 registrada.» y el bloque «Designación programada» con el nuevo supervisor y su fecha |
| 9 | Revise el historial | SUP-01 «En ejercicio · Sustituida» (hasta el día anterior a la fecha nueva) y SUP-02 «Programada · Vigente». Nada se borró |
| 10 | Intente sustituir con el mismo acto de la designación vigente, o con una fecha posterior al fin del contrato | Rechazo con mensaje claro |
| 11 | Entre a la ficha del expediente de origen | La cronología muestra «Supervisor de CT-…: …» |
| 12 | Gobierno › Bitácora: filtre por la acción de supervisor del contrato | Constan la designación y la sustitución, con el actor |

**Qué no hace (a propósito):**
- No revoca sin sucesor: la ley no regula la revocación.
- No permite dos supervisores a la vez (decisión OD-CNT04-01).
- No conforma valuaciones ni actas (eso es CNT-03).

Credenciales: no se registran. Su aceptación (OWNER_ACCEPTED) solo la da usted.
