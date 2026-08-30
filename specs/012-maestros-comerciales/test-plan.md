# PLAN DE PRUEBAS — SPEC 012

## 1. Qué hay que demostrar

No que las tablas existen. Tres cosas:

1. Que el precio **sale del maestro** y se puede explicar.
2. Que la precedencia **es dato** — reordenarla cambia el resultado.
3. Que cambiar el maestro **no reescribe la historia**.

Si las tres se cumplen, la Spec sirvió. Si no, no.

## 2. Unidad

| Bloque | Casos |
|---|---|
| Precedencia | Cliente gana a segmento; segmento a empresa; reordenada, cambia el resultado |
| Desempate | Vigencia más reciente; a igualdad, menor precio |
| Empate irresoluble | 422 con los candidatos |
| Ausencia | `resolved:false`, `unit_price:null`, **nunca** cero |
| Presentación | Precio por caja convertido a unidad con el motor de la Spec 011 |
| Volumen | Dentro y fuera de rango |
| Vigencia | Antes de `valid_from`, dentro, después de `valid_to` |
| Descuento | Bajo límite, sobre límite, sin política, incompatibles |
| Condición de pago | Los cuatro tipos y los tres desplazamientos |

## 3. Integración — sobre PostgreSQL 18.x

| Caso | Qué se comprueba |
|---|---|
| Solapamiento de vigencias | La **restricción de base** lo impide, no solo el servicio |
| Dos activaciones concurrentes | Una sola prospera |
| Borrado de versión referenciada | 409 con el recuento |
| Aislamiento multiempresa | La resolución de A nunca ve listas de B |
| Snapshot inmutable | Editar la lista tras aprobar no cambia el documento |
| Versión nueva tras aprobar | Tampoco lo cambia |

## 4. Legado

Fixture con las seis clases: vacío, determinista, ambiguo, revisión manual,
reconstruible y bloqueante. Se comprueba que la migración **anota** las seis y
**no convierte** ninguna, y que sus tres invariantes quedan en 0.

## 5. E2E — pila real

| Escenario | Qué demuestra |
|---|---|
| Crear lista, versión e ítems; resolver un precio | El camino completo por la interfaz |
| Ver el origen del precio en pantalla | Que se puede **explicar**, no solo mostrar |
| Cambiar la lista y comprobar el documento aprobado | `P5` visible para el usuario |
| Descuento excesivo → aparece la aprobación | Integración con 045 sin vía paralela |
| Reordenar la precedencia y volver a resolver | `P8` visible para el usuario |

Cross-browser en Chromium, Firefox y WebKit. axe en las cinco pantallas.
Responsive en 6 viewports.

## 6. Verificación por comando

| Comprobación | Valor exigido |
|---|---:|
| Porcentajes, plazos o nombres de lista en el módulo | 0 |
| `float` en importes | 0 |
| Cálculos de precio fuera de `pricing.py` | 0 |
| Filas en los catálogos tras instalar | 0 |
| Permisos, auditoría o aprobaciones propios | 0 |

## 7. Lo que no se prueba aquí

Cotización, pedido, facturación, cobranza y comisiones. No son de esta Spec, y
probarlas aquí sería ampliarla por la puerta de atrás.
