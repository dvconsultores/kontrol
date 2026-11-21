# Delta · BUD-02-CLASSIFIER-PARENT-LEVEL · el padre de una partida es del nivel inmediatamente anterior

- **Spec dueña:** BUD-01 + BUD-02 (este directorio).
- **Encargo:** «P2 — BUD-02 · Validación de jerarquía del clasificador presupuestario» (2026-11-20).
- **Autorización de implement:** la del encargo.
- **Entrada:** b726c1da, cabeza Alembic 0128_gov_tre04_pago.
- **Migración:** ninguna.

## Defecto

- BUD12-06 dice: «padre del mismo tipo y nivel −1».
- `_validar_partida` (`service_presupuesto.py`) comprobaba solo que existiera una partida con ese `(tipo, codigo)`. El mapa `existentes` no guardaba el nivel.
- Por eso una partida de nivel 3 aceptaba como padre una de nivel 1, de nivel 3 o de nivel 4, tanto en el alta (201) como en la importación CSV (200).
- La auditoría de parametrización registraba el defecto en BUD-02 (CURRENT_PRODUCT_DEFECT=YES).

## Arqueología

| Elemento | Hallazgo |
|---|---|
| LEVEL_FIELD | `GovernmentBudgetClassifierItem.nivel`, SmallInteger, con CHECK `nivel BETWEEN 1 AND 12` |
| PARENT_FIELD | `parent_id`, FK a la misma tabla. El cliente envía `codigo_padre` y el servidor lo resuelve a id |
| CLASSIFIER_VERSION_FIELD | `classifier_id`. Hay un clasificador por ejercicio (`year_id` UNIQUE): la versión del clasificador **es** el clasificador del ejercicio |
| TYPE_FIELD | `tipo` (RECURSO o EGRESO). El padre es del mismo tipo (BUD12-06) |
| CURRENT_PARENT_VALIDATION | Existencia de `(tipo, codigo)` en el clasificador del ejercicio, sin nivel |
| CURRENT_IMPORT_VALIDATION | La misma función, fila a fila. Las filas válidas se suman al mapa, de modo que el padre puede venir del mismo lote siempre que vaya antes. Todo o nada |
| CURRENT_UI_VALIDATION | Ninguna. «Código superior» es un campo de texto libre, no un selector |
| Edición | No existe: las partidas solo se dan de alta, se eliminan sin hijas o se importan. Padre y nivel son inmutables |
| Consumidores | BUD-03/04, BUD-05, BUD-06, BUD-08, BUD-09, CNT-01, CNT-03, TRE-09. Leen partidas por id; ninguno valida la jerarquía |

## Decisiones

- **D-CPL-01. Una sola regla.** `validar_padre_partida(tipo, nivel, codigo_padre, niveles)` es la única autoridad (CLASSIFIER_PARENT_AUTHORITIES=1). La usa `_validar_partida`, que es la vía común del alta y de la importación.
- **D-CPL-02. Raíz.** `NIVEL_RAIZ_PARTIDA = 1`, porque así lo dicen BUD12-06 y el CHECK de la base. La raíz no lleva padre y el resto lo exige.
- **D-CPL-03. Nivel N-1.** El nivel del padre debe ser exactamente N-1. Se rechazan un padre del mismo nivel, uno que salte niveles y uno de nivel superior.
- **D-CPL-04. Alcance del padre.**
  - El mapa de niveles solo contiene las partidas del clasificador del ejercicio, y en una importación también las filas ya validadas del lote.
  - Por tanto, un padre de otro clasificador, de otra versión (otro ejercicio, incluso aprobado) o de otra empresa no existe.
  - El mensaje no revela datos ajenos: solo repite el código que escribió el usuario.
- **D-CPL-05. Tipo.** Se mantiene la semántica vigente (mismo tipo). Este ciclo no redefine tipos.
- **D-CPL-06. Código.** La jerarquía no se deduce del prefijo del código. La autoridad es relación padre, nivel y clasificador.
- **D-CPL-07. CSV.** Se conserva el contrato vigente: el padre puede estar en la base o en el mismo lote, siempre en una fila anterior. Una fila hija antes que su padre se rechaza («no existe»). Sigue siendo todo o nada.
- **D-CPL-08. Error.** Se mantiene el código estable `GOV_BUDGET_INVALID`, el de toda validación del ejercicio, que ya trata la UI.
  - Mensaje: «La partida padre «X» es de nivel A; una partida de nivel N necesita un padre de nivel N-1».
  - En el alta, el error se devuelve además en `field_errors.codigo_padre`, así que la UI lo muestra bajo «Código superior» sin cambiar el frontend.
  - En el CSV, cada error lleva «Fila N: ».
- **D-CPL-09. Normalización del padre.** El `codigo_padre` recortado se devuelve al cuerpo. Antes se validaba recortado y se enlazaba sin recortar, de modo que « 401 » dejaba la partida sin `parent_id`.
- **D-CPL-10. Datos existentes.**
  - No hay backfill ni se reescriben versiones aprobadas: las fotografías congeladas siguen legibles.
  - La regla se aplica a las altas nuevas.

## Requisitos del delta

| Id | Requisito | Prueba |
|---|---|---|
| FR-CPL-01 | Raíz sin padre; con padre, 422 | j00, j02 |
| FR-CPL-02 | Nivel N con padre de nivel N-1: se acepta | j01, j02, j06, j08 |
| FR-CPL-03 | Mismo nivel, salto o padre superior: 422 con los niveles en el mensaje | j00, j01, j02 |
| FR-CPL-04 | Padre inexistente o de otro tipo: 422 | j02 |
| FR-CPL-05 | Padre de otro clasificador, de otra versión o de otra empresa: 422, sin filtrar datos | j03, j04, j05 |
| FR-CPL-06 | CSV: misma regla, con padres del lote o de la base; el orden se respeta | j06, j07 |
| FR-CPL-07 | CSV todo o nada ante un padre inválido | j07 |
| FR-CPL-08 | En la UI, el alta inválida muestra el error y la corregida se acepta; el CSV inválido no importa nada | E2E |

## Gate

BLOCKER=0 · CRITICAL=0 · CONTRADICTIONS=0 · OWNER_CONFLICT=0 · MATERIAL_OQ=0 (la regla ya está fijada por BUD12-06) · UNKNOWN=0 · trazabilidad 100 %.

- **D-CPL-11. Accesibilidad.** La lista de errores de la importación era `<ul role="alert">`, y el rol anulaba la lista: los `<li>` quedaban huérfanos (Axe `listitem`, seria). Pasa a `<div role="alert"><ul>`, que se sigue anunciando igual.

## Observaciones fuera de alcance

**OBS-CPL-ALERT-LIST.**
- `src/pages/CopiasDeDiagnostico.tsx:191` usa el mismo `<ul role="alert">`.
- Es de plataforma (copias de diagnóstico), no de Gobierno, y queda fuera de este ciclo.


**OBS-CPL-CODIGO-ESPACIOS.**
- `codigo` se valida recortado pero se guarda tal cual llega.
- No afecta a la jerarquía: el padre se busca con el mismo código guardado.
- Queda como deuda menor.
