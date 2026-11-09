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

**En teléfono:** cada acción deja una notificación que se cierra a mano. Hoy pueden tapar botones del pie: ciérrelas con su ✕.

**Aún no disponible:** repartir los gastos entre productos y sumarlos al costo (ciclo 4B); reporte formal de diferencias como documento; clasificación y zonas de almacén, pendientes de validar por el sponsor. Comparación completa con el documento del sponsor: pendiente.
