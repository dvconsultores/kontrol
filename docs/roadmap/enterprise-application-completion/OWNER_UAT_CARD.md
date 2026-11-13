# Tarjeta de prueba de la dueña

**Dirección:** http://127.0.0.1:5173, en el equipo de P2. **Acceso:** fichero local protegido, nunca en Git. **Datos:** sintéticos.

**Límites conocidos:** `UAT_DATABASE_ENGINE = PostgreSQL`, `UAT_SCHEMA_SOURCE = Alembic`, con Vite, no el empaquetado de producción. Al primer ingreso pide dar de alta la verificación en dos pasos. El menú también muestra Gobierno por la licencia de prueba; no forma parte de esta tarjeta. Solo es accesible desde ese equipo. El bloqueo de pago a proveedores no aprobados afectará a los proveedores existentes cuando se despliegue: decisión pendiente.

## Terceros (Maestros → Terceros)

1. Pulse «Nuevo tercero», cree un proveedor con RIF y marque el rol Proveedor. Debe llevarle a su ficha sin pedir confirmación.
2. Edite la razón social y guarde.
3. Agregue una dirección y un contacto, y agregue el rol Cliente.
4. Intente registrar un pago en Compras → CxP. Debe rechazarlo: «El proveedor no está aprobado para recibir pagos.»
5. Pulse «Aprobar proveedor». Debe decir que falta una cuenta bancaria verificada.
6. Agregue una cuenta, escriba la evidencia, verifíquela y apruebe. El pago ya debe registrarse.
7. Edite la cuenta. El proveedor vuelve a «Pendiente» y el historial lo muestra.

## Importaciones (Compras → Importaciones)

Necesita un proveedor y una orden de compra aprobada de ese proveedor.

1. Pulse «Nueva importación», ponga un código y elija el proveedor.
2. Intente vincular la orden. Debe decir qué falta negociar.
3. Complete INCOTERM, condiciones de pago y de entrega, guarde y vincule la orden. El estado pasa a «Orden vinculada».
4. Pulse «Confirmar documentación». Debe decir qué documentos faltan.
5. En cada documento: escriba la referencia, pulse «Recibir», adjunte un PDF y pulse «Validar». Necesita un tipo documental que admita PDF, en Documentos → Tipos documentales.
6. Pulse «Confirmar documentación». El estado pasa a «Documentación completa» y el historial lo muestra.

### Continuar la importación

Antes de pagar, apruebe al proveedor en Maestros → Terceros (RIF y cuenta bancaria verificada). El expediente enlaza a su ficha si falta.

7. En «Finanzas», elija «Anticipo», escriba un monto y pulse «Registrar». El anticipo aparece en la lista, y se aprueba o ejecuta en Cuentas por pagar.
8. Intente registrar un pago con un proveedor sin aprobar. Debe rechazarlo y ofrecer «Ver proveedor».
9. En «Seguimiento», designe un agente, escriba origen y destino y pulse «Guardar seguimiento». El resumen muestra al agente.
10. Registre el hito «Salida» con su fecha. Aparece en la línea de tiempo y rellena la salida real.
11. En «Correcciones», cree un faltante. Si estaba en «Documentación completa», el expediente vuelve a «Orden vinculada» y no deja confirmar hasta resolverlo.
12. Escriba la resolución, pulse «Resolver» y vuelva a pulsar «Confirmar documentación».
13. En «Resumen», pulse «Confirmar despacho». El estado pasa a «Despachada», desaparece «Cancelar importación» y el historial muestra «Despacho confirmado».
14. Reduzca la ventana al ancho de un teléfono y recargue: el menú arranca plegado y el expediente se lee sin desplazamiento lateral.

### Recibir y ubicar

Necesita un almacén con una ubicación activa, en Organización.

15. Tras despachar, en «Recepción» escriba un código, elija el almacén y pulse «Crear recepción». No pide la orden: es la del expediente. El resumen pasa a «Esperando arribo».
16. En «Arribo» indique los bultos y confirme. Pasa a «En recepción».
17. Pulse «Abrir recepción». Registre la línea y pulse confirmar, enviar a calidad, conforme y aceptar. Pulse «Volver al expediente».
18. Pulse «Gestionar incidencias», registre un daño, escálelo y trátelo. Vuelva: la incidencia aparece en «Diferencias e inventario» y el expediente dice «Por confirmar inventario».
19. Pulse «Confirmar inventario», registre el conteo y confirme. Vuelva: dice «Por ubicar».
20. En «Ubicación», elija el destino y pulse «Ubicar». Dice «Recibida y ubicada», con la ubicación y la cantidad.

**Límite:** un put-away hecho desde el menú de Inventario, sin pasar por el expediente, no se le atribuye.

### Costos de importación: gastos

