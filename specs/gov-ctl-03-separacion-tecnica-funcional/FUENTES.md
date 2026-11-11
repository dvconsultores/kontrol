# CTL-03 · Fuentes leídas (2026-11-11)

Requisito del sponsor (IR): GOV-CTL-004 «No permitir al administrador técnico fabricar autoridad funcional para
comprometer/pagar/aprobar.» Fuentes N20, N23 (N40 no material: `specs/gov-norm-n40/`), P0, actor Control Interno.

Copias oficiales obtenidas el 2026-11-11 de la base normativa de la Contraloría que cita la biblioteca (fuera del repositorio):
- N20 `CONTROLINTERNO.pdf`, sha256 3959f8b0…: Resolución N.° 01-00-000619 de la Contraloría General de la República,
  16-12-2015, «Normas Generales de Control Interno» (biblioteca: G.O. 40.851, 18-02-2016, clase A). Escaneado, sin capa de
  texto: leído página a página.
- N23 `LCC.pdf`, sha256 cd75b9b9…: G.O. N.° 6.699 Extraordinario, 02-05-2022, Ley de Reforma del Decreto con Rango, Valor y
  Fuerza de Ley contra la Corrupción, con el texto íntegro reimpreso (clase A).

## N20 · Normas Generales de Control Interno

| Artículo | Texto literal |
|---|---|
| art. 5 | «El control interno es un sistema que comprende el plan de organización, las políticas, normas, así como los métodos y procedimientos, adoptados para la autorización, procesamiento, clasificación, registro, verificación, evaluación, seguimiento y seguridad de las operaciones…» |
| art. 6 | El sistema de control interno tiene por objeto «asegurar el acatamiento de las normas, salvaguardar los recursos y bienes que integran el patrimonio público… promover la eficiencia, eficacia y legalidad de las operaciones… así como garantizar razonablemente la rendición de cuentas» |
| art. 30 | «Son elementos de las actividades de control, entre otros, segregación de funciones; controles sobre acceso a los recursos, información y archivos; verificaciones; aprobaciones; autorizaciones; conciliaciones; revisión de operaciones, procesos y actividades; y supervisión» |
| art. 32 | «El acceso a los registros y recursos materiales y financieros debe limitarse a los servidores públicos autorizados para ello, quienes estarán obligados a rendir cuenta de su custodia o utilización» |
| art. 39, num. 3 | «Adoptar las medidas que permitan, sólo al personal autorizado, el acceso y la modificación de los datos y de la información contenidos en los sistemas…» |
| art. 39, num. 8 | «**Establecer políticas y procedimientos para prevenir que algún individuo controle aspectos claves de las operaciones del computador y de esa manera evitar acciones o accesos no autorizados a los bienes o archivos**» |
| art. 34, num. 3 | Manual de Descripción de Cargos: «las funciones, complejidad, requisitos y líneas de autoridad, así como la responsabilidad de cada uno de los cargos» |

## N23 · Ley contra la Corrupción (G.O. 6.699 Ext.)

| Artículo | Texto literal |
|---|---|
| art. 6 | «Son principios rectores para la administración, manejo, custodia y salvaguarda del patrimonio público: la honestidad, probidad, decoro, honradez, transparencia, participación ciudadana, eficacia, eficiencia, legalidad, colaboración, rendición de cuentas, responsabilidad y corresponsabilidad» |
| art. 7 | Los funcionarios «deben administrar y custodiar el patrimonio público con decencia, decoro, probidad y honradez, de forma que la utilización de los bienes y el gasto de los recursos que lo integran, se haga de la manera prevista en la Constitución… y las leyes» |

## Lectura para el producto

El poder técnico sobre la plataforma (usuarios, roles, licencia, configuración) es un «aspecto clave de las operaciones del
computador» (N20 art. 39 num. 8). Si ese poder bastara para obtener la autoridad de aprobar, comprometer o pagar, un solo
individuo controlaría a la vez el sistema y la operación: es lo que la norma ordena prevenir. La autoridad de negocio debe
nacer de la línea de autoridad del cargo (N20 art. 34 num. 3), en el marco de la legalidad (N23 arts. 6 y 7). Ninguna fuente
prohíbe que una misma persona tenga legítimamente ambas funciones por concesiones separadas.

## Decisiones vigentes que se reutilizan (no se reabren)

OD-DEL-10 (ADMIN técnico y de seguridad; FUNCIONAL_COMPLETO, el negocio), techo de delegación de la Spec 003 (INV-DEL-*),
OD-ORG06-04 (alcance: cuenta → vínculo → funcionario → ocupación → cargo), OD-ORG06-06 (categorías de rol como metadato,
incluida ADMINISTRACION_TECNICA), OD-ORG06-09 (exigencia de identidad por ente, inactiva por defecto, activada con MFA),
OD-ORG06-13 (nadie vincula ni activa su propia cuenta), ORG-04 (nadie registra ni activa la ocupación de su propio
funcionario).
