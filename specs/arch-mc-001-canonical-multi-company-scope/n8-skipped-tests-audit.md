# AUDITORÍA DE PRUEBAS SALTADAS — N8

Dieciséis skips en quince puntos del código. Ninguno puede quedar sin explicar.

| Prueba | Motivo | Dependencia | Categoría | ¿De N8? | Acción |
|---|---|---|---|---|---|
| Aislamiento multiempresa | Motor no es PostgreSQL | PostgreSQL 18.6 | Entorno | No | Se ejecuta con el motor real |
| Estructura de N7 | Ídem | Ídem | Entorno | No | Ídem |
| Corrupción por SQL directo | Ídem | Ídem | Entorno | No | Ídem |
| Estructura de almacén | Ídem | Ídem | Entorno | No | Ídem |
| SQL sin conexión (×3) | Alembic ausente | Alembic | Entorno | No | Se ejecuta con Alembic instalado |
| Análisis antivirus | Escáner desactivado | ClamAV | Servicio externo | No | Se ejecuta con ClamAV aprovisionado |
| Clasificación de SVG | libmagic no lo distingue | libmagic | Servicio externo | No | Limitación de la biblioteca |
| Almacenamiento real | Sin servicio compatible con S3 | S3 | Servicio externo | No | Fuera del alcance de N8 |
| Cadena documental | No incluye ese campo | — | No aplicable | No | Correcto |
| **Preflight de N4 (×2)** | **No hay base heredada** | **Fixture hostil** | **Requisito oculto** | **Sí** | **Resuelto** |

## Los dos que importaban

Las pruebas del fixture hostil se saltaban porque la base `kontrol_legacy` se
sembró en una sesión anterior y desapareció al borrarse el directorio temporal.

Un fixture hostil que no se puede reconstruir no es un fixture: es un recuerdo.
Y mientras se saltaban, ocultaban que el clasificador de N4 había quedado ciego
tras N7 — el hallazgo material de esta fase.

Resuelto creando `qa/n4-legacy-hostile-seed.py`, que reconstruye la base desde
cero. Las **23 pruebas** del preflight ahora corren y pasan.

## Resultado medido con el entorno completo

Con PostgreSQL 18.6, Alembic y ClamAV aprovisionados, la regresión final deja
**8 skips**, todos del mismo sitio:

```
8 × test_documents_storage.py → KONTROL_S3_ENDPOINT no está configurado
```

Es un único motivo: no hay servicio compatible con S3 en este entorno, y el
propio mensaje lo dice sin adornos — «la conformidad de este adaptador queda
SIN VERIFICAR».

Los otros ocho de la lista inicial no eran skips permanentes sino falta de
entorno: seis dependían de PostgreSQL o Alembic y dos del antivirus. Con las
dependencias presentes, se ejecutan.

```
N8_REQUIREMENT_HIDDEN_BY_SKIP : 0
```

## Sobre no convertir skips en verdes artificialmente

La prueba de almacenamiento con S3 real sigue saltándose, y debe seguir así:
N8 no requiere S3, y montar un servicio para que un contador diga «0 skips»
sería cambiar la medida en vez del sistema.

Lo que no se admite es un skip sin dueño.