Necesita una tasa en Tesorería para la moneda del gasto, con fecha igual o anterior a la del gasto.

21. En «Costos de importación», registre un gasto en una moneda sin tasa. Debe rechazarlo y ofrecer «Registrar tasa en Tesorería»; nunca asume tasa 1.
22. Registre la tasa y repita. El gasto muestra la moneda, la tasa, su fuente y fecha, y el equivalente en moneda funcional. Ejemplo: `1.250,50 × 36,125 = 45.174,31`.
23. Pulse «Anular gasto», escriba el motivo y confirme. Sigue en la lista como «Anulado» con su motivo, deja de sumar y el historial lo muestra.
24. Compruebe «Capas de costo de esta importación»: el costo aparece en la moneda de la orden.

**En teléfono:** cada acción deja una notificación que se cierra a mano con su ✕; solo se ve la más reciente.

### Costos de importación: repartir y aplicar al costo (landed cost)

Necesita un expediente recibido, con capas de costo, y un gasto registrado.

25. En la tarjeta del gasto, en «Clasificación del costo», elija «Capitalizable» y pulse «Guardar clasificación». Sin esa clasificación, la vista previa explica que no se puede aplicar.
26. En «Criterio de reparto» elija «Por valor», «Por cantidad» o «Manual». No hay criterio marcado de antemano. En «Manual», escriba el importe de cada producto.
27. Pulse «Generar vista previa». Ve «Vista previa: aún no se ha aplicado nada», la tabla por producto (base, participación, importe asignado, costo actual y costo resultante) y «El reparto cuadra exactamente». Si en «Manual» no cuadra, muestra la diferencia y no deja aplicar.
28. Pulse «Aplicar costo», revise el resumen y pulse «Confirmar aplicación». El costo efectivo de la capa y su «Valor en inventario» suben; Inventario → Valorización también lo refleja.
29. Intente aplicar de nuevo el mismo gasto: el sistema lo impide.
30. En «Historial de aplicación», pulse «Revertir aplicación», escriba el motivo y confirme. Queda «Revertido», el valor vuelve exactamente al anterior y el historial conserva ambas operaciones.
31. Si alguna mercancía de ese expediente ya salió del inventario, la aplicación y la reversión se bloquean y lo explican: el costo no se aplica de forma retroactiva.

### Reporte formal de diferencias

Necesita una recepción del expediente con alguna diferencia: una incidencia registrada (paso 18) o una cantidad que no coincide.

32. En «Diferencias e inventario», busque «Reporte formal de diferencias · REC-…» de esa recepción. Una recepción sin diferencias dice «Sin diferencias» y no deja emitir.
33. Con diferencias, dice «Diferencias detectadas sin reporte». Pulse «Emitir reporte formal». Ve una referencia del tipo `DIF-000001-R1` (el número es correlativo por empresa), «Revisión 1», «Emitido por» con su nombre de usuario y el estado «Reporte emitido».
34. Pulse «Descargar PDF»: se descarga un PDF con esa referencia en el nombre. Ábralo: trae la cabecera del expediente, las líneas con diferencia, las incidencias con su tratamiento y las evidencias.
35. Pulse «Imprimir»: el PDF se abre en otra pestaña, listo para imprimir.
36. Registre otra incidencia en esa recepción y vuelva al expediente: dice «Nueva revisión disponible». Pulse «Emitir nueva revisión». Sale `…-R2` con el mismo número. La R1 no cambia.
37. En «Historial de revisiones» están R2 y R1, cada una con su botón de descarga.
38. En Compras → Recepciones, abra esa recepción: «Reporte formal de diferencias» lista sus reportes, permite descargarlos y abre el expediente con «Abrir expediente IMP-…».

**Límites:** la referencia es interna, no un folio legal. El reporte no se aprueba, no se firma y no se envía al proveedor. Un usuario sin permiso de crear en Compras lo consulta y lo descarga, pero no lo emite.

### Validar la ubicación física y reubicar por error

Necesita mercancía ya ubicada desde el expediente (paso 20) y otra ubicación activa del mismo almacén, creada en Organización. Hace falta un usuario con permiso de crear en Inventario: con permisos solo de Compras se ve la sección, pero no se valida ni se reubica.

