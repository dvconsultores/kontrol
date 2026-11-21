"""Autoridad única de procesos de Gobierno para la auditoría (CTL-02 · CTL-02-AUDIT-PROCESS-RESOLUTION).

Un evento de auditoría se asocia a su proceso por la metadata explícita del catálogo de
eventos: cada entrada declara su `owner_spec` y este registro dice a qué proceso pertenece
cada Spec. El módulo sale del prefijo del código del proceso.

La bitácora (CTL-02), la auditoría institucional (CTL-04), los eventos SoD (CTL-07), el
reporte de control interno (REP-10) y los expedientes de cuenta (CTL-05) consumen esta
autoridad; ninguno mantiene una lista propia. Un proceso nuevo se registra aquí una sola
vez, y la guardia `test_ctl02_procesos_*` falla si un evento de Gobierno no resuelve.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.shared.audit_catalog import catalog

CLASE_PROCESO = "PROCESS_EVENT"
CLASE_AUTENTICACION = "AUTH_EVENT"
CLASE_PLATAFORMA = "PLATFORM_EVENT"
CLASE_SISTEMA = "SYSTEM_EVENT"

FUENTE_CATALOGO = "CATALOGO_DE_EVENTOS"
FUENTE_SIN_REGISTRO = "SIN_REGISTRO"

MODULO_GOBIERNO = "government"

ACCIONES_AUTENTICACION = frozenset(
    {
        "LOGIN_SUCCESS",
        "LOGIN_FAILED",
        "LOGIN_BLOCKED",
        "MFA_CHALLENGE_SUCCEEDED",
        "MFA_CHALLENGE_FAILED",
        "MFA_REAUTH_SUCCEEDED",
        "MFA_REAUTH_FAILED",
        "SESSION_REVOKED",
        "SESSIONS_REVOKED_SECURITY_CHANGE",
    }
)


@dataclass(frozen=True)
class ModuloGobierno:
    codigo: str
    nombre: str


@dataclass(frozen=True)
class ProcesoGobierno:
    codigo: str
    nombre: str
    owner_specs: tuple[str, ...]

    @property
    def modulo(self) -> str:
        return self.codigo.split("-", 1)[0]


@dataclass(frozen=True)
class ProcesoResuelto:
    """Resultado de resolver un evento: clase y, si es de proceso, código, nombre y módulo."""

    clase: str
    codigo: str | None
    nombre: str | None
    modulo: str | None
    modulo_nombre: str | None
    fuente: str


MODULOS: tuple[ModuloGobierno, ...] = (
    ModuloGobierno("ORG", "Organización y autoridad"),
    ModuloGobierno("DOC", "Expedientes y actos administrativos"),
    ModuloGobierno("BUD", "Presupuesto"),
    ModuloGobierno("PROC", "Contrataciones"),
    ModuloGobierno("CNT", "Contratos"),
    ModuloGobierno("TRE", "Tesorería"),
    ModuloGobierno("CTL", "Control interno"),
    ModuloGobierno("REP", "Reportes"),
)

# Una Spec que cubre varios procesos (p. ej. BUD-01 + BUD-02) se registra en su proceso principal,
# el primero de su título: el catálogo de eventos solo declara la Spec dueña.
PROCESOS: tuple[ProcesoGobierno, ...] = (
    ProcesoGobierno("ORG-01", "Configuración del ente", ("gov-0-01",)),
    ProcesoGobierno("ORG-02", "Estructura organizativa", ("gov-0-02",)),
    ProcesoGobierno("ORG-03", "Cargos y competencias", ("gov-0-03",)),
    ProcesoGobierno("ORG-04", "Ocupación de cargos", ("gov-org-04",)),
    ProcesoGobierno("ORG-06", "Identidad institucional", ("gov-0-06",)),
    ProcesoGobierno("ORG-07", "Matriz de autoridad", ("gov-org-07",)),
    ProcesoGobierno("DOC-02", "Actos administrativos", ("gov-doc-02",)),
    ProcesoGobierno("DOC-04", "Notificaciones administrativas", ("gov-doc-04",)),
    ProcesoGobierno("DOC-08", "Paquetes de auditoría", ("gov-doc-08",)),
    ProcesoGobierno("BUD-01", "Ejercicio y clasificador presupuestario", ("gov-bud-01",)),
    ProcesoGobierno("BUD-03", "Plan operativo y fuentes de financiamiento", ("gov-bud-03",)),
    ProcesoGobierno("BUD-05", "Presupuesto aprobado", ("gov-bud-05",)),
    ProcesoGobierno("BUD-06", "Disponibilidad presupuestaria", ("gov-bud-06",)),
    ProcesoGobierno("BUD-08", "Compromiso presupuestario", ("gov-bud-08",)),
    ProcesoGobierno("BUD-09", "Causado presupuestario", ("gov-bud-09",)),
    ProcesoGobierno("PROC-02", "Comisiones de contrataciones", ("gov-proc-02",)),
    ProcesoGobierno("PROC-03", "Expedientes de contratación", ("gov-proc-03",)),
    ProcesoGobierno("PROC-11", "Funciones incompatibles en contrataciones", ("gov-proc-11",)),
    ProcesoGobierno("CNT-01", "Contratos y órdenes", ("gov-cnt-01",)),
    ProcesoGobierno("CNT-02", "Modificaciones contractuales", ("gov-cnt-02",)),
    ProcesoGobierno("CNT-03", "Ejecución del contrato", ("gov-cnt-03",)),
    ProcesoGobierno("CNT-04", "Supervisión del contrato", ("gov-cnt-04",)),
    ProcesoGobierno("CNT-07", "Terminación del contrato", ("gov-cnt-07",)),
    ProcesoGobierno("CNT-08", "Expedientes contractuales", ("gov-cnt-08",)),
    ProcesoGobierno("CNT-09", "Alertas de vencimiento", ("gov-cnt-09",)),
    ProcesoGobierno("TRE-01", "Cuentas bancarias públicas", ("gov-tre-01",)),
    ProcesoGobierno("TRE-02", "Programación financiera", ("gov-tre-02",)),
    ProcesoGobierno("TRE-03", "Órdenes de pago", ("gov-tre-03",)),
    ProcesoGobierno("TRE-04", "Pagos", ("gov-tre-04",)),
    ProcesoGobierno("TRE-05", "Retenciones", ("gov-tre-05",)),
    ProcesoGobierno("TRE-09", "Tasas oficiales", ("gov-tre-09",)),
    ProcesoGobierno("CTL-01", "Segregación de funciones", ("gov-ctl-01",)),
    ProcesoGobierno("CTL-04", "Auditoría institucional", ("gov-ctl-04",)),
    ProcesoGobierno("CTL-05", "Expedientes de cuenta", ("gov-ctl-05",)),
    ProcesoGobierno("CTL-06", "Hallazgos y acciones correctivas", ("gov-ctl-06",)),
    ProcesoGobierno("CTL-07", "Alertas de operaciones atípicas", ("gov-ctl-07",)),
    ProcesoGobierno("CTL-09", "Actas de entrega", ("gov-ctl-09",)),
    ProcesoGobierno("CTL-10", "Controles de cierre", ("gov-ctl-10",)),
    ProcesoGobierno("REP-03", "Reporte de contrataciones", ("gov-rep-03",)),
    ProcesoGobierno("REP-10", "Reporte de control interno", ("gov-rep-10",)),
)

_POR_CODIGO = {proceso.codigo: proceso for proceso in PROCESOS}
_POR_OWNER_SPEC = {owner_spec: proceso for proceso in PROCESOS for owner_spec in proceso.owner_specs}
_MODULO_NOMBRE = {modulo.codigo: modulo.nombre for modulo in MODULOS}


def proceso(codigo: str | None) -> ProcesoGobierno | None:
    """Devuelve el proceso registrado con ese código, o None."""
    return _POR_CODIGO.get(codigo) if codigo else None


def es_proceso(codigo: str | None) -> bool:
    """Indica si el código es un proceso de Gobierno registrado (validación de filtros)."""
    return proceso(codigo) is not None


def nombre_de(codigo: str | None) -> str | None:
    """Nombre del proceso registrado, o None."""
    encontrado = proceso(codigo)
    return encontrado.nombre if encontrado else None


def modulo_nombre(codigo_modulo: str | None) -> str | None:
    return _MODULO_NOMBRE.get(codigo_modulo) if codigo_modulo else None


def owner_specs_de(codigo: str) -> tuple[str, ...]:
    encontrado = proceso(codigo)
    return encontrado.owner_specs if encontrado else ()


def proceso_de_owner_spec(owner_spec: str | None) -> ProcesoGobierno | None:
    return _POR_OWNER_SPEC.get(owner_spec) if owner_spec else None


def resolver_proceso(action: str, entity_type: str) -> ProcesoResuelto:
    """Resuelve el proceso de un evento de auditoría por la metadata del catálogo de eventos."""
    if action in ACCIONES_AUTENTICACION:
        return ProcesoResuelto(CLASE_AUTENTICACION, None, None, None, None, FUENTE_CATALOGO)
    spec = catalog().get((action, entity_type))
    if spec is None:
        return ProcesoResuelto(CLASE_SISTEMA, None, None, None, None, FUENTE_SIN_REGISTRO)
    if spec.owner_module != MODULO_GOBIERNO:
        return ProcesoResuelto(CLASE_PLATAFORMA, None, None, None, None, FUENTE_CATALOGO)
    encontrado = proceso_de_owner_spec(spec.owner_spec)
    if encontrado is None:
        return ProcesoResuelto(CLASE_PROCESO, None, None, None, None, FUENTE_SIN_REGISTRO)
    return ProcesoResuelto(
        CLASE_PROCESO,
        encontrado.codigo,
        encontrado.nombre,
        encontrado.modulo,
        modulo_nombre(encontrado.modulo),
        FUENTE_CATALOGO,
    )
