# EL FIXTURE HOSTIL — N8

## 1. Era un recuerdo

La base `kontrol_legacy` se sembró en una sesión anterior con comandos ad hoc y
desapareció al borrarse el directorio temporal. Desde entonces, las dos pruebas
que la usan se saltaban con el mensaje «no hay base legacy sembrada en este
entorno».

Un fixture hostil que no se puede reconstruir no es un fixture. Y mientras se
saltaba, ocultó durante toda la fase N7 que el clasificador había quedado ciego.

## 2. Ahora es un artefacto

`qa/n4-legacy-hostile-seed.py` lo reconstruye desde cero, y está versionado.

## 3. Qué siembra, y por qué cada caso es difícil

| Caso | Qué se siembra | Por qué es difícil |
|---|---|---|
| `MC-A` | Tercero de un tenant que solo tuvo una empresa cuando se creó la fila | Se resuelve por **intervalo temporal**, no por el recuento de hoy: un tenant que hoy tiene una pudo tener dos el año pasado |
| `MC-B` | Saldo de inventario sin empresa propia, con almacén | La evidencia del dominio pesa más que el recuento de empresas |
| `MC-C` | Tercero creado **después** de que el tenant tuviera dos empresas | Hay dos candidatas y ninguna razón para preferir una |
| `MC-E` | Serie fiscal ambigua | En fiscal no basta con decir «ambiguo»: atribuir una serie a la empresa equivocada emite facturas a nombre de otro contribuyente |
| `OK` | Tercero que ya tenía su empresa | No debe reclasificarse |

## 4. El esquema se detiene en `0032` a propósito

Una instalación heredada **no tiene** las claves foráneas que N7 añadió. Sembrar
sobre el esquema final haría que la base rechazara justamente las filas
inválidas que hacen falta, y el fixture dejaría de ser hostil.

## 5. Resultado tras el cleanup de N8

Las **23 pruebas** del preflight se ejecutan y pasan, con las columnas
transitorias ya retiradas. El clasificador distingue los cinco casos, no escribe
nada, es repetible y no rebaja de clase ninguna fila crítica.

## 6. Lo que no se hizo

No se «limpió» el fixture. Contiene a propósito el defecto histórico de KONTROL
—`company_id` guardando el identificador del tenant— porque esa es exactamente
la forma que tendrá una instalación real que algún día haya que migrar.