39. En «Ubicación», busque «Ubicación física». Cada fila muestra el producto, la recepción, el estado, la cantidad y «Ubicación registrada: A», con su ruta (almacén / zona / … / código). Sin validar, dice «Sin validar».
40. En «Ubicación encontrada», elija la misma ubicación A y pulse «Validar ubicación física». Dice «Coincide · Ubicación física validada». No se mueve nada.
41. Elija ahora la otra ubicación B y valide. Dice «No coincide», «Registrada: A» y «Encontrada: B». Todavía no se mueve nada: la validación solo deja constancia.
42. Pulse «Reubicar por error». El diálogo muestra origen, destino, producto, cantidad y estado. Escriba el motivo (obligatorio) y pulse «Confirmar reubicación».
43. La fila pasa a «Ubicación registrada: B», y la tabla de ubicaciones del expediente muestra B. En Inventario, A baja y B sube en la misma cantidad; el total, el estado y la valoración no cambian.
44. En «Historial de ubicación física» están las dos validaciones (coincide y no coincide) y la reubicación A → B con fecha, usuario y motivo.
45. Si la existencia en A cambió después de validar, la reubicación se rechaza y pide validar de nuevo.

**Límites:** no hay escáner: la ubicación encontrada se elige de la lista de ubicaciones activas del almacén. La reubicación no cambia de almacén; para eso están las transferencias. Hoy no hay pantalla propia en Inventario: la función se usa desde el expediente.

### Clasificación de almacenamiento, zona y etiqueta

Necesita un almacén con el tramo de zona declarado, al menos dos zonas (Organización → Almacenes) con una ubicación activa en cada una, y una importación con mercancía confirmada y pendiente de ubicar (pasos 15 a 19).

46. En Maestros → Almacenamiento, en «Condiciones especiales», cree una condición (por ejemplo, «Frágil»). En «Clases de tamaño» puede crear las clases que use la empresa.
47. En «Perfil de almacenamiento del producto», elija el producto, marque la condición (y, si quiere, peso y volumen con su unidad, y la clase de tamaño) y pulse «Guardar perfil».
48. En «Reglas de almacenamiento» cree una regla: código, nombre, prioridad 1, el almacén, «Tipo de destino: Zona del almacén», la zona, la condición especial y «Etiquetado: Requerida». Pulse «Crear regla».
49. En «Política del almacén», elija el almacén, «Clasificación: Obligatoria» y «Sin regla aplicable: Bloquear la ubicación». Pulse «Guardar política».
50. Abra la importación → «Ubicación» → «Clasificación de almacenamiento». La fila dice «Sin clasificar» y no deja ubicar. Pulse «Clasificar»: verá «Zona determinada: Zona …», la regla aplicada, las razones y «Etiqueta requerida».
51. En «Ubicación de destino» solo aparecen las ubicaciones de esa zona. «Ubicar» sigue bloqueado hasta generar la etiqueta.
52. Pulse «Generar etiqueta» y después «Descargar ETQ-…» o «Imprimir ETQ-…»: es un PDF interno con el producto, la cantidad, la recepción, el expediente, la zona y un QR.
53. Elija la ubicación y pulse «Ubicar …». La mercancía queda en esa ubicación.
54. Pruebe también una regla con «Etiquetado: No requerida» (se ubica sin etiqueta) y un producto sin regla aplicable: con «Bloquear la ubicación» no deja ubicar y lo explica; con «Permitir cualquier ubicación» muestra todas.

**Límites:** la etiqueta es identificación interna, no fiscal, aduanera ni regulatoria. El sistema determina la zona; la ubicación exacta la elige usted. El put-away genérico de Inventario no aplica la política: hágalo desde el expediente. La rotación ya puede ser un criterio de la regla (ver «Planificación de abastecimiento», abajo). Las zonas A a E se pueden configurar, pero su significado debe validarlo el sponsor.

**Aún no disponible:** comparación completa con el documento del sponsor.

## Planificación de abastecimiento y requisición (Spec 015)

Necesita:
- un almacén;
- un producto con existencia;
- algo de demanda en los últimos días. Con la fuente «Salidas de inventario» basta una salida registrada; con «Ventas despachadas», despachos de venta confirmados.

55. En Maestros → Planificación de abastecimiento, cree una política:
    - código y nombre;
    - Alcance: el almacén, o «Toda la empresa»;
    - la fuente de demanda;
    - Días de histórico, Días de horizonte y Plazo de reposición (no hay valores precargados);
    - el stock de seguridad (sin stock, cantidad fija o días de demanda);
    - la métrica de rotación.

    Pulse «Crear política».
56. Cree dos bandas de rotación de la misma métrica, por ejemplo:
    - «Lenta»: Desde 0, Hasta 2;
    - «Rápida»: Desde 2, Hasta vacío.

    Una banda que se solape con otra se rechaza.
57. En Compras → Requisiciones pulse «Nueva requisición», ponga un código, elija el almacén y pulse «Crear requisición». Se abre su detalle.
58. En «Agregar línea» elija el producto. El panel «Planificación del producto» muestra:
    - la política y su versión, y la ventana;
    - la demanda neta, la media diaria y la proyección;
    - el stock de seguridad y el punto de reorden;
    - existencia, reservado y disponible;
    - la cobertura y la banda de rotación;
    - la cantidad sugerida.
