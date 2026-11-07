from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.ops.backup_rpo import (
    TIPO_DESTINO_MONTADO,
    Copia,
    Politica,
    codigo_saneado,
    errores_de_politica,
    etiqueta_valida,
    evaluar,
    franja,
    seleccionar_purga,
)

AHORA = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


def _politica(**cambios: object) -> Politica:
    valores: dict[str, object] = {
        "rpo_minutos": 15,
        "intervalo_minutos": 5,
        "margen_minutos": 2,
        "retencion_dias": 7,
        "retencion_minimas": 3,
        "destino_tipo": TIPO_DESTINO_MONTADO,
        "destino_etiqueta": "nas-1",
        "habilitada": True,
    }
    valores.update(cambios)
    return Politica(**valores)


def _politica_purga(**cambios: object) -> Politica:
    valores: dict[str, object] = {"retencion_dias": 7, "retencion_minimas": 1}
    valores.update(cambios)
    return _politica(**valores)


def _copia(hace_minutos: int = 1, **cambios: object) -> Copia:
    instantanea = AHORA - timedelta(minutes=hace_minutos)
    valores: dict[str, object] = {
        "backup_id": "b",
        "origen": "SCHEDULED",
        "estado": "VERIFIED_DURABLE",
        "transferencia": "COMPLETED",
        "iniciada": instantanea,
        "instantanea": instantanea,
        "duracion_segundos": 60,
        "tamano": 1,
        "fuera_del_anfitrion": True,
        "retenida": False,
    }
    valores.update(cambios)
    return Copia(**valores)


def _vieja(nombre: str, dias: int, **cambios: object) -> Copia:
    return _copia(backup_id=nombre, hace_minutos=dias * 1440, **cambios)


def test_politica_valida_sin_errores():
    assert errores_de_politica(_politica()) == ()


def test_rpo_15_aceptado():
    assert errores_de_politica(_politica(rpo_minutos=15)) == ()


def test_rpo_16_da_rpo_above_maximum():
    assert "RPO_ABOVE_MAXIMUM" in errores_de_politica(_politica(rpo_minutos=16))


def test_rpo_none_da_rpo_required():
    assert "RPO_REQUIRED" in errores_de_politica(_politica(rpo_minutos=None))


def test_intervalo_igual_al_rpo_da_interval_exceeds_rpo():
    assert "INTERVAL_EXCEEDS_RPO" in errores_de_politica(
        _politica(intervalo_minutos=15, margen_minutos=0)
    )


def test_intervalo_mas_margen_igual_al_rpo_da_interval_exceeds_rpo():
    assert "INTERVAL_EXCEEDS_RPO" in errores_de_politica(
        _politica(intervalo_minutos=13, margen_minutos=2)
    )


def test_retencion_ausente_da_retention_required():
    assert "RETENTION_REQUIRED" in errores_de_politica(
        _politica(retencion_dias=None, retencion_minimas=None)
    )


def test_destino_ausente_da_destination_required():
    assert "DESTINATION_REQUIRED" in errores_de_politica(
        _politica(destino_tipo=None, destino_etiqueta=None)
    )


def test_destino_s3_da_destination_unsupported():
    assert "DESTINATION_UNSUPPORTED" in errores_de_politica(_politica(destino_tipo="S3"))


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("nas-1", True),
        ("..", False),
        ("a/b", False),
        ("../x", False),
        ("A", False),
        ("", False),
    ],
)
def test_etiqueta_valida(valor, esperado):
    assert etiqueta_valida(valor) is esperado


def test_codigo_saneado_pg_dump_failed_se_conserva():
    assert codigo_saneado("PG_DUMP_FAILED") == "PG_DUMP_FAILED"


def test_codigo_saneado_texto_libre_y_none_dan_backup_failed():
    assert codigo_saneado("error en /data/x") == "BACKUP_FAILED"
    assert codigo_saneado(None) == "BACKUP_FAILED"


def test_franja_estable_dentro_de_la_ventana():
    clave1, siguiente1 = franja(AHORA, 5)
    clave2, siguiente2 = franja(AHORA + timedelta(minutes=4), 5)
    assert clave1 == clave2
    assert siguiente1 == siguiente2


