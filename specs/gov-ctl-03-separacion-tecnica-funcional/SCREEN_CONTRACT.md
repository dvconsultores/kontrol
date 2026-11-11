# CTL-03 · Contrato de pantalla

Ruta `/gobierno/control/separacion`; menú Gobierno → «Separación técnica y funcional» (junto a «Bitácora institucional»);
permiso `gobierno_auditoria:view`; módulo `gobierno`; empresa activa = ente. Sólo lectura.

## Encabezado
- Título h1 «Separación técnica y funcional».
- Texto: «Quien administra la plataforma no obtiene por ello autoridad de negocio. Esta vista muestra, para cada administrador
  técnico, de dónde viene cada permiso y si ejerce un cargo.»

## Bloque 1 · Integridad de la separación (sección «Integridad»)
- Estado: «Separación íntegra» o «Separación alterada» (con la lista de capacidades fuera de lugar y en qué rol).
- «El rol Administrador tiene N capacidades, todas técnicas.» / «Funcional completo tiene M capacidades, ninguna técnica.»
- Exigencia de identidad institucional del ente: «Activa» o «Inactiva», con el texto del efecto (PDD-CTL03-09).

## Bloque 2 · Administradores técnicos (sección «Administradores técnicos»)
Lista (tabla en escritorio, tarjetas en móvil). Por cuenta:
- Usuario y estado de la cuenta.
- Estado de separación (PDD-CTL03-05) como texto, no solo color.
- Roles técnicos y roles funcionales, cada uno con su nombre, «protegido» si lo es, el alcance («Todas las empresas» o el
  ente) y su origen (PDD-CTL03-07); categorías ORG-06 del rol en el ente si las tiene.
- Identidad institucional: código del vínculo y funcionario, o «Sin vínculo institucional vigente».
- Cargos que ejerce y competencias (acción × materia) derivadas, o el motivo de ORG-06 por el que no tiene autoridad.
- Enlaces (solo si el usuario tiene el permiso): a Identidad institucional del funcionario.
Estado vacío: «No hay administradores técnicos con acceso a este ente.»

## Bloque 3 · Intentos denegados (sección «Intentos denegados»)
Últimos 50: fecha y hora, usuario, qué intentó (rol o capacidad), código y su explicación en español, capacidades que excedía;
enlace «Ver en la bitácora» solo si el evento está en la bitácora institucional. Estado vacío: «No hay intentos denegados.»

## Reglas
- Ningún UUID como texto principal.
- Errores con mensaje en español y reintento; 403 «No tiene permiso para ver esta información».
- Responsive: 1280, 390 y 320 sin desborde horizontal; teclado y foco visibles; Axe sin violaciones serias o críticas.