59. Pulse «Usar cantidad sugerida». La línea aparece con «Sugerencia aceptada», la cantidad en unidad base, la sugerida, la diferencia 0 y la política con su versión.
60. Agregue otra línea escribiendo una cantidad propia en «Cantidad en unidad base» y pulse «Agregar con esta cantidad». La línea dice «Cantidad manual» y muestra la diferencia frente a la sugerencia.
61. Vuelva a Maestros → Planificación, desactive y active la política (su versión sube). Reabra la requisición: las líneas ya guardadas conservan la versión con la que se calcularon. Las nuevas usan la versión actual.
62. Si la política cambia mientras tiene el panel abierto en otra pestaña, al volver a ella el panel se recalcula con la versión nueva. Si aun así llega una sugerencia calculada con la versión anterior, el sistema la rechaza («La política cambió: revisa la nueva sugerencia») y no la guarda. Ese rechazo lo comprueban las pruebas automáticas, porque en la pantalla es difícil de provocar a mano.
63. Sin política para el almacén, el panel dice que la cantidad se escribe a mano y la línea se guarda igual. Con un producto sin movimientos dice que no hay historia suficiente.
64. En Maestros → Almacenamiento, en «Reglas de almacenamiento», elija una «Banda de rotación» en la regla. La lista muestra «Rotación: …».
65. Al clasificar una recepción (pasos 50 a 53), un producto de esa banda va a la zona de la regla. Uno de otra banda no la usa. Uno sin política o sin historia aparece con el criterio «Banda de rotación» faltante.
66. Un usuario con solo permiso de consulta de Compras ve el detalle y el panel, pero no puede agregar líneas.

**Límites:**
- El cálculo es la media de la ventana: sin estacionalidad, sin estadística avanzada y sin IA.
- El suministro abierto por almacén no se descuenta, y el panel lo dice: las órdenes de compra no tienen almacén.
- No hay costo estimado de la línea.
- El plazo es por política, no por producto ni por proveedor.
- La línea guarda la cantidad en unidad base.
- Las líneas no se editan ni se borran desde esta pantalla.
- La planificación se calcula al consultar; la detección automática de reposición se describe en la sección siguiente.

## Detección automática de reposición (Spec 015)

Detección automática, decisión humana: el sistema avisa, pero no crea requisiciones ni órdenes de compra.

Necesita:
- un almacén;
- un producto con existencia y salidas registradas;
- un paso del planificador del sistema. En producción lo lanza el temporizador del sistema. En esta UAT local **no hay temporizador**: cada paso se lanza a mano con `kontrol.py scheduler-tick` (lo hace P2 cuando la dueña lo pide). Donde abajo dice «tras el siguiente paso del planificador», hay que lanzarlo.

67. En Maestros → Planificación de abastecimiento, cree una política para el almacén y marque «Detección automática de reposición». En una política existente, pulse «Activar detección». La columna «Detección» dice «Activa».
68. Mientras el disponible esté por encima del punto de reorden, el planificador no crea nada.
69. Registre salidas hasta que el disponible quede en el punto de reorden o por debajo. Tras el siguiente paso del planificador, en el Centro de alertas aparece «… requiere reposición en el almacén …». Aunque el planificador pase varias veces, la alerta es una sola.
70. En la alerta, pulse «Abrir origen». Llega a la necesidad, que muestra:
    - «Necesita reposición»;
    - la frase «Se generó porque el disponible (X) era menor o igual que el punto de reorden (Y), con la política … vN»;
    - la demanda, la proyección, el stock de seguridad, la existencia, la rotación y la cantidad sugerida;
    - la situación actual.
71. La lista completa está en Compras → Necesidades de reposición, con filtros por estado, almacén y producto.
72. En la necesidad, pulse «Crear requisición». La nueva requisición llega con el almacén elegido. Póngale un código y pulse «Crear requisición». En el detalle, el producto y la cantidad sugerida vienen cargados: puede cambiar la cantidad y pulsar «Agregar con esta cantidad». La línea muestra «Ver necesidad».
73. Vuelva a la necesidad: en «Requisiciones creadas desde esta necesidad» aparece la suya. La necesidad sigue activa, porque crear la requisición no repone el inventario.
74. Registre una entrada que deje el disponible por encima del punto. Tras el siguiente paso del planificador, la necesidad dice «Resuelta: La condición dejó de cumplirse» y la alerta queda resuelta, sin borrarse.
75. Si el disponible vuelve a caer, nace otra necesidad con otra alerta. La anterior queda en el historial como resuelta.
76. Si apaga la detección de la política, sus necesidades activas se resuelven con «Se apagó la detección automática».

