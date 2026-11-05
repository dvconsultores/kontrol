# GOV-TRE-01 · mutaciones de negocio (T012)

**Método** (herramienta de Claude `mutar2.py`)
- Uno o varios SEARCH únicos por mutante.
- Purga de `__pycache__` y `PYTHONDONTWRITEBYTECODE=1`.
- Restauración verificada por sha256 tras cada mutante.

**Órdenes**
- Backend: las 4 suites `tests/test_gov_tre01_*.py` sobre PostgreSQL (48 pruebas), con `-x`.
- Interfaz: `vitest run` del fichero de pruebas del componente mutado.

## Resultado final: 37 mutantes · 36 muertos · 1 equivalente · 0 supervivientes de comportamiento

| ID | Mutación | Resultado | Primera prueba que falla |
|---|---|---|---|
| TRE-M01 | alcance: la cuenta se busca sin filtrar por empresa | KILLED | cuentas · cb12_alcance_por_empresa |
| TRE-M02 | alcance: el banco utilizable no filtra por empresa | KILLED | cuentas · cb12_alcance_por_empresa |
| TRE-M03 | banco inactivo admitido | KILLED | cuentas · cb03_banco_editar_e_inactivar |
| TRE-M04 | acto de otra empresa admitido | KILLED | autorizados · ac02_acto_invalido |
| TRE-M05 | acto sin efecto admitido | KILLED | autorizados · ac02_acto_invalido |
| TRE-M06 | acto con fecha futura admitido | KILLED | autorizados · ac02_acto_invalido |
| TRE-M07 | cargo de otra empresa admitido | EQUIVALENT | — |
| TRE-M08 | cargo no vigente admitido | KILLED | cuentas · cb13_opciones |
| TRE-M09 | cargo de otro ejercicio admitido | KILLED | cuentas · cb13_opciones |
| TRE-M10 | activar sin autorizado | KILLED | estados · st02_activar_sin_preparar |
| TRE-M11 | activar sin acto | KILLED | estados · st02_activar_sin_preparar |
| TRE-M12 | activar o reactivar con acto sin efecto | KILLED | estados · st03_activar_acto_revocado |
| TRE-M13 | autorizar con acto de la cuenta sin efecto | KILLED | estados · st04_acto_sin_efecto |
| TRE-M14 | activar desde cualquier estado | KILLED | estados · st07_cerrada_no_admite_nada |
| TRE-M15 | cerrada admite autorizar | KILLED | estados · st07_cerrada_no_admite_nada |
| TRE-M16 | reactivar sin requisitos | KILLED | estados · st04_acto_sin_efecto |
| TRE-M17 | cerrar no termina autorizados | KILLED | estados · st06_cerrar |
| TRE-M18 | historia: el fin de autorización se registra como edición | KILLED | autorizados · au07_cambio_conserva_historia |
| TRE-M19 | fin de autorización con fecha futura | KILLED | autorizados · au06_fechas |
| TRE-M20 | número: enmascarado devuelve el completo | KILLED | cuentas · cb04_cuenta_alta |
| TRE-M21 | número: sin validar el prefijo del banco | KILLED | cuentas · cb05_numero_invalido_no_se_repite |
| TRE-M22 | número: ver el completo no audita | KILLED | cuentas · cb10_ver_numero_completo |
| TRE-M23 | auditoría: el alta guarda el número completo | KILLED | cuentas · cb04_cuenta_alta |
| TRE-M24 | concurrencia: sin bloqueo de fila al escribir | KILLED | concurrencia · cc04_inactivar_contra_autorizar |
| TRE-M25 | concurrencia: If-Match no se compara | KILLED | cuentas · cb09_editar_borrador |
| TRE-M26 | SoD: activar sin guarda | KILLED | estados · ix03_guarda_sod_bloquea |
| TRE-M27 | SoD: autorizar sin guarda | KILLED | estados · ix04_guarda_sod_en_autorizar |
| TRE-M28 | permiso: ver el número con view | KILLED | cuentas · cb10_ver_numero_completo |
| TRE-M29 | permiso: activar con manage | KILLED | cuentas · cb11_permisos |
| TRE-M30 | filtro por cargo incluye autorizaciones terminadas | KILLED | autorizados · au10_filtro_por_cargo_solo_en_vigor |
| TRE-M31 | interfaz: ver número sin manage | KILLED | CuentaPage > CF-02: con view solo muestra datos y oculta accione |
| TRE-M32 | interfaz: activar sin capacidad | KILLED | CuentaPage > CF-02: con view solo muestra datos y oculta accione |
| TRE-M33 | interfaz: alta de autorizado con acto sin efecto | KILLED | AutorizadosCuenta > AC-05: acto_sin_efecto oculta el botón de au |
| TRE-M34 | interfaz: alta sin validar el prefijo | KILLED | NCP > NC-05 · número que no empieza por el código del banco: «El |
| TRE-M35 | interfaz: Nueva cuenta sin manage | KILLED | CuentasPage > CP-02 · con view: tabla con código, banco, tipo «C |
| TRE-M36 | interfaz: bancos sin manage | KILLED | BancosPage > BP-02 · con view muestra la tabla sin formulario ni |
| TRE-M37 | cargo de otra empresa: sin ningún filtro de empresa | KILLED | cuentas · cb13_opciones |

## TRE-M07: equivalente, demostrado

Quitar `GovernmentPosition.company_id == ctx.company_id` no cambia el comportamiento: la consulta sigue exigiendo que la estructura del cargo sea de la empresa, y un cargo pertenece a su estructura. Son dos filtros redundantes.

TRE-M37 quita los dos a la vez y muere. Por tanto el aislamiento del cargo por empresa sí está probado.

**BEHAVIORALLY_SURVIVING_MUTANTS = 0.** Árbol verificado sin restos de mutantes (sha256).
