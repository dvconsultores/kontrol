# Tarjeta UAT · Procesos en la bitácora y en la auditoría (CTL-02 y CTL-04)

**Use solo datos sintéticos.**

## Antes de empezar

- **Usuarios:**
  - uno con «Bitácora institucional» y «Auditoría institucional» (`gobierno_auditoria:view`);
  - un operador vinculado a un funcionario con cargo (Identidad institucional), con permiso para registrar tasas oficiales y para ver el reporte de contrataciones.
- **Datos:** el ente activo y el ejercicio vigente.

## Ruta en el menú

- Gobierno › **Bitácora institucional**
- Gobierno › **Auditoría institucional**
- Gobierno · Tesorería › **Tasas oficiales**, y Gobierno · Contrataciones › **Reporte de contrataciones** (para generar los eventos)

## A. Un proceso que antes salía sin nombre (Tasas oficiales)

1. Con el operador, registre una tasa oficial de hoy.
2. Con el usuario de auditoría, abra la Bitácora y filtre por la acción de registro de tasa.

**Esperado:**
- debajo de la acción se lee «Tesorería · Tasas oficiales»;
- ya no aparece un código técnico del tipo «gov-tre-09».

## B. Detalle del evento

1. Abra el evento de la parte A.

**Esperado:**
- «Proceso: Tasas oficiales» y «Módulo: Tesorería»;
- se mantienen el actor efectivo (funcionario), el cargo, la unidad, la IP, la sesión y la correlación.

## C. Otro proceso, clasificado por separado

1. Con el operador, exporte el Reporte de contrataciones.
2. En la Bitácora, filtre por la acción de exportación del reporte.

**Esperado:** «Reportes · Reporte de contrataciones».

## D. Procesos ya conocidos

1. En la Bitácora, abra un evento de Estructura organizativa, de Cargos, de Actos administrativos o de Cuentas bancarias.

**Esperado:** el mismo nombre de proceso que antes, ahora con su módulo, por ejemplo «Organización y autoridad · Estructura organizativa».

## E. Inicios de sesión

1. Filtre la Bitácora por un inicio de sesión de una cuenta vinculada.

**Esperado:** el proceso dice «Autenticación», sin módulo. Es correcto: un inicio de sesión no pertenece a un proceso institucional.

## F. Filtro por proceso de la Auditoría institucional (CTL-04)

1. Abra Auditoría institucional y despliegue el filtro «Proceso».

**Esperado:**
- la lista incluye, entre otros, «BUD-08 · Compromiso presupuestario», «CNT-01 · Contratos y órdenes», «TRE-09 · Tasas oficiales» y «REP-10 · Reporte de control interno»;
- al elegir «TRE-09 · Tasas oficiales», la tabla muestra el evento de la parte A, ya sin el error de filtro no válido que daba antes.

## Fuera de esta tarjeta

- Los eventos históricos no se reescriben: el proceso se calcula al consultar, así que los eventos antiguos también aparecen ya clasificados.
- No hay cambios de permisos.