**Límites:**
- No se descuentan las compras en curso por almacén (la orden de compra no tiene almacén).
- El aviso es una alerta: no crea tareas.
- La etiqueta de severidad «Advertencia» del Centro de alertas tiene poco contraste. Es un defecto previo del componente de alertas, informado aparte.

## De la importación al despacho (Spec 018 §4)

Comprueba que la mercancía que entra por una importación sale por la cadena de ventas, sin ningún paso «Liberar» aparte. Una mercancía se puede vender cuando se confirma su inventario: queda en estado Disponible y el pedido liberado la reserva.

Necesita:
- un expediente de importación con su recepción, como en los pasos anteriores de esta tarjeta;
- un segundo usuario que confirme el pedido, porque quien prepara no puede confirmar;
- la serie fiscal y el lote de control de la empresa.

77. Antes de confirmar el inventario de la recepción, lo recibido figura como «Recibido», con disponible para vender 0.
78. Confirme el inventario y ubique la mercancía desde el expediente. Queda «Disponible» en la ubicación elegida.
79. En Ventas → Órdenes, cree un pedido del mismo producto y almacén por una cantidad menor o igual a la importada y emítalo. Queda liberado y con su reserva.
80. En Ventas → Preparación de pedidos, el pedido aparece en la cola. Asigne la ubicación donde quedó la mercancía importada, recoja y consolide en el área de confirmación. La salida del picking queda registrada desde esa ubicación.
81. Con el segundo usuario, en Ventas → Confirmación de pedido, confirme las cantidades.
82. En Ventas → Facturación, solicite, genere y emita la factura.
83. En Ventas → Despacho, el pedido aparece en «Pedidos por despachar». Indique destino y transporte, valide y confirme la salida. El pedido queda despachado y su costo sale del inventario (pasos 85 a 89).
84. En el inventario del producto quedan como Disponible solo las unidades no vendidas; las despachadas figuran como «Despachado». Un pedido por más de lo que queda se rechaza con «No hay disponible suficiente para confirmar el pedido».

**Límites:**
- La ubicación final de cada unidad importada no se atribuye al expediente (deuda IMPORT-PUTAWAY-ATRIBUCION, abierta).

## El despacho descuenta el costo (DISPATCH-COST-RELIEF)

Comprueba que lo despachado sale del valor del inventario, con su costo de importación incluido. No hace falta saber contabilidad: basta con comparar cuatro números antes y después del despacho.

Necesita la importación de los pasos anteriores, con un gasto capitalizable aplicado (por ejemplo, un flete) y todavía sin despachar.

85. En el expediente, pestaña «Costos», anote de la capa del artículo el costo unitario efectivo (el de compra más su parte del flete) y el valor. Ejemplo: 6,000000 USD y 60,00 USD, para 10 unidades.
86. En Inventario → Valorización, anote la valoración total de la empresa. La pantalla no filtra por artículo, así que no haga otros movimientos de inventario mientras dure la prueba.
87. Despache una parte siguiendo los pasos 79 a 83; por ejemplo, 4 unidades.
88. Vuelva a la pestaña «Costos». El valor de la capa del artículo es ahora 36,00 USD: bajó exactamente lo despachado por el costo unitario efectivo (4 × 6 = 24), y lo que queda son 6 unidades. La valoración total del paso 86 baja lo mismo (24).
89. En la misma pestaña, la aplicación del flete ya no se puede revertir: KONTROL no ofrece la acción o la rechaza. La mercancía ya se consumió en parte, y revertir cambiaría el costo de una salida pasada.

**Límites:**
- No se genera un asiento contable de costo de ventas: KONTROL todavía no tiene contabilidad general.
- Los despachos hechos antes de este cambio siguen dentro de la valoración. Corregirlos es una reparación de datos que necesita la autorización de la dueña (deuda DISPATCH-COST-RELIEF-HISTORICO).
- Lo que vuelve de una devolución como Disponible recupera el costo de su salida; lo que se reingresa como Rechazado no se valora (deuda RETURN-REJECTED-VALUATION).

## Comparar ofertas y adjudicar el proveedor (IMP-05)

Comprueba que el proveedor de una compra se elige entre ofertas comparadas y que la orden de compra sale de la oferta elegida, sin volver a escribirla.

Necesita un artículo y dos proveedores activos, dados de alta en Maestros.

