# KONTROL GOBIERNO — REGISTRO DE FUENTES (línea de producto separada)

> Incorporado al inventario el 2026-10-22 por indicación de la dueña («más adelante lo vas a necesitar»).
> **No modifica MASTER57**: las 57 filas de `master-56-specs-status.md` siguen intactas. Las dos fuentes lo
> exigen de forma expresa: «Este documento no modifica MASTER57 de KONTROL Empresarial. La línea Gobierno
> permanece separada hasta freeze del sponsor» y «Ninguna GOV-SPEC forma parte de las 57 Specs actuales».

## Estado

| Campo | Valor |
|---|---|
| Línea de producto | KONTROL Gobierno (Administración Pública venezolana), separada de KONTROL Empresarial |
| Estado de las fuentes | `SPONSOR REVIEW — NO AUTORIZA DESARROLLO` (borrador controlado) |
| Corte normativo | 16-10-2026 |
| Specs | **ninguna**. La numeración GOV-SPEC solo se crea tras el freeze del sponsor |
| Spec Kit | `NOT_STARTED`. Sin `specs/gov-*`, sin `/speckit-specify`, `DEEPSEEK CALLS = 0` |
| Efecto en MASTER57 | ninguno (57 filas; `NEXT MASTER SPEC` sigue `NOT YET PRIORITIZED`) |

## Fuentes

| Fichero (`requerimientos/gobierno/`) | Versión | Páginas | SHA-256 |
|---|---|---|---|
| `Ingenieria_de_Requerimientos_KONTROL_Gobierno_v1.0.pdf` | 1.0 | 26 | `8f86615f63ecfa0b25cc983e354c96936fe80cba5a3742190aeb0da0b5378c83` |
| `Biblioteca_Normativa_Oficial_KONTROL_Gobierno_v1.0.pdf` | 1.0 | 22 | `4a980bb96e6b3f79bddf48d1dbc4199c4aac385a879a400f6d54d1d304ac047b` |

La dueña los dejó en `docs/Administracion Publica - Gobierno/` el 2026-10-20. Se movieron, sin renombrarlos, a la
carpeta canónica de fuentes.

## Ingeniería de Requerimientos v1.0 — mapa de lectura

- **§1–2:** premisa legal-first y principios P-01..P-09:
  - separación Empresarial/Gobierno, presupuesto antes del gasto, expediente como evidencia;
  - backend como autoridad, historia no destructiva, versión normativa;
  - interoperabilidad con procedencia y control por diseño.
- **§3:** alcance v1.0:
  - organización y autoridad; presupuesto; contrataciones; contratos y garantías;
  - almacenes de consumo; tesorería; contabilidad pública; bienes públicos;
  - expediente y actos; control interno y auditoría; trámites e interoperabilidad;
  - Atenea para la nómina.
- **§3.1:** exclusiones: tributación municipal integral, nómina completa, BIM, gestión judicial, plataforma ciudadana
  completa y requisitos propios de un organismo convertidos en comportamiento global.
- **§4:** marco normativo. **§5:** actores. **§6:** arquitectura funcional (contextos):
  - Government Core, Budget Ledger, Procurement;
  - Treasury & Public Accounting, Public Assets, Records & Audit;
  - Digital Government, Integration Layer.
- **§7:** requerimientos funcionales. **§8:** máquinas de estado. **§9:** modelo lógico preliminar.
- **§10:** requerimientos no funcionales. **§11:** integraciones. **§12:** reportes. **§13:** criterios E2E.
- **§14:** ciclos de planificación GOV-0..GOV-7, que **no son Specs**:

  | Ciclo | Alcance |
  |---|---|
  | GOV-0 | Fundación |
  | GOV-1 | Presupuesto |
  | GOV-2 | Contrataciones |
  | GOV-3 | Tesorería y contabilidad |
  | GOV-4 | Bienes y SUDEBIP |
  | GOV-5 | Expediente y auditoría |
  | GOV-6 | Trámites e interoperabilidad |
  | GOV-7 | Integraciones, UAT y homologación |

- **§15:** decisiones del sponsor, todas abiertas:

  | Decisión | Tema |
  |---|---|
  | D-GOV-01 | Jurisdicción piloto |
  | D-GOV-02 | Profundidad presupuestaria |
  | D-GOV-03 | Alcance de SNC |
  | D-GOV-04 | Plan de cuentas ONCOP del piloto |
  | D-GOV-05 | Copias oficiales SUDEBIP 43.077 |
  | D-GOV-06 | Catálogo de trámites tras G.O. 7.018/2026 |
  | D-GOV-07 | Contrato con Atenea |
  | D-GOV-08 | Firma e interoperabilidad |

- **§16:** definición de convergencia. **§17:** referencias oficiales. La URL no sustituye la copia local con SHA-256.

## Biblioteca Normativa Oficial v1.0 — mapa de lectura

- **§1:** clases de verificación:
  - **A:** verificada en fuente oficial;
  - **B:** facsímil o repositorio institucional;
  - **C:** pendiente de pin oficial. No autoriza reglas codificadas en el producto.
- **§2:** alertas de vigencia:
  - G.O. 7.018/2026 desplaza a la simplificación de trámites de 2014;
  - para anticorrupción rige la reforma de G.O. 6.699/2022;
  - para la LOAFSP rige el Decreto 2.174 (G.O. 6.210/2015);
  - la LOBP se combina con SUDEBIP G.O. 43.077/2025;
  - los instructivos y clasificadores de ONAPRE/ONCOP se versionan por ejercicio.
- **§3:** inventario N01..N40: **40 instrumentos (26 A · 2 B · 12 C)**. Clase C:
  - instructivos ONAPRE 20/21/3 y clasificador (N07–N10);
  - SUDEBIP (N14–N17);
  - normas técnicas ONCOP (N36);
  - normativa local (N37);
  - normativa tributaria (N38);
  - seguridad digital (N40).
- **§4:** fichas normativas. **§5:** fuentes históricas que no deben gobernar reglas nuevas.
- **§6:** paquete normativo obligatorio por tenant. **§7:** registro de vigencia. **§8:** impacto por dominio.
- **§9:** checklist de freeze (10 puntos): copia custodiada y SHA-256 de cada P0, vigencia, normativa del piloto,
  edición ONAPRE/ONCOP, SNC/SUDEBIP, retenciones, trámites, matriz requisito → fuente y aprobación del sponsor y de su
  asesor jurídico antes de crear GOV-SPECs.

## Reglas para quien lo use más adelante

1. **No es alcance de MASTER57.** No se agregan filas 058+ ni flags «gobierno» dentro de las Specs empresariales
   (P-02). Reutilizar componentes técnicos no implica reutilizar reglas de negocio empresariales (§6).
2. **Solo la dueña o el sponsor abren la línea**, con el freeze de la baseline y las D-GOV cerradas. Hasta entonces
   cualquier encargo de implementación es `BLOCKED BY OWNER DECISION`.
3. **Cruces con KONTROL Empresarial que hay que vigilar:**
   - la 057 (Activos Fijos) frente a los bienes públicos (LOBP/SUDEBIP);
   - la 008 (Almacenes) frente a los almacenes de consumo;
   - las 039–043 (fiscal) frente a las retenciones del pagador público (N38, clase C);
   - el licenciamiento y el aislamiento de tenant.

   Ninguno se resuelve sin decisión.
4. **Las fuentes de clase C** no sustentan reglas P0 hasta que exista una copia oficial pinneada.
