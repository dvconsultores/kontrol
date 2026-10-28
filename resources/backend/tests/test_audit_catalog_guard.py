"""Prueba de arquitectura OD-AUD-04: guarda estática del catálogo de auditoría.

Antes de ejecutar nada, inspecciona el código fuente con `ast` y comprueba
cuatro invariantes del diseño descrito en
`specs/001-fundacion/evidence/audit-catalog/catalogo.md`.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import NamedTuple

APP = Path(__file__).resolve().parents[1] / "app"
ALEMBIC = Path(__file__).resolve().parents[1] / "alembic" / "versions"
CATALOG_MODULE = "app.shared.audit_catalog"
CATALOG_ENTRIES_MODULE = "app.shared.audit_catalog_entries"
AUDIT_MODULE = "app/shared/audit.py"

EMITTERS = frozenset(
    {
        "record_audit",
        "record_audit_after_rollback",
        "_audit",
        "_auditar",
        "_audit_mfa",
        "_audit_reservation",
        "_auditar_tarea",
        "_denegar",
    }
)

FIXED_ENTITY_BY_EMITTER = {
    ("modules/documents/service.py", "_audit"): "Document",
    ("modules/identity_access/mfa_service.py", "_audit_mfa"): "User",
    ("modules/inventory/service.py", "_audit_reservation"): "Reservation",
    ("modules/notifications/service.py", "_auditar_tarea"): "Task",
}

DESIGN_DOC = "specs/001-fundacion/evidence/audit-catalog/catalogo.md"
OD_AUD_04 = "OD-AUD-04"


class Emission(NamedTuple):
    """Par acción/entidad resuelto estáticamente."""

    action: str
    entity_type: str | None
    file: str
    line: int
    is_action_joined_str: bool = False


def _python_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def _walk_app_files() -> list[Path]:
    files: list[Path] = []
    for path in _python_files(APP):
        relative = str(path.relative_to(APP)).replace("\\", "/")
        if relative in {
            "shared/audit_catalog.py",
            "shared/audit_catalog_entries.py",
        }:
            continue
        files.append(path)
    return files


def _emitter_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_emitter(node: ast.AST) -> bool:
    return _emitter_name(node) in EMITTERS


def _wrapped_str(value: ast.expr | None) -> str | None:
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    return None


def _is_joined_str(value: ast.expr | None) -> bool:
    return isinstance(value, ast.JoinedStr)


def _find_function_def(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _positional_parameter_names(func: ast.FunctionDef) -> list[str]:
    names: list[str] = []
    positional = list(func.args.posonlyargs) + list(func.args.args)
    names.extend(argument.arg for argument in positional)
    names.extend(argument.arg for argument in func.args.kwonlyargs)
    return names


def _keyword_only_default_index(func: ast.FunctionDef, name: str) -> int | None:
    """Índice del parámetro solo-palabra-clave en `kwonlyargs`."""
    for index, argument in enumerate(func.args.kwonlyargs):
        if argument.arg == name:
            return index
    return None


def _argument_value(
    call: ast.Call,
    name: str,
    tree: ast.AST,
    module_relative_path: str,
) -> ast.expr | None:
    """Resuelve el valor estático de un argumento de llamada.

    Primero busca argumentos con nombre; después, si el emisor está definido en
    el mismo fichero, recorre los argumentos posicionales usando los nombres de
    sus parámetros. Para parámetros no pasados devuelve el valor por defecto si
    es una cadena literal.
    """
    for keyword in call.keywords:
        if keyword.arg == name and isinstance(
            keyword.value, ast.Constant
        ):
            return keyword.value

    func = call.func
    emitter_name = _emitter_name(func)
    if emitter_name is None:
        return None

    function_def = _find_function_def(tree, emitter_name)
    if function_def is None:
        return None

    names = _positional_parameter_names(function_def)
    if name not in names:
        return None
    index = names.index(name)
    positional = list(call.args)
    if index < len(positional):
        value = positional[index]
        if isinstance(value, ast.Constant):
            return value
        return value

    positional_count = len(list(function_def.args.posonlyargs) + list(function_def.args.args))
    defaults_offset = positional_count - len(function_def.args.defaults)
    if index < positional_count and index >= defaults_offset:
        default = function_def.args.defaults[index - defaults_offset]
        if isinstance(default, ast.Constant) and isinstance(default.value, str):
            return default

    if index >= positional_count:
        kwonly_index = _keyword_only_default_index(function_def, name)
        if kwonly_index is None:
            return None
        kw_default = function_def.args.kw_defaults[kwonly_index]
        if (
            isinstance(kw_default, ast.Constant)
            and isinstance(kw_default.value, str)
        ):
            return kw_default

    return None


def _resolve_emission(
    call: ast.Call,
    tree: ast.AST,
    module_relative_path: str,
) -> Emission | None:
    """Resuelve una llamada a emisor a un par estático si es posible."""
    func = call.func
    emitter_name = _emitter_name(func)
    if emitter_name not in EMITTERS:
        return None

    action_value: ast.expr | None = None
    entity_value: ast.expr | None = None
    action_is_joined: bool = False

    for keyword in call.keywords:
        if keyword.arg in {"action", "accion"}:
            if _wrapped_str(keyword.value) is not None:
                action_value = keyword.value
            elif _is_joined_str(keyword.value):
                action_value = keyword.value
                action_is_joined = True
        if keyword.arg in {"entity_type", "entidad"}:
            if _wrapped_str(keyword.value) is not None:
                entity_value = keyword.value

    if action_value is None:
        action_value = _argument_value(
            call, "action", tree, module_relative_path
        )
        if _is_joined_str(action_value):
            action_is_joined = True
    else:
        positional_action = _argument_value(
            call, "action", tree, module_relative_path
        )
        if positional_action is not None and _is_joined_str(action_value):
            action_is_joined = True

    if entity_value is None:
        entity_value = _argument_value(
            call, "entity_type", tree, module_relative_path
        )
    if entity_value is None:
        entity_value = _argument_value(
            call, "entidad", tree, module_relative_path
        )

    action = _wrapped_str(action_value)
    entity = _wrapped_str(entity_value)

    if action is None and not action_is_joined:
        return None

    if entity is None:
        fixed = FIXED_ENTITY_BY_EMITTER.get(
            (module_relative_path, emitter_name)
        )
        if fixed is not None:
            entity = fixed

    if action is None:
        return None

    return Emission(
        action=action,
        entity_type=entity,
        file=module_relative_path,
        line=call.lineno,
        is_action_joined_str=action_is_joined,
    )


def _extract_emissions(
    file_path: Path, module_relative_path: str
) -> list[Emission]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    emissions: list[Emission] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_emitter(node.func):
            emission = _resolve_emission(node, tree, module_relative_path)
            if emission is not None:
                emissions.append(emission)
    return emissions


def _extract_all_emissions() -> list[Emission]:
    emissions: list[Emission] = []
    for file_path in _walk_app_files():
        relative = str(file_path.relative_to(APP)).replace("\\", "/")
        emissions.extend(_extract_emissions(file_path, relative))
    return emissions


def _extract_from_source(source: str) -> list[Emission]:
    module = ast.parse(source)
    tree = ast.Module(body=module.body, type_ignores=[])
    emissions: list[Emission] = []
    for node in ast.walk(module):
        if isinstance(node, ast.Call) and _is_emitter(node.func):
            emission = _resolve_emission(
                node, tree, "synthetic/source.py"
            )
            if emission is not None:
                emissions.append(emission)
    return emissions


def _catalog_map():
    from app.shared.audit_catalog import catalog

    return catalog()


def _load_catalog():
    catalog_map = _catalog_map()
    entries = list(catalog_map.values())
    entries_by_code: dict[str, list] = {}
    for entry in entries:
        entries_by_code.setdefault(entry.code, []).append(entry)
    return entries, entries_by_code


def test_guard_a_emisiones_literales_en_catalogo() -> None:
    """GUARD-A: cada par estático debe existir en el catálogo no LEGACY."""
    offenses: list[str] = []
    entries, entries_by_code = _load_catalog()
    catalog_by_key = {entry.key: entry for entry in entries}

    for emission in _extract_all_emissions():
        location = f"{emission.file}:{emission.line}"
        if emission.entity_type is None:
            matches = entries_by_code.get(emission.action, [])
            active_or_deprecated = [
                entry for entry in matches if entry.lifecycle != "LEGACY"
            ]
            if not active_or_deprecated:
                offenses.append(
                    f"{OD_AUD_04} {DESIGN_DOC}: acción literal "
                    f"'{emission.action}' sin entidad resuelta y sin entrada "
                    f"no LEGACY en catálogo: {location}"
                )
            continue

        entry = catalog_by_key.get((emission.action, emission.entity_type))
        if entry is None:
            offenses.append(
                f"{OD_AUD_04} {DESIGN_DOC}: par inventado "
                f"('{emission.action}', '{emission.entity_type}') fuera del "
                f"catálogo: {location}"
            )
        elif entry.lifecycle == "LEGACY":
            offenses.append(
                f"{OD_AUD_04} {DESIGN_DOC}: par "
                f"('{emission.action}', '{emission.entity_type}') es LEGACY: "
                f"{location}"
            )

    assert offenses == [], "\n".join(offenses)


def test_guard_b_audit_event_solo_en_shared() -> None:
    """GUARD-B: `AuditEvent(` solo puede construirse en `app/shared/audit.py`."""
    offenses: list[str] = []
    audit_file = APP / "shared" / "audit.py"

    for file_path in _python_files(APP):
        relative = str(file_path.relative_to(APP)).replace("\\", "/")
        if file_path == audit_file:
            continue
        tree = ast.parse(
            file_path.read_text(encoding="utf-8"), filename=str(file_path)
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                is_audit_event = (
                    isinstance(func, ast.Name) and func.id == "AuditEvent"
                ) or (
                    isinstance(func, ast.Attribute)
                    and func.attr == "AuditEvent"
                )
                if is_audit_event:
                    offenses.append(
                        f"{OD_AUD_04} {DESIGN_DOC}: construcción de AuditEvent "
                        f"fuera de {AUDIT_MODULE}: {relative}:{node.lineno}"
                    )

    assert offenses == [], "\n".join(offenses)


def _emission_has_static_code(entry_code: str, source_by_path: dict[str, ast.AST]) -> bool:
    for tree in source_by_path.values():
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == entry_code:
                return True
    return False


def test_guard_c_catalogo_activo_rastreable() -> None:
    """GUARD-C: cada entrada ACTIVE tiene rastro de emisión o justificación."""
    offenses: list[str] = []
    entries, _ = _load_catalog()

    app_files = _walk_app_files()
    source_by_path: dict[str, ast.AST] = {}
    for file_path in app_files:
        relative = str(file_path.relative_to(APP)).replace("\\", "/")
        source_by_path[relative] = ast.parse(
            file_path.read_text(encoding="utf-8"), filename=str(file_path)
        )

    all_emissions = _extract_all_emissions()
    emitted_keys = {
        (emission.action, emission.entity_type)
        for emission in all_emissions
        if emission.entity_type is not None
    }

    for entry in entries:
        if entry.lifecycle == "DEPRECATED":
            continue

        if entry.lifecycle == "ACTIVE":
            if entry.emission == "STATIC":
                if not _emission_has_static_code(entry.code, source_by_path):
                    offenses.append(
                        f"{OD_AUD_04} {DESIGN_DOC}: entrada ACTIVE/STATIC "
                        f"'{entry.code}/{entry.entity_type}' sin literal de código "
                        f"en el árbol"
                    )
            elif entry.emission == "DYNAMIC":
                if not re.fullmatch(r"[^:]+:[^:]+", entry.emitted_by):
                    offenses.append(
                        f"{OD_AUD_04} {DESIGN_DOC}: entrada ACTIVE/DYNAMIC "
                        f"'{entry.code}/{entry.entity_type}' con emitted_by inválido: "
                        f"{entry.emitted_by!r}"
                    )
                    continue
                relative, function_name = entry.emitted_by.rsplit(":", 1)
                destination = APP / "modules" / relative
                if not destination.exists():
                    offenses.append(
                        f"{OD_AUD_04} {DESIGN_DOC}: entrada ACTIVE/DYNAMIC "
                        f"'{entry.code}/{entry.entity_type}' apunta a fichero "
                        f"inexistente: {relative}"
                    )
                    continue
                tree = ast.parse(
                    destination.read_text(encoding="utf-8"),
                    filename=str(destination),
                )
                if _find_function_def(tree, function_name) is None:
                    offenses.append(
                        f"{OD_AUD_04} {DESIGN_DOC}: entrada ACTIVE/DYNAMIC "
                        f"'{entry.code}/{entry.entity_type}' no define la función "
                        f"'{function_name}' en {relative}"
                    )
            elif entry.emission == "MIGRATION":
                candidatas = re.findall(r"\d{4}_[a-z0-9_]+", entry.emitted_by)
                if not any(
                    (ALEMBIC / f"{candidata}.py").exists()
                    for candidata in candidatas
                ):
                    offenses.append(
                        f"{OD_AUD_04} {DESIGN_DOC}: entrada '{entry.code}/"
                        f"{entry.entity_type}' MIGRATION sin revisión en alembic: "
                        f"{entry.emitted_by!r}"
                    )
            elif entry.emission == "RESERVED":
                if not entry.emitted_by:
                    offenses.append(
                        f"{OD_AUD_04} {DESIGN_DOC}: entrada '{entry.code}/"
                        f"{entry.entity_type}' RESERVED sin justificación"
                    )
        elif entry.lifecycle == "LEGACY":
            if not entry.emitted_by:
                offenses.append(
                    f"{OD_AUD_04} {DESIGN_DOC}: entrada LEGACY '{entry.code}/"
                    f"{entry.entity_type}' sin justificación"
                )
            if entry.key in emitted_keys:
                offenses.append(
                    f"{OD_AUD_04} {DESIGN_DOC}: par LEGACY emitido "
                    f"('{entry.code}', '{entry.entity_type}')"
                )

    assert offenses == [], "\n".join(offenses)


def _prefix_of_joined_str(value: ast.JoinedStr) -> str:
    prefix_parts: list[str] = []
    for element in value.values:
        if isinstance(element, ast.FormattedValue):
            break
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            prefix_parts.append(element.value)
    return "".join(prefix_parts)


def test_guard_d_familias_dinamicas_con_prefijo() -> None:
    """GUARD-D: f-string de acción exige prefijo dinámico catalogado."""
    offenses: list[str] = []
    entries, _ = _load_catalog()

    for file_path in _walk_app_files():
        relative = str(file_path.relative_to(APP)).replace("\\", "/")
        tree = ast.parse(
            file_path.read_text(encoding="utf-8"), filename=str(file_path)
        )
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _is_emitter(node.func):
                continue
            action_value: ast.expr | None = None
            for keyword in node.keywords:
                if keyword.arg in {"action", "accion"}:
                    action_value = keyword.value
                    break
            if action_value is None:
                action_value = _argument_value(
                    node, "action", tree, relative
                )
            if not isinstance(action_value, ast.JoinedStr):
                continue

            prefix = _prefix_of_joined_str(action_value)
            if not prefix:
                continue

            containing_name: str | None = None
            for function_node in ast.walk(tree):
                if not isinstance(
                    function_node, ast.FunctionDef | ast.AsyncFunctionDef
                ):
                    continue
                if function_node.lineno <= node.lineno <= (
                    function_node.end_lineno or function_node.lineno
                ):
                    containing_name = function_node.name
            if containing_name is None:
                continue

            matches = [
                entry
                for entry in entries
                if entry.code.startswith(prefix)
                and entry.lifecycle == "ACTIVE"
                and entry.emission == "DYNAMIC"
                and entry.emitted_by.endswith(f":{containing_name}")
            ]
            if not matches:
                offenses.append(
                    f"{OD_AUD_04} {DESIGN_DOC}: familia dinámica '{prefix}' "
                    f"sin entrada ACTIVE/DYNAMIC apuntando a '{containing_name}'"
                    f": {relative}:{node.lineno}"
                )

    assert offenses == [], "\n".join(offenses)


def test_guard_detecta_un_par_inventado() -> None:
    """El resolutor detecta un par inventado y hay cobertura mínima."""
    synthetic = 'record_audit(db, action="ACCION_FALSA", entity_type="Nada")'
    emissions = _extract_from_source(synthetic)
    assert len(emissions) == 1
    emission = emissions[0]
    assert emission.action == "ACCION_FALSA"
    assert emission.entity_type == "Nada"

    catalog_map = _catalog_map()
    assert (emission.action, emission.entity_type) not in catalog_map

    all_emissions = _extract_all_emissions()
    literal_pairs = [item for item in all_emissions if item.entity_type is not None]
    distinct_literal_pairs = {
        (emission.action, emission.entity_type)
        for emission in literal_pairs
    }
    assert len(distinct_literal_pairs) >= 160, (
        "Cobertura estática insuficiente: "
        f"{len(distinct_literal_pairs)} pares literales distintos encontrados"
    )
