# GOV-TRE-FUNCTIONAL-03 · TRE-08 · informe de bloqueo

**Resultado:** `TRE08_FULL_PROCESS_IMPLEMENTABLE = 0`. Sin código, sin migración, sin Spec Kit: la parada ocurre en las compuertas de dependencia, antes de `specify`, como ordena el encargo (§43, §44).

Requisito: GOV-TRE-009, «Controlar fondos/cajas autorizadas, responsables, reposicion, rendicion y arqueos cuando aplique» (IR, N05, N20, N23).

## Fuentes leídas

- **N04, Reglamento N.º 1 LOAFSP**, G.O. 5.781 Extraordinario, 12-08-2005, arts. 64 a 78 y 94 a 99. Es la norma que regula la materia; la matriz cita N05, N20 y N23, y no N04.
- **Manual Funcional de Fondos en Anticipo**, ONCOP/SIGECOF, §4.1 a §4.11. Es un manual del sistema nacional: se usa como procedimiento, no como norma.
- N05, ficha de la Biblioteca y texto consultado en TRE-02. Sin regla propia de fondos o cajas en lo revisado.
- `requerimientos/gobierno/`: IR y Biblioteca. El SNAT protegido no se abrió.

## Compuertas

| # | Compuerta | Resultado | Evidencia |
|---|---|---|---|
| 1 | Dependencia de pago | **TRE04_DEPENDENCY_REQUIRED = 1** | Art. 66: la entrega se autoriza «mediante órdenes de pago sin imputación presupuestaria». Manual 4.5.2 y 4.8.2: constitución y reposición emiten Orden de Pago; 4.9.2: la ONT «procede a realizar el respectivo pago» |
| 1b | Dependencia de presupuesto | **BUD_DEPENDENCY_REQUIRED = 1**, nueva | Los gastos del fondo registran compromiso y causado (Manual 4.7 a 4.14). Art. 68: la reposición indica «la imputación» de cada comprobante. Art. 64: tope de 8 % sobre créditos presupuestarios |
| 2 | Responsable | **ORG06_DEPENDENCY_REQUIRED = 1** | Art. 96: la resolución identifica «el funcionario responsable del fondo». Art. 72: registro de «funcionarios». Manual 4.1: designación y cuenta del cuentadante. Es persona natural. Gobierno no tiene modelo de persona; ORG-06 está BLOCKED (N40) |
| 3 | Tipos | RESUELTA | Términos normativos: «fondo en anticipo», «fondo de caja chica». También existe «fondo en avance»; no es fondo fijo. La caja chica depende de un fondo en anticipo (arts. 70 y 97) |
| 4 | Origen de fondos | **BLOQUEADA** | Art. 67: cuenta a nombre de la dependencia, con autorización de la ONT. Los recursos llegan por orden de pago. La caja chica va «con cargo al respectivo fondo en anticipo» |
| 5 | Acto | RESUELTA | Art. 96: resolución interna de la máxima autoridad, con unidad, funcionario, monto, conceptos, máximo por pago y periodicidad. Art. 97 para la caja chica. Reutilizaría DOC-02 |

**Arqueo:** ni N04 ni el manual lo regulan en el texto revisado, y el requisito dice «cuando aplique». Sin contrato normativo.

**Rendición:** arts. 64, 68 y 70: obligación de rendir, con relación de comprobantes, beneficiario, monto, imputación y estado del fondo.

**Reposición:** es una solicitud del responsable al alcanzar el 75 % (arts. 68 y 70). Su efecto es una orden de pago. Solo la solicitud podría existir sin TRE-04.

## Por qué no cabe un proceso parcial

El movimiento del fondo es un pago público con ejecución presupuestaria (arts. 74 y 75, Manual 4.7 a 4.15), y constituirlo y reponerlo son órdenes de pago. Sin esos dominios, el saldo que la pantalla debe mostrar no tiene origen real: habría que declararlo o simularlo, y el encargo prohíbe ambas cosas. Un registro de resoluciones y responsables no sería «controlar fondos, reposición, rendición y arqueo».

## Lo que desbloquea TRE-08

| Dependencia | Estado | Bloqueo actual |
|---|---|---|
| TRE-03 orden de pago | NOT_STARTED | Requiere obligación causada |
| TRE-04 pago | BLOCKED | Validación legal N37 |
| BUD, compromiso y causado | sin Gobierno | Motor presupuestario |
| ORG-06 persona-cargo-usuario | BLOCKED | Validación legal N40 |

Preguntas para la dueña, solo si quiere un alcance distinto:
- **OQ-TRE08-01:** ¿el responsable puede ser cargo más acto de DOC-02, como en TRE-01, aunque la norma nombre al funcionario? Resolvería solo la compuerta 2.
- **OQ-TRE08-02:** ¿se autoriza un proceso reducido y distinto, sin saldo ni movimientos, solo «registro de fondos autorizados y solicitudes»? No cerraría GOV-TRE-009.

Cifras en U.T. (200 y 20) y porcentajes (8 %, 75 %): requerirían una fuente vigente de valor de U.T. y validación legal de vigencia.
