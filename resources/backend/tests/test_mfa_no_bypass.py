"""MFA-NB01..NB04 · guardas estructurales: no puede existir ningún atajo que
desactive, omita o debilite el MFA.
"""

from __future__ import annotations

from pathlib import Path

import app.core.clock as reloj
from app.core.config import Settings
from app.core.route_contexts import contextos_de_api
from app.main import create_app

BACKEND = Path(__file__).resolve().parents[1]
APP_DIR = BACKEND / "app"
ENV_EXAMPLE = BACKEND / ".env.example"

PROHIBIDOS = {
    "DISABLE_MFA",
    "SKIP_MFA",
    "TEST_MFA_MODE",
    "ACCEPT_ANY_OTP",
    "FIXED_OTP",
    "MFA_BYPASS",
    "BYPASS_MFA",
    "MFA_OFF",
}


def test_mfa_nb01_ningun_atajo_mfa_en_el_codigo_ni_env_example():
    """MFA-NB01: ningún atajo MFA en el código ni en .env.example."""
    ficheros = list(APP_DIR.rglob("*.py"))
    if ENV_EXAMPLE.exists():
        ficheros.append(ENV_EXAMPLE)

    infracciones: list[tuple[Path, str]] = []
    for fichero in ficheros:
        texto = fichero.read_text(encoding="utf-8")
        texto_lower = texto.lower()
        for token in PROHIBIDOS:
            if token.lower() in texto_lower:
                infracciones.append((fichero, token))

    assert not infracciones, (
        "se encontraron atajos MFA prohibidos: "
        f"{[(str(f), t) for f, t in infracciones]}"
    )


def test_mfa_nb02_clock_no_lee_el_entorno():
    """MFA-NB02: clock.py no lee el entorno ni importa la configuración."""
    fuente = Path(reloj.__file__).read_text(encoding="utf-8")
    for token in ("os.environ", "getenv", "get_settings"):
        assert token not in fuente, token
    assert "app.core.config" not in fuente


def test_mfa_nb03_ninguna_ruta_contiene_breakglass_bypass_skip():
    """MFA-NB03: ninguna ruta de la app contiene breakglass, bypass o skip."""
    app = create_app()
    rutas = []
    for contexto in contextos_de_api(app):
        path = contexto.path or ""
        for token in ("breakglass", "break-glass", "bypass", "skip"):
            if token in path.lower():
                rutas.append((path, token))
    assert not rutas, rutas


def test_mfa_nb04_solo_mfa_keys_en_settings():
    """MFA-NB04: solo `mfa_keys` puede contener "mfa" en Settings."""
    for nombre in Settings.model_fields:
        if "mfa" in nombre.lower():
            assert nombre == "mfa_keys", nombre