def test_franja_distinta_en_la_siguiente_ventana():
    clave1, _ = franja(AHORA, 5)
    clave2, _ = franja(AHORA + timedelta(minutes=5), 5)
    assert clave1 != clave2


def test_franja_con_fecha_sin_zona_lanza_value_error():
    with pytest.raises(ValueError):
        franja(datetime(2026, 11, 7, 12, 0), 5)


def test_estado_disabled():
    resultado = evaluar(AHORA, _politica(habilitada=False), [_copia()])
    assert resultado.estado == "DISABLED"


def test_estado_misconfigured():
    resultado = evaluar(AHORA, _politica(rpo_minutos=None), [_copia()])
    assert resultado.estado == "MISCONFIGURED"


def test_estado_no_valid_backup_sin_copias():
    resultado = evaluar(AHORA, _politica(), [])
    assert resultado.estado == "NO_VALID_BACKUP"


def test_estado_no_valid_backup_con_solo_failed():
    resultado = evaluar(AHORA, _politica(), [_copia(estado="FAILED")])
    assert resultado.estado == "NO_VALID_BACKUP"


def test_estado_local_only_con_solo_verified_local():
    resultado = evaluar(AHORA, _politica(), [_copia(estado="VERIFIED_LOCAL")])
    assert resultado.estado == "LOCAL_ONLY"


def test_estado_rpo_breached_con_copia_de_hace_20_min():
    resultado = evaluar(AHORA, _politica(), [_copia(hace_minutos=20)])
    assert resultado.estado == "RPO_BREACHED"


def test_estado_degraded_con_copia_reciente_y_failed_mas_nueva():
    copias = [
        _copia(hace_minutos=1),
        _copia(
            backup_id="f",
            hace_minutos=0,
            estado="FAILED",
            transferencia="FAILED",
        ),
    ]
    resultado = evaluar(AHORA, _politica(), copias)
    assert resultado.estado == "DEGRADED"


def test_estado_degraded_con_retencion_degradada():
    resultado = evaluar(AHORA, _politica(), [_copia()], retencion_degradada=True)
    assert resultado.estado == "DEGRADED"


def test_estado_rpo_at_risk_con_copia_de_hace_14_min():
    resultado = evaluar(AHORA, _politica(), [_copia(hace_minutos=14, duracion_segundos=61)])
    assert resultado.estado == "RPO_AT_RISK"


def test_estado_rpo_certified_con_copia_durable_de_hace_1_min():
    resultado = evaluar(AHORA, _politica(), [_copia(hace_minutos=1)])
    assert resultado.estado == "RPO_CERTIFIED"


def test_estado_rpo_met_con_destination_sin_fuera_del_anfitrion():
    copia = _copia(
        estado="VERIFIED_DESTINATION",
        fuera_del_anfitrion=False,
    )
    resultado = evaluar(AHORA, _politica(), [copia])
    assert resultado.estado == "RPO_MET"


def test_edad_desde_la_instantanea_y_no_desde_el_fin():
    copia = _copia(
        iniciada=AHORA - timedelta(minutes=1),
        instantanea=AHORA - timedelta(minutes=20),
    )
    resultado = evaluar(AHORA, _politica(), [copia])
    assert resultado.estado == "RPO_BREACHED"


def test_staging_no_cuenta_como_fuera_del_anfitrion():
    copia = _copia(estado="VERIFIED_LOCAL", fuera_del_anfitrion=True)
    resultado = evaluar(AHORA, _politica(), [copia])
    assert resultado.estado == "LOCAL_ONLY"


def test_copia_en_curso_no_cuenta():
    copia = _copia(estado="RUNNING")
    resultado = evaluar(AHORA, _politica(), [copia])
    assert resultado.estado == "NO_VALID_BACKUP"


def test_ultima_copia_visible_aunque_deshabilitada():
    resultado = evaluar(AHORA, _politica(habilitada=False), [_copia(hace_minutos=10)])
    assert resultado.ultima_valida is not None
    assert resultado.edad_segundos is not None


