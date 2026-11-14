# OMA · Ficha de pantalla

**Ruta.** Menú › Gobierno › Expedientes de contratación › un expediente › sección «Ofertas» › «Ver detalle de R-000N» › bloque «Monto declarado».

| Elemento | Contenido | Regla |
|---|---|---|
| Resumen de la oferta (dt «Monto») | «1160.00 VES (total con tributos)», o el estado: «Sellada: el monto se registra después de la apertura», «No declarado» o «No aplica: el sobre de calificación no lleva precio» | Sin cálculos: el texto viene de la API |
| Bloque «Monto declarado» | Moneda; monto del objeto sin IVA; tributos; total con tributos; documento soporte (tipo · título · versión); registro (versión · usuario · fecha) | Sin UUID |
| Nota de incoherencia | «La suma declarada no coincide con el total (diferencia X VES).» (`role="note"`) | Solo se señala; no se corrige |
| Bloqueo | El motivo: sellada sin apertura, expediente no en curso o evaluación concluida | Sin botón cuando hay bloqueo |
| Botón | «Declarar monto» o «Corregir monto» | Pide `gobierno_ofertas:amount` |
| Formulario | Moneda (VES, USD, EUR); 3 importes como texto; documento soporte (de la oferta o acta de apertura); en la corrección, motivo de 10 caracteres o más | Errores debajo de cada campo; si cambió la versión: «El expediente o el monto cambió; recargue la oferta» |
| Historial | Una línea por versión: total, moneda, usuario, fecha y motivo | Con 2 versiones o más |
| Decisión (PROC-08) | Columna «Monto declarado» en «Ofertas evaluadas» | Solo muestra el monto; no valida límites (OQ-OMA-01) |
| Reporte (REP-03) | Sección «Monto»: tabla por moneda con total con tributos, monto sin IVA y adjudicaciones; además, las adjudicaciones sin monto y una nota | La tabla se desplaza dentro de una región accesible |

**Responsive:** 1280, 390 y 320 px, sin desplazamiento horizontal de la sección. **Accesibilidad:** Axe sin violaciones en la sección de ofertas, en los 3 anchos.
