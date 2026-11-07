"""Núcleo puro para evaluar el RPO y seleccionar copias purgables."""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

RPO_MAXIMO_MINUTOS = 15
TIPO_DESTINO_MONTADO = "MOUNTED_FILESYSTEM"
ESTADOS_VALIDOS = ("VERIFIED_LOCAL", "VERIFIED_DESTINATION", "VERIFIED_DURABLE")

_PATRON_ETIQUETA = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")
_PATRON_CODIGO = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


@dataclass(frozen=True)
class Politica:
    rpo_minutos: int | None
    intervalo_minutos: int | None
    margen_minutos: int | None
    retencion_dias: int | None
    retencion_minimas: int | None
    destino_tipo: str | None
    destino_etiqueta: str | None
    habilitada: bool


@dataclass(frozen=True)
class Copia:
    backup_id: str | None
    origen: str
    estado: str
    transferencia: str
    iniciada: datetime
    instantanea: datetime | None
    duracion_segundos: int | None
    tamano: int | None
    fuera_del_anfitrion: bool
    retenida: bool


@dataclass(frozen=True)
class Evaluacion:
    estado: str
    ultima_valida: Copia | None
    ultima_en_destino: Copia | None
    ultima_fuera_del_anfitrion: Copia | None
    edad_segundos: int | None
    fallo_reciente: bool


def etiqueta_valida(etiqueta: str) -> bool:
    """Indica si la etiqueta cumple el formato permitido."""
    return bool(_PATRON_ETIQUETA.fullmatch(etiqueta))


def codigo_saneado(codigo: str | None) -> str:
    """Devuelve el código si es válido o el código de fallo genérico."""
    if codigo is not None and _PATRON_CODIGO.fullmatch(codigo):
        return codigo
    return "BACKUP_FAILED"


def errores_de_politica(p: Politica) -> tuple[str, ...]:
    """Devuelve los códigos de error de la política, en orden."""
    errores: list[str] = []

    if p.rpo_minutos is None:
        errores.append("RPO_REQUIRED")
    elif p.rpo_minutos > RPO_MAXIMO_MINUTOS:
        errores.append("RPO_ABOVE_MAXIMUM")
    elif p.rpo_minutos < 1:
        errores.append("RPO_INVALID")

    if p.intervalo_minutos is None:
        errores.append("INTERVAL_REQUIRED")
    elif p.intervalo_minutos < 1:
        errores.append("INTERVAL_INVALID")

    if p.margen_minutos is None:
        errores.append("MARGIN_REQUIRED")
    elif p.margen_minutos < 0:
        errores.append("MARGIN_INVALID")

    if (
        p.rpo_minutos is not None
        and p.intervalo_minutos is not None
        and p.margen_minutos is not None
        and p.intervalo_minutos + p.margen_minutos >= p.rpo_minutos
    ):
        errores.append("INTERVAL_EXCEEDS_RPO")

    if p.retencion_dias is None or p.retencion_minimas is None:
        errores.append("RETENTION_REQUIRED")
    elif p.retencion_dias < 1 or p.retencion_minimas < 1:
        errores.append("RETENTION_INVALID")

    if p.destino_tipo is None or p.destino_etiqueta is None:
        errores.append("DESTINATION_REQUIRED")

    if p.destino_tipo is not None and p.destino_tipo != TIPO_DESTINO_MONTADO:
        errores.append("DESTINATION_UNSUPPORTED")

    if p.destino_etiqueta is not None and not etiqueta_valida(p.destino_etiqueta):
        errores.append("DESTINATION_LABEL_INVALID")

    return tuple(errores)


def _es_aware(valor: datetime) -> bool:
    """Comprueba que el datetime tiene zona horaria."""
    return valor.tzinfo is not None and valor.tzinfo.utcoffset(valor) is not None


def franja(ahora: datetime, intervalo_minutos: int) -> tuple[str, datetime]:
    """Calcula la clave de la franja actual y su siguiente disparo."""
    if not _es_aware(ahora):
        raise ValueError("NAIVE_DATETIME")
    minuto = int(ahora.timestamp()) // 60
    inicio = minuto - minuto % intervalo_minutos
    clave = f"{intervalo_minutos}m:{inicio}"
    siguiente = datetime.fromtimestamp((inicio + intervalo_minutos) * 60, UTC)
    return clave, siguiente


def _instante(c: Copia) -> datetime:
    """Devuelve la instantánea de la copia o el mínimo datetime si no existe."""
    if c.instantanea is not None:
        return c.instantanea
    return datetime.min.replace(tzinfo=UTC)


def _ultima_por_instantanea(copias: Iterable[Copia]) -> Copia | None:
    """Devuelve la copia con mayor instantánea, ignorando las que no la tienen."""
    candidatas = [c for c in copias if c.instantanea is not None]
    if not candidatas:
        return None
    return max(candidatas, key=_instante)


