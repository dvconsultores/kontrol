# OWNER UAT CARD · GOV-CTL-10 · CTL-10 «Controles materiales que impiden cerrar ejercicio o proceso» (GOV-CTL-012)

```
MÓDULO: Gobierno · PROCESO: CTL-10 Controles de cierre
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)

DÓNDE ENTRAR:
  - Gobierno › Controles de cierre (/gobierno/cierres): lista, nueva política y ficha.
  - Gobierno › Controles de cierre › Cierres bloqueados (/gobierno/cierres/bloqueos): intentos que el sistema impidió.
  - El bloqueo se ve en los cierres existentes: Estructura organizativa › «Cerrar ejercicio» y
    Programación financiera › «Cerrar programa». No hay botón nuevo de cierre.

ROLES A USAR:
  - Control Interno: gobierno_cierre:view y :manage. Para activar y retirar, además :activate (pide MFA).
    En la base de QA, el administrador «con todo» (ADMIN + FUNCIONAL_COMPLETO) los tiene.
  - Lector: solo gobierno_cierre:view.
  - Negativas: un usuario solo con :view; un usuario de otra empresa.

QUÉ ES Y QUÉ NO ES:
  Una política dice qué controles deben estar resueltos antes de cerrar la estructura de un ejercicio o un programa
  financiero. Hay dos controles y dos cierres, fijos: no es un motor de reglas y nadie escribe condiciones.
  El control solo impide; nunca concede autoridad. Si no hay política efectiva, el cierre funciona como antes.

PRECONDICIONES:
  - Licencia de QA con el módulo «gobierno» y ente activo.
  - Para el flujo A: una estructura VIGENTE de un ejercicio pasado.
  - Para el flujo B: un programa VIGENTE y un acto EMITIDO con fecha en el ejercicio del programa.

PASOS Y RESULTADO ESPERADO (flujo A, estructura):
  1. NUEVA POLÍTICA: en Controles de cierre pulse «Nueva política». Elija «Cerrar estructura del ejercicio», escriba nombre,
     fundamento y vigencia. Pulse «Crear política». Se abre la ficha «Política PC-…» en Borrador.
  2. CONTROL: pulse «Añadir control». Elija «Hallazgos abiertos», riesgo «Medio o superior» y escriba por qué es material.
     Pulse «Guardar». El control aparece en la tabla.
  3. ACTIVAR: pulse «Activar» (MFA). Estado Vigente · efectiva hoy; la historia muestra quién y cuándo.
  4. BLOQUEO: con un hallazgo de riesgo ALTO abierto, abra la estructura del ejercicio pasado y pulse «Cerrar ejercicio».
     Aparece «Cierre bloqueado por control material» con la política, por qué es material, el hallazgo con su enlace,
     «Ir a la lista» y «Quién es dueño: Control Interno». La estructura sigue Vigente.
     «Ir a la lista» abre los hallazgos pendientes de ese control, con el aviso «Filtro de cierre» y su botón «Quitar filtro».
  5. REGISTRO: en Cierres bloqueados aparece el intento con fecha, política, objeto y usuario.
  6. RESOLVER: complete y verifique el hallazgo en Hallazgos (lo verifica otra persona) y repita «Cerrar ejercicio».
     Esta vez cierra.

FLUJO B, PROGRAMA:
  7. Cree y active una política para «Cerrar programa financiero» con el control «Actos sin eficacia».
  8. Con un acto emitido en el ejercicio del programa, pulse «Cerrar programa» y confirme. El panel muestra el acto.
  9. RETIRAR: abra la política, pulse «Retirar», escriba el motivo y confirme (MFA). Estado Retirada; la historia lo muestra.
 10. Repita «Cerrar programa»: cierra. La política retirada ya no controla.

PRUEBA NEGATIVA:
  a) Segunda activa: active otra política de la misma acción: «Ya hay una política vigente para esa acción de cierre.»
  b) Sin controles: en Borrador sin controles, «Activar» está deshabilitado y lo explica.
  c) Solo lectura: un usuario con :view no ve «Nueva política», «Activar» ni «Retirar».
  d) Otro ente: un usuario de otra empresa no ve la política ni sus bloqueos.
  e) Edición tardía: tras activar no se pueden cambiar datos ni controles.
  f) Programa o estructura cerrados: repetir el cierre responde por el estado, no por CTL-10.

QUÉ DEBE REVISAR USTED:
  - Si el texto del panel explica el bloqueo a quien intenta cerrar.
  - Si «Medio o superior» y «Cualquier riesgo» son las palabras que usaría Control Interno.
  - El código «EST-<ejercicio>» del cierre de estructura es derivado: no está guardado en la estructura.
  - ORG-02 no tiene SoD propia en el cierre: solo los programas pasan por SoD antes de CTL-10.
  - Límite: la lista de bloqueos revisa los 5.000 eventos más recientes de la empresa.

DATOS REALES: esta prueba usa datos sintéticos. No hay datos de producción ni datos reales de Gobierno.
```

Respuesta: `ACEPTADO`, u `OBSERVADO` con lo que deba cambiar.