90. En Compras → Cotizaciones, «Nueva cotización»: cree una cotización para cada proveedor (código, proveedor y, si quiere, «Válida hasta»).
91. En «Agregar línea», añada a cada cotización el mismo artículo y la misma cantidad, con precios distintos; por ejemplo, 10 unidades a 12 y a 9,50.
92. En «Comparar ofertas», elija ese artículo en «Artículo a comparar». Aparecen las dos ofertas ordenadas por precio, con el proveedor, la cantidad, el precio, el importe (primero 95.00 y después 120.00), la entrega y la vigencia. KONTROL no elige: solo compara.
93. Pulse «Adjudicar» en la oferta elegida, escriba el motivo (por ejemplo, «Mejor precio») y confirme. En la tabla de cotizaciones esa queda «Adjudicada», y ya no se puede adjudicar otra vez. Sin motivo no se adjudica.
94. En la cotización adjudicada pulse «Emitir orden». El código viene propuesto (OC-<código de la cotización>). Confirme y la cotización queda «Orden emitida».
95. En Compras → Órdenes aparece la orden en borrador, con el proveedor, el precio y la cantidad de la oferta. Desde ahí sigue su camino normal: enviar, aprobar según los niveles (Aprobaciones → Mis aprobaciones) y recibir.

**Límites:**
- La cotización no queda ligada a la requisición de la que salió (deuda QUOTE-REQUISITION-LINK).
- La tabla de Órdenes muestra todavía el identificador interno del proveedor y las acciones con su código («submit», «approve»; deuda ORDENES-UI-ETIQUETAS).
- Una cotización vencida se puede comparar, pero no adjudicar.

## Conteo independiente en la recepción (control crítico)

Comprueba que lo recibido lo cuenta una persona distinta de quien lo recibió. Es la regla que usted decidió: quien registra o acepta una recepción no puede contarla. El control está activo por defecto, y la empresa puede desactivarlo de forma auditada.

Necesita dos usuarios de la empresa: el suyo y un segundo usuario con permisos de inventario. Se crea en Seguridad → Usuarios si no lo tiene.

96. Con su usuario, en Compras → Recepciones, registre una recepción de una orden aprobada y llévela hasta «Aceptada» (confirmar, enviar a calidad, conforme y aceptar).
97. En Inventario → Confirmación, elija esa recepción. Arriba se lee: «Conteo independiente activo: quien registró o aceptó la recepción no puede contar sus líneas; debe contarlas otra persona.»
98. Escriba la cantidad en «Contado (base)» y pulse «Registrar conteo». KONTROL lo rechaza con el mensaje «El conteo debe hacerlo una persona distinta de quien registró o aceptó la recepción.». La línea sigue «sin contar» y el inventario no cambia.
99. Salga y entre con el segundo usuario. En Inventario → Confirmación, elija la misma recepción, registre el conteo (esta vez se acepta) y confirme la cantidad. Aparece «Decisiones tomadas» y la mercancía pasa a Disponible.
100. En Seguridad → Auditoría, los eventos «Línea de recepción contada» e «Ingreso a inventario confirmado» de esa recepción tienen como usuario al segundo usuario.
101. (Opcional) En Inventario → Confirmación, sección «Política de conteo», marque «Permitir que quien recibe cuente la mercancía» y pulse «Guardar política». El aviso cambia a «Conteo independiente desactivado por la empresa», y el cambio queda auditado con su valor anterior y el nuevo. Desmárquelo para volver a activar el control.

**Límites:**
- La regla solo separa a quien recibe de quien cuenta. Quien confirma puede ser cualquiera de los dos, porque así lo decidió usted.
- Las recepciones ya confirmadas no se revisan cuando cambia la política.

## Programar la descarga desde la importación (§2)

Comprueba que la descarga se programa desde el propio expediente y que Recepciones ve exactamente la misma fecha.

Necesita un expediente de importación ya despachado y con su orden, como en los pasos anteriores de esta tarjeta.

102. En Compras → Importaciones, abra el expediente. En «Recepción», al crearla, rellene «Descarga programada» con una fecha y hora (hora de Caracas) y pulse «Crear recepción».
103. En la sección «Arribo», la tarjeta de la recepción muestra «Descarga programada:» con la fecha y la hora que eligió, en formato legible.
104. Confirme el arribo. Después, en «Nueva descarga programada», elija otra fecha y hora y pulse «Programar descarga de <código>». La tarjeta muestra la nueva programación. Si pulsa sin elegir fecha, aparece «Indique la fecha y la hora de la descarga.».
105. Recargue la página: la programación sigue ahí.
106. Pulse «Abrir recepción <código>». En Compras → Recepciones, la columna «Descarga programada» de esa recepción muestra exactamente la misma fecha y hora.
107. Siga con la recepción como en los pasos anteriores. Cuando la recepción deja de estar abierta (enviada a calidad o aceptada), la acción de programar desaparece.

**Límites:**
- Se programa la fecha y la hora, que es lo que pide el proceso. No se registran muelle, ventana horaria ni responsable.

## Trazabilidad de la importación hasta la ubicación final

Comprueba que el expediente sabe dónde quedó cada unidad recibida y por qué camino llegó: recepción, colocación y reubicación, con fecha y usuario.

