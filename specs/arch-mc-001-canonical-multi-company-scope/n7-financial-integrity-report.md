# INTEGRIDAD FINANCIERA — N7

## 1. Estructura

| Entidad | Empresa | Estado |
|---|---|---|
| Bancos y cuentas | directa | clave real, obligatoria |
| Transacciones bancarias | directa | clave real, obligatoria |
| Cajas y sesiones | directa | clave real, obligatoria |
| Movimientos de sesión | derivada de la sesión | clave real, obligatoria |
| Conciliaciones y líneas | directa / derivada | claves reales |
| Pagos y cobros (`ap_payments`) | directa | clave real, obligatoria |
| Aplicaciones (`ap_applications`) | directa | clave real, obligatoria |
| Documentos abiertos (`ap_open_items`) | directa | clave real, obligatoria |
| Anticipos, retenciones, calendarios | directa | claves reales |

## 2. Lo que la base rechaza ahora

Un pago bajo una empresa inexistente: `23503`. Un pago sin empresa: `23502`.
Comprobado con `INSERT` directo.

## 3. Lo que la base sigue sin poder decidir

Que un pago de la empresa B no cancele la deuda de la A. Ambos objetos existen,
ambas referencias son válidas y la combinación es la que está mal.

Una clave foránea no expresa esa regla. La guarda que N5 añadió a `apply_source`
sí, y **sigue donde estaba** con sus pruebas en las dos direcciones del cruce.

N7 añade una capa; no retira ninguna. Confundir las dos garantías —creer que la
estructura hace innecesaria la guarda— sería el error que deja la puerta abierta.
