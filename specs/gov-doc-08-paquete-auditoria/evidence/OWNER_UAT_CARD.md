# OWNER UAT CARD · GOV-DOC-08 · DOC-08 «Paquete de auditoría exportable» (GOV-DOC-010)

```
MÓDULO: Gobierno · PROCESO: DOC-08 Paquete de auditoría exportable
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)

DÓNDE ENTRAR:
  - Gobierno › Auditoría institucional › (una muestra) › botón «Generar paquete de auditoría».
  - Gobierno › Paquetes de auditoría (ruta /gobierno/paquetes): historial y verificación de copias.

ROLES A USAR:
  - Control Interno: usuario con gobierno_paquetes:view y :generate (MFA), documentos:download y la consulta de los
    procesos cuya evidencia se exporta. En la base de QA, el administrador «con todo» (ADMIN + FUNCIONAL_COMPLETO)
    los tiene: la migración 0071 concede gobierno_paquetes a FUNCIONAL_COMPLETO.
  - Consulta: un usuario solo con gobierno_paquetes:view. Ve el historial y verifica, pero no genera.
  - Negativas:
      · un usuario sin documentos:download;
      · un usuario de otra empresa.

PRECONDICIONES:
  - Licencia de QA con el módulo «gobierno».
  - Una muestra de CTL-04 guardada que incluya eventos con documentos, por ejemplo una muestra «Todas» del proceso
    ORG-01 tras activar el ente con su acto adjunto.
  - Opcional: un hallazgo de CTL-06 originado en esa muestra.

PASOS Y RESULTADO ESPERADO:
  1. MUESTRA: abra la muestra y pulse «Generar paquete de auditoría».
  2. VISTA PREVIA: verá la muestra (código, método, población y tamaño) y el contenido del paquete: eventos,
     documentos incluidos, documentos excluidos, hallazgos y tamaño estimado.
     La tabla de documentos indica «Incluido» o «Excluido» con el motivo (sin permiso / no disponible).
  3. GENERAR: escriba el propósito (para qué y para quién) y pulse «Generar paquete».
     Se abre «Paquete PA-<año>-<nnnn>» con la huella del paquete y la del manifiesto (SHA-256).
     El aviso dice que la huella no es una firma electrónica.
  4. CONTENIDO: revise las tablas de eventos, documentos y hallazgos del paquete.
  5. DESCARGAR: «Descargar paquete» baja paquete-<código>.zip y «Descargar manifiesto» baja manifiesto-<código>.json.
     Dentro del ZIP: manifest.json, SHA256SUMS, INDICE.csv, LEEME.txt, muestra/, eventos/, documentos/ y hallazgos/.
  6. ÍNDICE: abra INDICE.csv (separador «;»). Hay una fila por fichero, con su huella.
     LEEME.txt explica cómo verificar el paquete.
  7. VERIFICAR LA COPIA ÍNTEGRA: en Gobierno › Paquetes de auditoría › «Verificar un paquete», suba el ZIP descargado.
     Resultado: «Válido» y «La copia es idéntica byte a byte a la registrada».
  8. VERIFICAR UNA COPIA ALTERADA: modifique un fichero dentro del ZIP (por ejemplo, edite LEEME.txt) o borre uno, y vuelva a verificar.
     Resultado: «Inválido · Archivo alterado» o «Incompleto · Falta un archivo», con la ruta afectada.
  9. HISTORIA: en la ficha del paquete, la sección «Verificaciones» lista cada comprobación con fecha, resultado y usuario.
 10. FUERA DEL SISTEMA (opcional): descomprima el ZIP y ejecute «sha256sum -c SHA256SUMS».
     Compare la huella de manifest.json con la que muestra KONTROL.

PRUEBA NEGATIVA:
  a) Usuario de consulta: ve el historial y puede verificar, pero en la muestra no aparece «Generar paquete de auditoría».
  b) Usuario sin documentos:download: al generar, todos los documentos salen «Excluido · Sin permiso».
     Si intenta descargar un paquete con documentos incluidos, recibe «No puede descargar el paquete».
  c) Otra empresa: «Paquete no encontrado». Si verifica una copia de otra empresa, el resultado es «Inválido · El paquete no está
     registrado en este ente», sin revelar nada de la otra.
  d) Un ZIP que no es un paquete (cualquier otro fichero) se rechaza: «El archivo no es un ZIP legible».

AUDITORÍA:
  - Sistema › Auditoría registra «Paquete de auditoría generado», «descargado», «verificado íntegro» y «Verificación no superada».
  - Gobierno › Auditoría institucional incluye el proceso «DOC-08 · Paquetes de auditoría».

LIMPIEZA: no hace falta. Los paquetes y sus verificaciones son registros permanentes por diseño.

DEUDAS CONOCIDAS NO BLOQUEANTES:
  - El paquete no lleva firma electrónica (DOC-05 es otro proceso): la integridad se prueba con huellas.
  - El paquete se genera de una muestra de CTL-04; el expediente electrónico (DOC-01) llegará con su proceso.
```
