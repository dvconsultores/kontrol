# REGRESIÓN — N8

## 1. Lo que N8 tocó, y lo que podía romper

Cinco cambios con riesgo distinto:

| Cambio | Riesgo | Resultado |
|---|---|---|
| Desacoplar `planes()` del ORM | El clasificador podía quedar peor | 23 pruebas del preflight en verde |
| Retirar el repliegue de almacén | Cuatro dominios lo llamaban | Inventario, compras, ventas y tesorería en verde |
| Declarar la cabecera | Cambia la firma de una dependencia usada en 332 operaciones | Sin cambios de comportamiento |
| Retirar 160 columnas | Podía romper migraciones o pruebas | Instalación limpia en 38 migraciones |
| Retirar `setActiveCompany` | Lo usaba una pantalla | Frontend en verde |

## 2. El cambio de firma que no cambió nada

Declarar la cabecera convierte `get_company_context` en una dependencia con un
parámetro más. FastAPI la inyecta igual y el valor resuelto es el mismo, pero la
diferencia importa: antes el dato entraba por un canal que el contrato no veía.

Las 112 pruebas que ya usaban la cabecera pasaron sin tocarse, que es la
comprobación de que el comportamiento no se movió.

## 3. Regresiones mantenidas

| Fase | Qué se comprueba | Resultado |
|---|---|---|
| N5 | Los once defectos históricos, 045 y 046 | PASS |
| N6 | Contexto por pestaña, caché, formularios, selector, manipulación | PASS |
| N7 | Claves foráneas, obligatoriedad, unicidad, derivadas, corrupción por SQL | PASS |
| N4 | Clasificador, fixture hostil, cero escrituras, repetibilidad | PASS |

## 4. Fixture hostil, después del cleanup

Se ejecuta **después** de retirar las columnas, que es el orden que importa: si
se hubiera comprobado antes, no probaría lo que N8 promete.

## 5. Skips

Dieciséis antes, catorce después. Los dos que desaparecieron son los del
preflight de N4, que ahora corren de verdad.

Los catorce restantes son entorno o servicio externo, cada uno con su
dependencia nombrada. Ninguno oculta trabajo de N8.