def _es_fallo_reciente(copias: Iterable[Copia]) -> bool:
    """Indica si la copia más reciente no en curso ni purgada falló."""
    candidatas = [c for c in copias if c.estado not in ("RUNNING", "PURGED")]
    if not candidatas:
        return False
    reciente = max(candidatas, key=lambda c: c.iniciada)
    return reciente.estado in ("FAILED", "ABANDONED") or reciente.transferencia == "FAILED"


def evaluar(
    ahora: datetime,
    p: Politica,
    copias: Iterable[Copia],
    *,
    retencion_degradada: bool = False,
) -> Evaluacion:
    """Evalúa la política y las copias para derivar el estado RPO."""
    if not _es_aware(ahora):
        raise ValueError("NAIVE_DATETIME")

    lista = list(copias)

    validas = [c for c in lista if c.estado in ESTADOS_VALIDOS and c.instantanea is not None]
    ultima_valida = _ultima_por_instantanea(validas)

    en_destino = [c for c in validas if c.estado in ("VERIFIED_DESTINATION", "VERIFIED_DURABLE")]
    ultima_en_destino = _ultima_por_instantanea(en_destino)

    fuera_anfitrion = [
        c for c in validas if c.estado == "VERIFIED_DURABLE" and c.fuera_del_anfitrion
    ]
    ultima_fuera = _ultima_por_instantanea(fuera_anfitrion)

    fallo = _es_fallo_reciente(lista)

    referencia = ultima_en_destino if ultima_en_destino is not None else ultima_valida
    edad = (
        int((ahora - _instante(referencia)).total_seconds())
        if referencia is not None
        else None
    )

    def resultado(estado: str) -> Evaluacion:
        return Evaluacion(estado, ultima_valida, ultima_en_destino, ultima_fuera, edad, fallo)

    if not p.habilitada:
        return resultado("DISABLED")

    errores = errores_de_politica(p)
    if errores:
        return resultado("MISCONFIGURED")

    if ultima_valida is None:
        return resultado("NO_VALID_BACKUP")

    if ultima_en_destino is None:
        return resultado("LOCAL_ONLY")

    rpo = p.rpo_minutos
    intervalo = p.intervalo_minutos
    margen = p.margen_minutos
    if rpo is None or intervalo is None or margen is None:
        return resultado("MISCONFIGURED")

    referencia_destino = _instante(ultima_en_destino)
    edad_destino = int((ahora - referencia_destino).total_seconds())

    if edad_destino > rpo * 60:
        return resultado("RPO_BREACHED")

    if fallo or retencion_degradada:
        return resultado("DEGRADED")

    duracion = ultima_en_destino.duracion_segundos or 0
    if edad_destino + duracion > rpo * 60 or (
        (intervalo + margen) * 60 + duracion > rpo * 60
    ):
        return resultado("RPO_AT_RISK")

    if (
        ultima_en_destino.fuera_del_anfitrion
        and ultima_en_destino.estado == "VERIFIED_DURABLE"
        and ultima_en_destino.duracion_segundos is not None
    ):
        return resultado("RPO_CERTIFIED")

    return resultado("RPO_MET")


def _rango(estado: str) -> int:
    """Devuelve el rango de seguridad de un estado válido."""
    if estado == "VERIFIED_LOCAL":
        return 1
    if estado == "VERIFIED_DESTINATION":
        return 2
    return 3


def seleccionar_purga(
    ahora: datetime,
    p: Politica,
    copias: Iterable[Copia],
) -> list[Copia]:
    """Selecciona las copias programadas que se pueden purgar."""
    if p.retencion_dias is None or p.retencion_minimas is None:
        return []

    lista = list(copias)
    validas = [c for c in lista if c.estado in ESTADOS_VALIDOS and c.instantanea is not None]
    if not validas:
        return []

    ultima_valida = _ultima_por_instantanea(validas)
    ultima_durable = _ultima_por_instantanea(
        [c for c in validas if c.estado == "VERIFIED_DURABLE"]
    )

    candidatas = sorted(
        [
            c
            for c in validas
            if c.origen == "SCHEDULED" and c.backup_id is not None and not c.retenida
        ],
        key=_instante,
        reverse=True,
    )

    umbral = ahora - timedelta(days=p.retencion_dias)

    seleccionadas: list[Copia] = []
    for copia in candidatas[p.retencion_minimas :]:
        if copia is ultima_valida or copia is ultima_durable:
            continue
        if _instante(copia) >= umbral:
            continue
        if any(
            _instante(c) > _instante(copia) and _rango(c.estado) >= _rango(copia.estado)
            for c in validas
        ):
            seleccionadas.append(copia)

    return sorted(seleccionadas, key=_instante)