Necesita un expediente con la recepción confirmada en inventario, como en los pasos anteriores de esta tarjeta.

108. En el expediente, sección «Ubicación», ubique la mercancía con «Clasificación de almacenamiento» (pulse «Ubicar Artículo …»).
109. En la misma sección, «Trazabilidad hasta la ubicación final» muestra una fila con la recepción, el producto, el almacén, «Sin ubicar» en «Desde», la ubicación elegida en «Hacia», la cantidad, la fecha y la hora legibles y su usuario.
110. En «Ubicación física», valide la ubicación contra otra distinta y pulse «Reubicar por error» con un motivo. La tabla de trazabilidad añade una segunda fila de la ubicación anterior a la nueva. Las dos filas siguen ahí al recargar.
111. Con otra recepción confirmada y aún sin ubicar, abra Inventario → Put-away, elija el almacén y pulse «Elegir ubicación» en la fila del producto.
112. Aparece «Recepción de origen» con «Sin recepción» seleccionado y una opción «<código> · pendiente <cantidad>». Elija la recepción, la ubicación de destino y una cantidad menor que la pendiente, y pulse «Confirmar ubicación»: aparece «Mercancía ubicada desde la recepción».
113. Vuelva a «Elegir ubicación» en la misma fila: la opción de la recepción muestra ahora el pendiente rebajado en lo que ubicó.
114. Si ubica sin elegir recepción («Sin recepción»), la mercancía se coloca igual, pero no se atribuye a ninguna recepción y su pendiente no cambia.

**Límites:**
- Desde Inventario, la recepción de origen es opcional: si no se indica, el sistema no adivina de cuál vino la mercancía, porque el stock sin ubicar es intercambiable (decisión de la dueña).
- El selector aparece solo para mercancía DISPONIBLE sin lote ni serial.
- Las colocaciones anteriores a este cambio se reconstruyeron solo cuando el código de la recepción coincidía exactamente y sin ambigüedad (decisión de la dueña).

## Condición del proceso de la recepción (§3)

Comprueba que la recepción dice en qué punto del procedimiento está —pendiente de validación, bloqueada por una incidencia o recibida— y que Recepciones y el expediente dicen lo mismo. No es un estado del inventario: la mercancía no cambia de sitio ni de saldo por abrir una incidencia.

Necesita un expediente de importación despachado, como en los pasos anteriores de esta tarjeta.

115. En Compras → Importaciones, abra el expediente y cree la recepción. En la sección «Recepción» de la tarjeta de la recepción, «Condición del proceso» dice «Pendiente de validación».
116. Pulse «Abrir recepción <código>». En Compras → Recepciones, la columna «Condición» de esa fila dice «Pendiente de validación».
117. Reciba una línea y cuéntela (sin confirmar el inventario). La condición sigue en «Pendiente de validación»: contar no valida.
118. Registre una incidencia sobre esa recepción (por ejemplo, un daño) y vuelva al expediente. «Condición del proceso» dice «Bloqueado por incidencia», explica que no se puede confirmar mientras haya incidencias sin resolver y ofrece «Ver la incidencia». En Compras → Recepciones la misma fila muestra el bloqueo.
119. Intente confirmar el inventario. Debe impedirlo con el aviso de incidencias sin resolver.
120. Abra la incidencia con «Ver la incidencia», trátela y resuélvala.
121. Vuelva al expediente. La condición se recalculó sola a «Pendiente de validación»; no hay que pulsar nada más.
122. Cuente y confirme el inventario.
123. La condición pasa a «Recibido», en el expediente y en Compras → Recepciones.
124. Recargue la página: la condición sigue igual, porque se calcula del estado real y no de la pantalla.
125. (Opcional) Antes de confirmar, compruebe en Inventario → Existencias que la mercancía sigue en RECIBIDO: abrir y resolver la incidencia no movió stock ni valoración.

**Límites:**
- La condición es del proceso, no del inventario: no crea estados nuevos de mercancía ni toca capas de costo.
- «Disponible» sigue siendo el estado DISPONIBLE de Inventario → Existencias, que aparece al confirmar.
- Una recepción anulada o rechazada no muestra condición: se rige por su estado documental.
- La condición no se guarda: se deriva de la recepción, su conteo, su confirmación y sus incidencias.

## Zona temporal de recepción o validación (§2)

Comprueba que se registra dónde queda la mercancía mientras se recibe y valida, que se ve igual en Recepciones y en el expediente, y que hacerlo no mueve inventario.

Necesita:
- dos ubicaciones activas del almacén de la recepción, creadas en Organización → Ubicaciones, por ejemplo «Muelle de recepción» y «Zona de validación»;
- un expediente con su recepción creada, como en los pasos anteriores de esta tarjeta.

