# Decisión pendiente de la dueña · `ENTORNO-SIN-CLAMSCAN — BLOCKED BY OWNER DECISION`

Hechos: el producto exige un analizador real por defecto y falla cerrado sin él (correcto); la Spec 046 se certificó con ClamAV
1.4.3 real (closeout §7) pero el método no está guionizado; esta máquina no lo tiene; sin él **no se certifican** 35 pruebas de
backend (los dos motores), 2 de n9 y 4 E2E: todo el camino principal de la gestión documental. Instalarlo exige privilegios
(`apt`) o un prefijo de usuario documentado, red para las firmas y una política de refresco (`clamav-qa-feasibility.md`,
`virus-definition-requirements.md`). No hay autoridad en el repositorio que lo ordene (CL-046-09 lo hace «configurable»).

Opciones (`option-matrix.md`): **A** proveer ClamAV real en el QA canónico (recomendada; ver `recommendation.md`), **B**
seguir declarando la ausencia (estado actual), C doble `CLEAN` en capas no de integración (descartada: §159 y closeout),
D todo PostgreSQL-only (descartada). Marcar una opción en el prompt de continuación.
