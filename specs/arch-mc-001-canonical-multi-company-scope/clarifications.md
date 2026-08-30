# ACLARACIONES — ARCH-MC-001

Resueltas contra la autoridad existente. Solo se eleva lo que ninguna decidía.

## CL-MC-01 · ¿Cómo viaja el contexto de empresa?

**Cabecera explícita por petición.** Razonado en `research.md` §1: es el único de
los cuatro modelos que resuelve dos pestañas en empresas distintas sin tocar la
renovación de sesión ya remediada.

## CL-MC-02 · ¿Y si el usuario tiene una sola empresa?

Se resuelve automáticamente (`FR-MC-013`). Pedir elegir entre una opción es
fricción sin información. El backend sigue usando la empresa real: la comodidad
es de la interfaz, no del dato.

## CL-MC-03 · ¿Y si tiene varias y no manda cabecera?

La operación de empresa se **rechaza** con un error explícito.

Se consideró elegir «la primera» o «la última usada». Se descarta: una factura
emitida por la empresa equivocada porque el sistema adivinó es exactamente el
daño que esta remediación evita.

## CL-MC-04 · ¿De dónde sale el acceso del usuario a una empresa?

De `UserScope`, que ya existe con `company_id` anulable, y de `user_roles`, que
también lo tiene. **No se crea un sistema paralelo** (`FR-MC-031`).

Hoy ninguna de las dos se usa para esto. Adaptarlas es trabajo de esta
remediación; sustituirlas, no.

## CL-MC-05 · ¿Pertenecer al tenant da acceso a todas sus empresas?

**No** (`FR-MC-030`). Sería reproducir el defecto en la capa de permisos: un
usuario de nóminas de la empresa A no tiene por qué ver la tesorería de la B.

Para instalaciones existentes con una sola empresa, el backfill de accesos es
determinista: todos los usuarios del tenant acceden a la única empresa.

## CL-MC-06 · ¿Directa o derivada?

Directa si la entidad es cabecera o maestro. Derivada si existe FK **obligatoria**
a una autoridad de empresa.

Medido: las 36 derivadas lo hacen por FK no anulable. Ninguna depende de una
relación que pueda faltar, que es lo que el §11 exige.

## CL-MC-07 · ¿Qué se hace con una fila histórica ambigua?

Se **anota y se detiene**, nunca se adivina (`FR-MC-051`). Si es fiscal,
financiera o de inventario, **bloquea** la migración final (`FR-MC-053`).

Es la misma decisión que la Spec 046 tomó con el legado documental, y la Spec 011
con el backfill de unidades.

## CL-MC-08 · ¿Basta con que hoy el tenant tenga una empresa?

**No** (`FR-MC-052`). Hay que demostrar que tuvo una sola durante el **intervalo**
en que se creó la fila. Un tenant que creó su segunda empresa en marzo tiene
filas deterministas antes y ambiguas después.

Por eso hace falta reconstruir el histórico de creación de empresas y calcular,
por tenant, el instante en que dejó de ser monoempresa.

## CL-MC-09 · ¿La licencia limita el esquema?

**No** (`FR-MC-035`). El esquema es multiempresa siempre. La licencia limita
cuántas empresas se pueden **crear y operar**. Degradar el esquema por el plan
comercial reproduce el defecto en cuanto alguien cambie de plan.

## CL-MC-10 · ¿Qué pasa con el plan `MONO_COMPANY` actual?

Hoy no se impone: se creó una segunda empresa con ese plan. El backend pasa a ser
autoridad (`FR-MC-034`). No se inventan planes ni límites nuevos: se **aplica** el
que ya existe.

## CL-MC-11 · ¿La auditoría histórica se migra?

Se clasifica igual que las transacciones. Un evento cuya empresa no sea
reconstruible **se queda sin ella**, anotado. Inventar la empresa de un evento de
auditoría sería falsificar el registro que existe para no falsificar nada.

## CL-MC-12 · ¿Las 14 tablas del tenant cambian?

Siete renombran `company_id` a `tenant_id` con FK real: hoy su nombre miente.

Tres —`user_roles`, `user_scopes`, `audit_events`— son filas del tenant cuyo
`company_id` **sí** designa una empresa: esa columna pasa a FK real. No es
contradicción: la fila es del tenant, el alcance que expresa es de empresa.

## CL-MC-13 · ¿Y `units_of_measure`, que hoy es única por `(company_id, code)`?

Su índice único acota hoy por tenant. Tras normalizar, acotaría por empresa: cada
empresa necesitaría su propio «KG».

**Se eleva.** Es una decisión de producto sobre si el catálogo de unidades es del
tenant o de la empresa. La Spec 011 lo trató como catálogo; el modelo permite
ambas. Ver `OQ-MC-01`.

---

## Elevado

| Id | Pregunta | ¿Bloquea? |
|---|---|---|
| **OQ-MC-01** | ¿`units_of_measure`, `movement_types` y otros catálogos con único por `(company_id, code)` son del tenant o de la empresa? | **No** para especificar; **sí** para migrar esas tablas concretas |
| **OQ-MC-02** | Con acceso a varias empresas, ¿el selector recuerda la última por usuario y dispositivo, o arranca siempre sin elegir? | No |

`OQ-MC-01` afecta a un puñado de catálogos, no al diseño. La clasificación los
marca y la ola correspondiente no se ejecuta hasta responderla.
