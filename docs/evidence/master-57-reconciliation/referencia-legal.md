# Referencia legal — derogatoria de SNAT/2024/000121 (compuerta de verificación, 2026-10-07)

| Campo | Valor |
|---|---|
| `LEGAL_REFERENCE` | Providencia Administrativa SNAT/2026/00084 |
| `OFFICIAL_GAZETTE` | Gaceta Oficial de la República Bolivariana de Venezuela N.º 43.435 |
| `DATE` | 12 de agosto de 2026 (vigente desde su publicación, sin período de transición según las fuentes) |
| `REPEALED_RULE` | Providencia Administrativa SNAT/2024/000121 (de 26-11-2024; G.O. N.º 43.032 del 19-12-2024): requisitos técnicos y operativos de los proveedores de sistemas informáticos para la emisión de facturas y otros documentos fiscales (régimen de homologación) |
| `SOURCE` | (1) PwC Venezuela, *Nota de Actualidad Corporativa — Servicios Tributarios y Legales*, 14-08-2026; (2) IUSDATA, sumario de la G.O. N.º 43.435 del 12-08-2026; (3) Acceso a la Justicia, «SENIAT permite el uso de cualquier sistema contable informático sin trámite previo»; (4) resúmenes de proveedores y blogs tributarios coincidentes (Gerencia y Tributos, Sistemas4S, Gesco). El texto íntegro de la Gaceta **no** está incorporado al repositorio ni en `requerimientos/` (la compilación INNOVA llega hasta 2025) |
| `VERIFIED` | **VERIFIED** por documentación jurídica fiable y concordante (PwC + sumario oficial de la Gaceta). Paráfrasis mínima: la 00084 deroga expresamente la 000121 y deja sin efecto el régimen de homologación de proveedores de sistemas de facturación; las fuentes señalan un vacío normativo a la espera de nuevos lineamientos |
| Referencia aportada por la dueña | Sí (coincide en norma, Gaceta, fecha y norma derogada) |

## Efecto registrado en KONTROL

- Se retira como requisito vigente la homologación/autorización del software bajo la 121: D0-07
  (`HOMOLOGATION_REQUIREMENT_REMOVED`), Spec 056 (redefinida), ruta fiscal y backlog.
- **No** se retira ninguna obligación tributaria ni ninguna validación fiscal funcional: IVA, ISLR,
  IGTF, documentos fiscales, numeración y control, contingencia, libros, cierres y las 24 reglas de
  la matriz siguen `LEGAL_VALIDATION_REQUIRED`; las Specs 039–043 siguen `BLOCKED_BY_LEGAL_VALIDATION`.
- Si el SENIAT dicta un régimen nuevo, se incorporará a `authority-matrix.md` como norma vigente.

No se copia texto de la Gaceta ni de las notas con derechos reservados; solo referencia, fuente,
fecha y la paráfrasis mínima necesaria.
