# N8 — CHECKPOINT DE CONTRATO Y RETIRADA

PostgreSQL **18.6** en UTC · head `0037` → `0038` · ciclo Spec completo

## 1. Qué cierra la fase

N7 dejó la estructura correcta. N8 retira lo transitorio del producto activo y
escribe el contrato que faltaba, **sin destruir la capacidad de entender y
migrar una instalación heredada futura**. Son dos cosas distintas y la fase se
jugaba en no confundirlas.

## 2. Lo que resultó ser fácil

Las columnas de transición **nunca llegaron al modelo**. N3 las añadió a 80
tablas como red de seguridad para un backfill, N4 concluyó que no había nada que
migrar, y entre una cosa y otra nadie las conectó.

| | |
|---|---:|
| Lecturas en runtime | 0 |
| Escrituras en runtime | 0 |
| Atributos ORM que retirar | 0 |
| Columnas retiradas del esquema | **160** |

No hubo lectura ni escritura doble que desmontar. Conviene decir por qué: no es
un logro de N8, es la consecuencia de haber cerrado la ventana antes de que
hubiera una instalación desplegada.

## 3. Lo que resultó ser el trabajo real

**El clasificador de N4 había quedado ciego después de N7.**

`planes()` decidía qué tablas revisar excluyendo las que ya tenían clave
foránea. Tras N7 las tienen todas, así que devolvía **cero planes**. Contra una
instalación heredada —que no las tiene— habría respondido «no hay nada que
revisar» a una base llena de filas que sí había que revisar.

La herramienta que la Spec 052 necesita para decidir si una actualización es
segura estaba rota, y en silencio.

**Y dos skips lo ocultaban.** Las pruebas del fixture hostil se saltaban porque
la base heredada se sembró en una sesión anterior y desapareció al borrarse el
directorio temporal. Un fixture hostil que no se puede reconstruir no es un
fixture: es un recuerdo.

## 4. Cómo se corrigió

`planes()` acepta una conexión al destino y le pregunta a **su** catálogo. La
división es deliberada:

| Qué | De dónde | Por qué |
|---|---|---|
| Qué entidad es de empresa, y por qué autoridad deriva | Modelos | Semántica del dominio: no cambia entre versiones |
| Si su propiedad ya está garantizada | **Catálogo del destino** | Eso sí cambia entre versiones |

Y el fixture pasó a ser artefacto: `qa/n4-legacy-hostile-seed.py` reconstruye la
base heredada desde cero, con esquema en `0032` —una instalación heredada no
tiene las claves de N7— y las filas que el clasificador debe distinguir sin
adivinar.

**32 pruebas del preflight**, ejecutándose de verdad, después de retirar las
columnas.

## 4.1 Sello final de evidencia

El primer cierre de N8 escribió «MC-A/B/C/E y OK preservadas», que era cierto y
no era suficiente: `MC-D` no tenía semilla, e `INVALID_LEGACY_SCOPE` y
`CROSS_TENANT` solo tenían aserciones sobre el valor del enum. Un nombre no es
una capacidad.

Al exigir ejecución real aparecieron **dos defectos**:

**`CROSS_TENANT` no se emitía nunca.** Una fila con empresa real pero de otro
cliente entraba por la primera rama —«¿ya tiene empresa? entonces nada que
hacer»— y se marcaba `OK`. `cross_tenant()` existía con `LIMIT 0` y un comentario
que la declaraba plantilla; nadie la llamaba.

**Las estrategias de maestro no se calculaban.** `MAESTROS` estaba definido y sin
usar, y `MASTER_DERIVE` no podía devolverse porque la función solo recibía el
conjunto de empresas, donde «se deduce por una relación obligatoria» no cabe.

Resultado tras corregir ambos, sobre el fixture hostil versionado:

```
MC-A                    PASS   (3 filas)
MC-B                    PASS   (1)
MC-C                    PASS   (2)
MC-D                    PASS   (1)
MC-E                    PASS   (1)
INVALID_LEGACY_SCOPE    PASS   (1)
CROSS_TENANT            PASS   (1)
OK                      PASS   (6)

MASTER_ASSIGN           PASS   (7)
MASTER_CLONE            PASS   (1)
MASTER_DERIVE           PASS   (1)
MASTER_MANUAL_REVIEW    PASS   (5)
```

Cada uno con clasificación correcta, cero escrituras y resultado repetible.
`INVALID` y `CROSS_TENANT` conservan severidad propia y no se degradan a `MC-D`.

## 5. El último repliegue

`warehouse_in_tenant_scope` reconciliaba tenant y empresa, y su docstring lo
describía como diseño vigente. Desde N2 sus cuatro llamantes pasaban la empresa
real, así que la reconciliación era código muerto que funcionaba **por
accidente**: si un identificador de empresa hubiera coincidido con uno de
tenant, habría aceptado el almacén equivocado.

Sustituido por `warehouse_belongs_to(company_id, warehouse)`, que comprueba lo
único que había que comprobar.

## 6. El contrato que faltaba

`X-Kontrol-Company` funcionaba desde N1 y la usaban 112 pruebas, pero la
dependencia la leía del `Request` en lugar de declararla. Quien leyera el
contrato no sabría que existe.

| | |
|---|---:|
| Rutas | 294, sin cambios |
| Operaciones que la declaran | **332** |
| Operaciones que no | 72 |

Se declara **opcional**, con la razón escrita: el servidor la resuelve solo
cuando el usuario puede operar en una sola empresa. Decirla obligatoria
describiría un sistema distinto, y quien leyera el contrato enviaría siempre una
cabecera que a veces sobra.

Y hay una sola lectura del valor. Dos serían dos autoridades sobre la misma
decisión.

## 7. Nulos legítimos, no eliminados

Once columnas admiten empresa nula y las once tienen semántica documentada:
unidades del sistema, archivos anteriores a su documento, tipos de movimiento y
perfiles de costo con alcance global, roles que valen en todas las empresas.

N7 endureció dos de ellas por inercia y hubo que revertirlo. N8 no repite el
error: la matriz de nulos existe precisamente para que «admite nulo» no se lea
como «le falta algo».

## 8. Estado

| | |
|---|---|
| Backend | **0 fallos**, 8 skips |
| Skips | de 16 a 8, todos por ausencia de S3 |
| Frontend | 278/278, tsc, eslint, build |
| OpenAPI | 294 rutas, 332 con cabecera declarada |
| Instalación limpia | 38 migraciones |
| SQL sin conexión | 160 sentencias revisables |
| Clasificador y fixture hostil | **32 pruebas** en verde |
| N5, N6, N7 | sin regresión |

## 9. Deuda de N8

**Ninguna.** No queda repliegue activo, lectura ni escritura doble, columna
transitoria en el esquema operativo, ni contrato que mienta sobre el contexto.

La capacidad de migración no solo se conserva: **mejora**. El clasificador ya no
depende del modelo de la versión que lo ejecuta, que era la limitación
registrada al cerrar N7.

## 10. Veredicto

**`ARCH-MC-001 — N8 COMPLETE / N8 CONVERGED`**

`SPEC 012 APTA_DOCUMENTALMENTE — BLOCKED_BY_ARCH_MC_001`
`REM-046-001 BLOCKED_BY_ARCH_MC_001`
`N4 Real Backfill — NOT_APPLICABLE — NO DEPLOYED LEGACY INSTALLATIONS`

N9 y N10 quedan pendientes y no se inician.