126. En el expediente, sección «Arribo», la tarjeta de la recepción dice «Zona temporal: Sin registrar».
127. En «Zona temporal de <código>», elija «Muelle de recepción» y pulse «Registrar zona temporal de <código>». La tarjeta muestra la zona elegida. Si pulsa sin elegir, aparece «Elija la zona temporal.».
128. Recargue la página: la zona sigue ahí.
129. Antes y después del paso 127, Inventario → Existencias y Movimientos de ese producto muestran lo mismo: registrar la zona no movió nada.
130. Pulse «Abrir recepción <código>». En Compras → Recepciones, la columna «Zona temporal» muestra la misma zona. En el detalle, cámbiela a «Zona de validación»: la columna se actualiza.
131. Vuelva al expediente: la tarjeta muestra «Zona de validación».
132. Siga con la recepción, el conteo y la confirmación del inventario como en los pasos anteriores. Al confirmar, la zona temporal sigue visible, pero ya no se puede cambiar (desaparece «Registrar zona temporal de <código>»).
133. Ubique la mercancía (sección «Ubicación»). «Trazabilidad hasta la ubicación final» muestra la ubicación final, y la zona temporal sigue aparte, en la tarjeta de la recepción: son dos datos distintos.

**Límites:**
- La zona temporal es una referencia: no crea movimientos, no cambia saldos ni costo y no cuenta como put-away.
- Vale cualquier ubicación activa del almacén de la recepción. Las zonas A a E siguen pendientes de validar por el sponsor y no se usan aquí.
- Cada cambio queda en la bitácora con la zona anterior y la nueva. No se puede vaciar.

## Suministro abierto por almacén (planificación de reposición)

Comprueba que la planificación descuenta lo ya pedido para un almacén y aún no recibido, y que no vuelve a sugerir esas unidades.

Necesita:
- dos almacenes activos (por ejemplo «Central» y «Norte»);
- un producto con una política de reposición activa en «Central», con la detección automática encendida (Maestros → Planificación de abastecimiento);
- un proveedor activo.

134. Deje el disponible del producto en «Central» por debajo del punto de reorden y espere al planificador. En Compras → Necesidades de reposición aparece la necesidad. Su detalle muestra, en «Por qué se generó», «Suministro abierto: 0» y «Disponible proyectado», igual al disponible.
135. Cree la requisición desde la necesidad («Crear requisición»). Después, cree la cotización, adjudíquela y emita la orden (Compras → Cotizaciones).
136. En Compras → Órdenes, pulse «líneas» en la orden. La línea dice «Sin almacén destino: no cuenta en la planificación». Elija «Central» en «Almacén destino de <producto>» y pulse «Fijar destino de <producto>»: la línea muestra «Central».
137. Al agregar una línea nueva a una orden, el formulario exige «Almacén destino». Sin él, no se agrega y avisa «Falta el almacén destino».
138. Envíe y apruebe la orden. En sus líneas, «Pendiente para la planificación» muestra la cantidad pedida.
139. Espere al planificador. La necesidad queda «Resuelta», y en «Situación actual» se ven el suministro abierto y el disponible proyectado (disponible + suministro abierto). No aparece una necesidad nueva por las mismas unidades.
140. Intente recibir esa línea en una recepción de «Norte». Se rechaza con «Esta línea de la orden va a otro almacén; recíbala en una recepción de su almacén destino.». Anule esa recepción.
141. Reciba una parte en «Central» (por ejemplo 5 de 12) y acéptela. «Pendiente para la planificación» baja a lo que falta (7).
142. Cierre la orden (pasa a «CLOSED»). El pendiente queda en 0. Si el disponible sigue bajo el punto de reorden, el planificador abre una necesidad nueva, cuyo detalle muestra «Suministro abierto: 0».
143. Antes y después de los pasos 136, 138 y 139, Inventario → Existencias y Movimientos muestran lo mismo: el suministro abierto no mueve inventario ni costo.

**Límites:**
- Solo cuentan las órdenes aprobadas o parcialmente recibidas, y solo las líneas de inventario que tienen almacén destino.
- Las órdenes anteriores a este cambio no tienen destino y no cuentan hasta que se les fije (si aún son editables).
- El destino se puede cambiar mientras la orden está en borrador, enviada o aprobada y la línea no tiene recepciones. Cada cambio queda en la bitácora.
- Lo aceptado pero aún sin confirmar (estado RECIBIDO) ya no es suministro abierto y todavía no es disponible: la necesidad puede verlo como faltante hasta la confirmación del inventario (deuda RECEIVED-UNCONFIRMED-PROJECTION).
- Una recepción rechazada no descuenta: lo no aceptado sigue pendiente mientras la orden no se cierre.
