# Tarjeta de prueba de la dueña

**Dirección:** http://127.0.0.1:5173, en el equipo de P2. **Acceso:** fichero local protegido, nunca en Git. **Datos:** sintéticos.

**Límites conocidos:** la pila usa SQLite y Vite, no PostgreSQL ni el empaquetado de producción. Solo es accesible desde ese equipo. El bloqueo de pago a proveedores no aprobados afectará a los proveedores existentes cuando se despliegue: decisión pendiente.

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

**Aún no disponible:** seguimiento del embarque, agente, despacho, recepción desde el expediente y costos de importación.
