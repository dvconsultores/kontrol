# N10 — ALCANCE DE LA API

Medido sobre el esquema OpenAPI en ejecución, no sobre el enrutador leído.

| | |
|---|---:|
| Rutas | 294 |
| Operaciones | 404 |
| Declaran la empresa (`X-Kontrol-Company`) | 342 |
| No la declaran | 62 |
| **De alcance indeterminado** | **0** |

Antes de N10 eran 332 y 72. Las **diez** que cambiaron de lado son las rutas a
las que N10 tuvo que dar contexto: cinco de líneas en ventas y compras, la
resolución de líneas de conciliación, la cancelación de solicitudes de
aprobación, la conversión de unidades y los establecimientos —listar y crear.

## Por qué 62 operaciones no la declaran

No es un hueco: es que su alcance no es la empresa. Cada prefijo con su motivo,
y la prueba `test_ninguna_operacion_de_la_api_queda_sin_alcance` exige que toda
operación esté o bien con la cabecera, o bien en esta lista.

| Prefijo | Alcance | Motivo |
|---|---|---|
| `/auth` | sesión | Precede a cualquier empresa |
| `/users` | tenant | La identidad es del tenant. **N10 lo hizo cierto**: antes no filtraba nada |
| `/roles` | instalación | El catálogo de roles es uno |
| `/setup` | instalación | Crea el tenant y la primera empresa |
| `/health`, `/system` | instalación | Sondas y configuración |
| `/license`, `/licensing` | instalación | |
| `/homologation` | instalación | Versión fiscal homologada |
| `/organization` | tenant e instalación | Quedan dos: listar y crear empresas. El selector precede al contexto. Sucursales y establecimientos **sí** la declaran desde N10 |
| `/audit` | tenant | La bitácora se consulta por tenant |

Y diez operaciones sueltas de módulos de empresa, cada una justificada:

- `/fiscal/legal-sources` y `/fiscal/tax-rule-versions` (6 operaciones): el
  núcleo fiscal está separado y versionado por instalación (P4). Una empresa no
  activa una gaceta ni aprueba una alícuota.
- `/approvals/steps/{id}/(approve|reject|return)`: la decisión no la acota la
  empresa sino la elegibilidad, y **N10 corrigió esa elegibilidad**, que
  ignoraba la empresa que se le pasaba.
- `/documentos/salud/almacenamiento`: sonda de almacenamiento.

## Paridad ejecución ↔ OpenAPI

Cero desviación: la cabecera se declara en la dependencia
`get_company_context`, de modo que la ruta que la exige es exactamente la que la
publica. No hay una segunda lista que mantener sincronizada.
