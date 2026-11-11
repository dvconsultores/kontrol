# SPEC018_RELEASE_TO_PREPARATION_AND_DISPATCH · registro de intentos

Todo con `deepseek-v4-pro` y `stream=true`, con briefs autocontenidos. **Presupuesto:** objetivo 2 llamadas, máximo 4, y máximo 2 reintentos por subproblema. **Usados:** 2 subtareas en 4 envíos.

| # | Subtarea | Entrada/salida (tokens) | Coste | Resultado |
|---|---|---|---|---|
| 1 | Extender la E2E de importaciones hasta el despacho | 10087/4585 | $0,008377 | AUDIT_REJECT. Pasaba objetos falsos con `@ts-expect-error` donde los helpers esperan `APIRequestContext`. La confirmación la hacía el administrador (rompía el maker/checker). Usaba la ruta inventada `/sales/orders/lines` y un POST de empresa inventado. Una variable se usaba antes de declararse. El rango fiscal era fijo. El movimiento se buscaba sin tener en cuenta el signo |
| 1·R1 | Reintento con diseño fijado por Claude (`{ page, request }` y la cadena de `dispatch.spec` copiada) | 12166/3864 | $0,008654 | Aplicados 4 de 5 bloques. El 4 se rechazó porque su SEARCH era una línea de otro fichero. Quedaron una factura obtenida con un GET inventado y una aserción que adivinaba un campo. El puente envió el brief con 83 caracteres menos que el fichero, y entre lo perdido estaban las líneas de `generar` |
| 1·R2 | Correcciones medidas con typecheck, sobre fragmentos | 2245/1633 | $0,002397 | AUDIT_PASS (brief idéntico al fichero). Quedó una variable sin uso, que la llamada 2 resolvió |
| 2 | Ajustar la E2E al contrato medido en Chrome | 2852/2073 | $0,003044 | AUDIT_PASS. E2E PASS a 1280, 390 y 320 |

**Total:** 4 envíos, $0,022472.

**Medido por Claude** con sondas en copias temporales fuera del repositorio:
- lo vendible es solo `DISPONIBLE`;
- la salida pasa a `DESPACHADO`, sin costo;
- la valoración es 50 antes y después del despacho;
- un pedido de 7 recibe 409.

**Implementado por Claude:** ninguna línea de producto ni de prueba. Solo documentos: el delta, la evidencia, la matriz y la tarjeta.

**Errores de Claude:**
- en la auditoría de la llamada 1 marqué como inventado `admintenant`, que existe en la siembra;
- la primera redacción de la tarjeta afirmaba que la cola propone la ubicación, y eso no se midió.
