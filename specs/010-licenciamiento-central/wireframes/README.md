# WIREFRAMES — 010-LICENCIAMIENTO-CENTRAL

| Campo | Valor |
|---|---|
| Iniciativa | 010-licenciamiento-central |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/010-licenciamiento-central/wireframes/README.md` |

> Maquetas de referencia para el frontend `src/modules/licenciamiento/`. Siguen el patrón DataTable/AsyncButton de la app.

## 1. Configuración central

```
[Licenciamiento ▸ Configuración central]
+--------------------------------------------------------------+
| Servidor central:  [______________________]                  |
| Clave pública:     [______________________]                  |
| Política de sync:  ( ) Manual   ( ) Programada               |
| Gracia offline (días): [ 7 ]                                  |
| [Guardar]                                                     |
+--------------------------------------------------------------+
```

## 2. Sincronización / Estado

```
[Licenciamiento ▸ Sincronización]
+--------------------------------------------------------------+
| Estado: FULL_ACCESS · Última sync: 2026-08-04 12:00 UTC       |
| last_reliable_date: 2026-08-04 · Expira: 2026-12-31          |
| [Sincronizar ahora]                                           |
+--------------------------------------------------------------+
| Historial de sincronización (DataTable)                       |
+--------------------------------------------------------------+
```

## 3. Entitlements por módulo

```
[Licenciamiento ▸ Entitlements]
+-------------------------------------------+
| Módulo      | Entitlement | Versión        |
| Ventas      | ✔           | snapshot v3   |
| Compras     | ✔           | snapshot v3   |
| ...         | ...         | ...           |
+-------------------------------------------+
```

## 4. Renovación

```
[Licenciamiento ▸ Renovación]
+--------------------------------------------------------------+
| Estado: REPORTED · Comprobante: [adjuntar]                    |
| [Solicitar renovación]  [Verificar]  [Emitir / Rechazar]     |
+--------------------------------------------------------------+
| Historial de renovaciones (DataTable)                         |
+--------------------------------------------------------------+
```

## 5. Eventos (auditoría)

```
[Licenciamiento ▸ Eventos]
+--------------------------------------------------------------+
| Fecha | Tipo | Detalle | Usuario | Instalación               |
+--------------------------------------------------------------+
```

> Nota: los wireframes detallados (HTML/Markdown) se añadirán en la fase de implementación si aplica; la ruta documental los resume aquí.