def test_local_only_informa_edad():
    resultado = evaluar(AHORA, _politica(), [_copia(estado="VERIFIED_LOCAL", hace_minutos=10)])
    assert resultado.ultima_valida is not None
    assert resultado.edad_segundos == 600


def test_purga_una_antigua_con_sucesoras():
    copias = [_vieja("vieja", 10), _copia(backup_id="nueva")]
    resultado = seleccionar_purga(AHORA, _politica_purga(), copias)
    assert [c.backup_id for c in resultado] == ["vieja"]


def test_purga_nunca_la_ultima_valida():
    copias = [_vieja("vieja", 10)]
    resultado = seleccionar_purga(AHORA, _politica_purga(), copias)
    assert resultado == []


def test_purga_nunca_una_manual():
    copias = [_vieja("manual", 10, origen="MANUAL"), _copia(backup_id="nueva")]
    resultado = seleccionar_purga(AHORA, _politica_purga(), copias)
    assert resultado == []


def test_purga_nunca_una_retenida():
    copias = [_vieja("retenida", 10, retenida=True), _copia(backup_id="nueva")]
    resultado = seleccionar_purga(AHORA, _politica_purga(), copias)
    assert resultado == []


def test_purga_respeta_retencion_minimas():
    copias = [
        _vieja("c14", 14),
        _vieja("c13", 13),
        _vieja("c12", 12),
        _vieja("c11", 11),
        _vieja("c10", 10),
    ]
    resultado = seleccionar_purga(
        AHORA,
        _politica_purga(retencion_minimas=3),
        copias,
    )
    assert [c.backup_id for c in resultado] == ["c14", "c13"]


def test_purga_respeta_retencion_dias():
    copias = [_vieja("reciente", 3), _copia(backup_id="nueva")]
    resultado = seleccionar_purga(AHORA, _politica_purga(), copias)
    assert resultado == []


def test_el_limite_de_dias_no_purga_lo_reciente():
    copias = [
        _vieja("antigua", 10),
        _vieja("reciente", 3),
        _copia(backup_id="nueva"),
    ]
    resultado = seleccionar_purga(AHORA, _politica_purga(), copias)
    assert [c.backup_id for c in resultado] == ["antigua"]


def test_purga_no_borra_durable_antigua_si_la_nueva_es_solo_local():
    copias = [
        _vieja("durable", 10, estado="VERIFIED_DURABLE"),
        _copia(backup_id="local", estado="VERIFIED_LOCAL"),
    ]
    resultado = seleccionar_purga(AHORA, _politica_purga(), copias)
    assert resultado == []


def test_purga_no_borra_predecesora_sin_sucesora_de_rango():
    copias = [
        _vieja("vieja10", 10, estado="VERIFIED_DESTINATION"),
        _vieja("vieja9", 9, estado="VERIFIED_DESTINATION"),
        _copia(backup_id="local", estado="VERIFIED_LOCAL"),
    ]
    resultado = seleccionar_purga(AHORA, _politica_purga(), copias)
    assert [c.backup_id for c in resultado] == ["vieja10"]


def test_purga_ignora_estados_no_validos():
    copias = [
        _vieja("failed", 10, estado="FAILED"),
        _vieja("abandoned", 10, estado="ABANDONED"),
        _vieja("purged", 10, estado="PURGED"),
        _vieja("running", 10, estado="RUNNING"),
        _copia(backup_id="nueva"),
    ]
    resultado = seleccionar_purga(AHORA, _politica_purga(), copias)
    assert resultado == []


def test_purga_sin_politica_devuelve_lista_vacia():
    copias = [_vieja("vieja", 10), _copia(backup_id="nueva")]
    resultado = seleccionar_purga(
        AHORA,
        _politica_purga(retencion_dias=None, retencion_minimas=None),
        copias,
    )
    assert resultado == []


def test_purga_orden_de_mas_antigua_a_mas_reciente():
    copias = [
        _vieja("c10", 10),
        _vieja("c12", 12),
        _copia(backup_id="nueva"),
    ]
    resultado = seleccionar_purga(AHORA, _politica_purga(), copias)
    assert [c.backup_id for c in resultado] == ["c12", "c10"]
