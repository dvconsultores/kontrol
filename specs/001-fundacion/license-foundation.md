# FUNDACIÓN DE LICENCIAMIENTO — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Responsable | Arquitecto de seguridad / Producto |
| Ruta | `specs/001-fundacion/license-foundation.md` |
| Fuente | DOC-07 (autoridad) |

## 1. Modelo

- Instalación independiente por cliente (ADR-002).
- Autoridad de licencia: propietario de KONTROL (alta, activación, renovación, derechos, suspensión, revocación, sustitución).
- Administración local: empresa, sucursales, usuarios, roles, operaciones; sin poder modificar licencia.
- Firma asimétrica Ed25519 (ADR-005); clave privada solo en la autoridad central.

## 2. Identidad de instalación

- `installation_uuid` + par de claves local generado al primer arranque.
- Persistencia en volumen protegido; persiste ante recreación de contenedores, reinicio de Docker y actualización de imagen.
- Clave privada local nunca se envía.

## 3. Modos de acceso

| Modo | Comportamiento |
|---|---|
| FULL_ACCESS | Operación completa |
| RENEWAL_NOTICE | Operación completa + aviso (desde 1 de abril) |
| CRITICAL_RENEWAL_NOTICE | Operación completa + aviso crítico (desde 21 de abril) |
| READ_ONLY | Consulta, reportes, exportación, reimpresión controlada, carga de comprobante; escritura bloqueada (desde 1 de mayo) |
| SECURITY_SUSPENSION | Firma inválida/manipulación; no aplicar paquete |

## 4. Ciclo anual

1 de abril inicio · 31 de marzo fin · gracia hasta 30 de abril · crítico desde 21 de abril · solo consulta desde 1 de mayo · reactivación inmediata al confirmar.

## 5. Reglas

- El pago reportado no equivale a renovación; solo la confirmación del propietario y la nueva licencia firmada renuevan.
- El reloj del navegador/SO/contenedor no decide; se usa fecha del servidor + última fecha confiable.
- El middleware de licencia bloquea WRITE antes de abrir transacción y antes de reservar correlativos.
- La expiración nunca elimina ni cifra destructivamente los datos del cliente.
- El modo solo consulta no detiene PostgreSQL ni impide respaldos.
- Plan monoempresa vs multiempresa según entitlement.

## 6. Subsistema local (001)

- Verificar firma; importar licencia (online/offline); consultar estado/historial; cargar comprobante; sincronizar.
- Pantalla Mi licencia (ruta completa, no modal).
- Respuesta de bloqueo HTTP 423 (`LICENSE_READ_ONLY`).

## 7. Portal central

Fuera de alcance de 001 → `010-licenciamiento-central`.

## 8. Privacidad

- La autoridad central no almacena facturas, inventario, clientes, proveedores ni operaciones del cliente.
- Soporte remoto solo con autorización expresa y sesión trazable.
- Paquetes de diagnóstico sanitizados por defecto.

## 9. Estado

| Elemento | Estado |
|---|---|
| Fundación de licenciamiento | ✔ |
| Aprobación | Pendiente |
