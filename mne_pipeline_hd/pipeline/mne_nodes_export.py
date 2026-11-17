"""Export simple MNE-Pipeline-HD custom functions as path-loaded plugins."""

from __future__ import annotations

import argparse
import ast
import builtins
import csv
import json
import keyword
import re
import tokenize
from copy import deepcopy
from pathlib import Path
from typing import NamedTuple

# Pipeline-HD data types (``load_<type>``/``save_<type>``) mapped to port names.
_DATA_TYPES = {
    "raw": "raw",
    "filtered": "raw",
    "epochs": "epochs",
    "events": "events",
    "evokeds": "evokeds",
    "forward": "forward",
    "noise_covariance": "covariance",
}
# ``group.load_items(data_type=...)`` items and group-level data types.
_GROUP_ITEMS = {"evoked": "evokeds", "epochs": "epochs"}
_GROUP_TYPES = {"ga_evokeds": "ga_evokeds"}
# Widget: (accepted default types, supported widget options).
_GUI_TYPES = {
    "BoolGui": (bool, set()),
    "IntGui": (int, {"min_val", "max_val"}),
    "FloatGui": ((int, float), {"min_val", "max_val", "step", "decimals"}),
    "StringGui": (str, set()),
    "ListGui": (list, set()),
    "TupleGui": (tuple, set()),
    "DictGui": (dict, set()),
    "ComboGui": (str, {"options", "editable"}),
    "CheckListGui": (list, {"options", "one_check"}),
    "SliderGui": ((int, float), {"min_val", "max_val", "step"}),
    "PathGui": (str, {"pick_mode"}),
    "ColorGui": (str, {"output_format"}),
    "ColorDictGui": (dict, {"keys", "output_format"}),
}
_HINTS = {"min_val", "max_val", "step", "decimals"}
_DEFAULT_BOUNDS = {
    "IntGui": (0, 1000),
    "FloatGui": (-1000, 1000),
    "SliderGui": (0, 100),
}
_SETTING_GUIS = {
    bool: "BoolGui",
    int: "IntGui",
    float: "FloatGui",
    str: "StringGui",
    list: "ListGui",
    dict: "DictGui",
}
_PIPELINE_OBJECTS = {"meeg", "fsmri", "group", "ct"}
_OPERATIONS_LICENSE = """\
BSD 3-Clause License

Copyright (c) 2019-2024, authors of mne-pipeline-hd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


class _Source(NamedTuple):
    """Module-level context shared by all function conversions."""

    parameters: dict[str, dict[str, str]]
    imports: dict[str, ast.stmt]
    helpers: dict[str, ast.FunctionDef]
    settings: dict


# --------------------------------------------------------------------------- #
# Parameters
# --------------------------------------------------------------------------- #


def _encode_tuples(value):
    if isinstance(value, tuple):
        return {"tuple_type": [_encode_tuples(item) for item in value]}
    if isinstance(value, list):
        return [_encode_tuples(item) for item in value]
    if isinstance(value, dict):
        return {key: _encode_tuples(item) for key, item in value.items()}
    return value


def _read_csv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream, delimiter=";")
        if not rows.fieldnames or "" not in rows.fieldnames:
            raise ValueError(f"{path}: expected an unnamed first column")
        result = {}
        for row in rows:
            name = row.pop("")
            if not name or name in result or None in row:
                raise ValueError(
                    f"{path}: missing, duplicate, or malformed row {name!r}"
                )
            result[name] = row
        return result


def _literal(text: str):
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parameter(name: str, row: dict[str, str]) -> dict:
    gui = row.get("gui_type", "")
    default = _literal(row["default"]) if row.get("default") else None
    if gui == "ColorGui" and isinstance(default, dict):
        gui = "ColorDictGui"
    if gui not in _GUI_TYPES:
        raise ValueError(f"parameter {name!r} uses unsupported widget {gui!r}")
    expected, allowed = _GUI_TYPES[gui]
    options = _literal(row.get("gui_args") or "{}")
    if isinstance(options, dict):
        # Editing hints the target widget lacks only constrain input; drop them.
        options = {k: v for k, v in options.items() if k in allowed or k not in _HINTS}
    if not isinstance(options, dict) or set(options) - allowed - {"none_select"}:
        raise ValueError(f"parameter {name!r} has unsupported widget options")
    if gui in {"ComboGui", "CheckListGui"} and not isinstance(
        options.get("options"), list
    ):
        raise ValueError(f"parameter {name!r} requires a list of options")
    if default is None:
        if not options.get("none_select"):
            raise ValueError(f"parameter {name!r} has no usable default")
    elif not isinstance(default, expected) or (
        isinstance(default, bool) and gui != "BoolGui"
    ):
        raise ValueError(f"parameter {name!r} has an incompatible default")
    elif gui in _DEFAULT_BOUNDS:
        lower = options.get("min_val", _DEFAULT_BOUNDS[gui][0])
        upper = options.get("max_val", _DEFAULT_BOUNDS[gui][1])
        if not (_is_number(lower) and _is_number(upper) and lower <= default <= upper):
            raise ValueError(f"parameter {name!r} has a default outside widget bounds")
    config = {"gui": gui, "default": default}
    if gui == "ColorDictGui":
        config["keys"] = options.get("keys", [])
    config.update(
        {key: row[key] for key in ("alias", "description", "unit") if row.get(key)}
    )
    config.update(options)
    return config


def _function_parameter(name: str, source: _Source) -> dict:
    if name in source.parameters:
        return _parameter(name, source.parameters[name])
    if name not in source.settings:
        raise ValueError(f"missing parameter configuration for {name!r}")
    default = source.settings[name]
    gui = _SETTING_GUIS.get(type(default))
    if gui is None:
        raise ValueError(f"setting {name!r} has an unsupported default")
    config = {"gui": gui, "default": default}
    if gui in {"IntGui", "FloatGui"}:
        lower, upper = _DEFAULT_BOUNDS[gui]
        if default < lower:
            config["min_val"] = default
        if default > upper:
            config["max_val"] = default
    return config


# --------------------------------------------------------------------------- #
# AST helpers
# --------------------------------------------------------------------------- #


def _is_name(node, ids=None) -> bool:
    return isinstance(node, ast.Name) and (ids is None or node.id in ids)


def _attr(node, owner: str | None = None, attrs=None) -> str | None:
    """Return ``attr`` of ``owner.attr`` (any variable if ``owner`` is None)."""
    if (
        isinstance(node, ast.Attribute)
        and _is_name(node.value, None if owner is None else {owner})
        and (attrs is None or node.attr in attrs)
    ):
        return node.attr
    return None


def _call(node, owner: str | None = None, attrs=None) -> str | None:
    """Return the method name of a call ``owner.method(...)``."""
    return _attr(node.func, owner, attrs) if isinstance(node, ast.Call) else None


def _io_call(node, owner: str, prefix: str) -> str | None:
    """Return the data type of an I/O call such as ``meeg.load_raw()``."""
    method = _call(node, owner)
    if method and method.startswith(prefix):
        return method[len(prefix) :]
    return None


def _assigned(statement) -> str | None:
    """Return the target of a simple ``name = value`` statement."""
    if (
        isinstance(statement, ast.Assign)
        and len(statement.targets) == 1
        and isinstance(statement.targets[0], ast.Name)
    ):
        return statement.targets[0].id
    return None


def _expr_call(statement) -> ast.Call | None:
    if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
        return statement.value
    return None


def _source_args(call: ast.Call) -> list[str]:
    return [ast.unparse(arg) for arg in call.args]


def _names(node) -> set[str]:
    """Return all variable and argument names used in ``node``."""
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)} | {
        n.arg for n in ast.walk(node) if isinstance(n, ast.arg)
    }


def _stored(node) -> set[str]:
    return {
        n.id
        for n in ast.walk(node)
        if isinstance(n, ast.Name) and not isinstance(n.ctx, ast.Load)
    }


def _uses(nodes, name: str) -> bool:
    return any(_is_name(n, {name}) for node in nodes for n in ast.walk(node))


def _contains(node, *types) -> bool:
    return any(isinstance(n, types) for n in ast.walk(node))


def _expr(code: str) -> ast.expr:
    return ast.parse(code, mode="eval").body


def _stmt(code: str) -> ast.stmt:
    return ast.parse(code).body[0]


def _bound_name(alias: ast.alias) -> str:
    return alias.asname or alias.name.split(".")[0]


def _is_hd_import(node) -> bool:
    if isinstance(node, ast.ImportFrom):
        return (node.module or "").startswith("mne_pipeline_hd")
    return isinstance(node, ast.Import) and any(
        alias.name.startswith("mne_pipeline_hd") for alias in node.names
    )


def _is_join_import(node: ast.stmt | None) -> bool:
    return (
        isinstance(node, ast.ImportFrom)
        and node.module == "os.path"
        and any(
            alias.name == "join" and alias.asname in (None, "join")
            for alias in node.names
        )
    )


def _is_join(node, source: _Source, first: str) -> bool:
    """Check for ``join(<first>, ...)`` with ``join`` from ``os.path``."""
    return (
        isinstance(node, ast.Call)
        and _is_name(node.func, {"join"})
        and _is_join_import(source.imports.get("join"))
        and bool(node.args)
        and ast.unparse(node.args[0]) == first
        and not node.keywords
    )


def _plot_figure(call: ast.Call) -> str:
    """Return the figure variable of ``obj.plot_save("name", matplotlib_figure=fig)``."""
    if (
        len(call.args) != 1
        or not isinstance(call.args[0], ast.Constant)
        or len(call.keywords) != 1
        or call.keywords[0].arg != "matplotlib_figure"
        or not _is_name(call.keywords[0].value)
    ):
        raise ValueError("unsupported plot save")
    return call.keywords[0].value.id


def _is_show(statement, figures) -> bool:
    """Check for ``if show_plots: fig.show()``."""
    return (
        isinstance(statement, ast.If)
        and _is_name(statement.test)
        and not statement.orelse
        and len(statement.body) == 1
        and ast.unparse(statement.body[0]) in {f"{fig}.show()" for fig in figures}
    )


def _parents(node) -> dict[ast.AST, ast.AST]:
    return {
        child: parent
        for parent in ast.walk(node)
        for child in ast.iter_child_nodes(parent)
    }


class _Replace(ast.NodeTransformer):
    """Replace nodes by identity; a ``None`` replacement removes a statement."""

    def __init__(self, replacements: dict[int, ast.AST | None]):
        self.replacements = replacements

    def visit(self, node):
        if id(node) not in self.replacements:
            return super().visit(node)
        new = self.replacements.pop(id(node))
        return None if new is None else self.generic_visit(ast.copy_location(new, node))


def _check_function(fn: ast.FunctionDef, metadata: dict, first: str | None) -> None:
    """Reject signatures and constructs that cannot be converted safely."""
    if metadata.get("dependencies"):
        raise ValueError("declared function dependencies need manual conversion")
    args = fn.args
    if (
        fn.decorator_list
        or args.posonlyargs
        or args.kwonlyargs
        or args.vararg
        or args.kwarg
    ):
        raise ValueError("unsupported function signature or decorator")
    if first and (
        not args.args
        or args.args[0].arg != first
        or len(args.defaults) == len(args.args)
    ):
        raise ValueError(f"expected {first} as a required first argument")
    if _contains(fn, ast.Global, ast.Nonlocal, ast.Yield, ast.YieldFrom, ast.Await):
        raise ValueError("generators or global state need manual conversion")
    nested = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
    if any(_contains(statement, *nested) for statement in fn.body):
        raise ValueError("nested functions need manual conversion")
    if any(_is_hd_import(node) for node in ast.walk(fn)):
        raise ValueError("depends on mne_pipeline_hd imports")


def _helper_error(helper: ast.FunctionDef) -> bool:
    """Check whether a module helper touches pipeline state or files."""
    for node in ast.walk(helper):
        if isinstance(node, (ast.Global, ast.Nonlocal)) or _is_name(
            node, _PIPELINE_OBJECTS
        ):
            return True
        if _is_hd_import(node):
            return True
        if isinstance(node, ast.Call):
            method = node.func.attr if isinstance(node.func, ast.Attribute) else ""
            if method.startswith(("load_", "save_")) or method in {
                "read_csv",
                "to_csv",
            }:
                return True
            if _is_name(node.func, {"open"}):
                return True
    return bool(helper.decorator_list)


def _dependencies(fn: ast.FunctionDef, source: _Source) -> tuple[set[str], set[str]]:
    """Return module imports/constants and helper functions used by ``fn``."""
    needed_imports, needed_helpers = set(), set()

    def visit(function):
        local_imports = {
            _bound_name(alias)
            for node in ast.walk(function)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        used = {
            n.id
            for n in ast.walk(function)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
        }
        external = used - _stored(function) - local_imports - _names(function.args)
        for item in external:
            if item in source.helpers:
                if item in needed_helpers:
                    continue
                if _helper_error(source.helpers[item]):
                    raise ValueError(f"helper {item!r} needs manual conversion")
                needed_helpers.add(item)
                visit(source.helpers[item])
            elif item in source.imports:
                node = source.imports[item]
                if isinstance(node, ast.ImportFrom) and node.level:
                    raise ValueError("relative imports need manual conversion")
                if _is_hd_import(node):
                    raise ValueError("depends on mne_pipeline_hd imports")
                needed_imports.add(item)
            elif item not in dir(builtins):
                raise ValueError(
                    f"module helper or global {item!r} needs manual conversion"
                )

    visit(fn)
    return needed_imports, needed_helpers


def _finish(
    fn: ast.FunctionDef,
    metadata: dict,
    source: _Source,
    target: str,
    inputs: dict[str, str],
    outputs: dict[str, str],
    parameters: dict[str, dict],
):
    """Build the node configuration and collect the function's dependencies."""
    config = {
        "inputs": {
            name: {"accepted_ports": [port], "optional": False}
            for name, port in inputs.items()
        },
        "parameters": parameters,
        "outputs": {name: {"accepted_ports": [port]} for name, port in outputs.items()},
        "target": target,
        "category": metadata.get("group") or "custom",
        "sub_category": metadata.get("tab") or None,
        "description": ast.get_docstring(fn) or "",
        "module_name": None,
        "class_name": None,
    }
    fn = ast.fix_missing_locations(fn)
    return fn, config, *_dependencies(fn, source)


def _returned(names) -> ast.expr:
    return _expr(", ".join(names))


# --------------------------------------------------------------------------- #
# MEEG functions
# --------------------------------------------------------------------------- #


def _unwrap_conditional_io(fn: ast.FunctionDef, start: int) -> None:
    """Replace matching raw/filtered selection with one explicit raw input."""
    first, last = fn.body[start], fn.body[-1]
    if not isinstance(first, ast.If) or not isinstance(last, ast.If):
        return
    test = first.test
    args = [arg.arg for arg in fn.args.args]
    if not (
        isinstance(test, ast.Compare)
        and _is_name(test.left, set(args[1:]))
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Eq)
        and isinstance(test.comparators[0], ast.Constant)
        and ast.dump(test) == ast.dump(last.test)
    ):
        return
    if any(len(b) != 1 for b in (first.body, first.orelse, last.body, last.orelse)):
        return
    loads, saves = [first.body[0], first.orelse[0]], [last.body[0], last.orelse[0]]
    names = set()
    for load, save in zip(loads, saves):
        name = _assigned(load)
        kind = _io_call(load.value, "meeg", "load_") if name else None
        call = _expr_call(save)
        if (
            _DATA_TYPES.get(kind) != "raw"
            or load.value.args
            or load.value.keywords
            or call is None
            or _io_call(call, "meeg", "save_") != kind
            or call.keywords
            or _source_args(call) != [name]
        ):
            return
        names.add(name)
    if len(names) != 1:
        return
    selector = test.left.id
    index = args.index(selector)
    default_start = len(args) - len(fn.args.defaults)
    if index >= default_start:
        try:
            ast.literal_eval(fn.args.defaults[index - default_start])
        except (ValueError, SyntaxError):
            return
    fn.body[start], fn.body[-1] = loads[0], saves[0]
    if _uses(fn.body, selector):
        return
    if index >= default_start:
        del fn.args.defaults[index - default_start]
    del fn.args.args[index]


def _terminal_save(body: list[ast.stmt], target: ast.Expr) -> bool:
    if not body:
        return False
    last = body[-1]
    if last is target:
        return True
    if isinstance(last, ast.If):
        return _terminal_save(last.body, target) or _terminal_save(last.orelse, target)
    return False


def _extract_csv_io(
    fn: ast.FunctionDef, source: _Source
) -> tuple[str | None, str | None, ast.Expr | None]:
    """Turn a simple Pipeline-HD CSV sidecar into a DataFrame port.

    Returns the input variable, the output variable and its ``to_csv`` statement.
    """
    nothing = None, None, None
    found = {
        name: [s for s in fn.body if _assigned(s) == name]
        for name in ("file_name", "file_path")
    }
    if any(len(statements) != 1 for statements in found.values()):
        return nothing
    filename, path = found["file_name"][0], found["file_path"][0]
    if not (
        isinstance(filename.value, ast.Constant)
        and isinstance(filename.value.value, str)
        and _is_join(path.value, source, "meeg.save_dir")
        and len(path.value.args) == 2
        and isinstance(path.value.args[1], ast.JoinedStr)
    ):
        return nothing
    for part in path.value.args[1].values:
        if isinstance(part, ast.FormattedValue) and (
            part.format_spec is not None
            or ast.unparse(part.value)
            not in {"file_name", "meeg.name", "meeg.p_preset"}
        ):
            return nothing
    uses = sorted(
        n.id
        for n in ast.walk(fn)
        if _is_name(n, {"file_name", "file_path"}) and isinstance(n.ctx, ast.Load)
    )
    if uses != ["file_name", "file_path"]:
        return nothing
    reader = writer = None
    for statement in fn.body:
        call = statement.value if _assigned(statement) else _expr_call(statement)
        if not isinstance(call, ast.Call) or _source_args(call) != ["file_path"]:
            continue
        if (
            _assigned(statement)
            and _call(call, "pd", {"read_csv"})
            and all(
                k.arg == "index_col" and ast.unparse(k.value) == "0"
                for k in call.keywords
            )
        ):
            reader = statement
        elif (
            not _assigned(statement)
            and _call(call, None, {"to_csv"})
            and not call.keywords
        ):
            writer = statement
    pandas = source.imports.get("pd")
    if (reader or writer) is None or not (
        isinstance(pandas, ast.Import)
        and any(a.name == "pandas" and a.asname == "pd" for a in pandas.names)
    ):
        return nothing
    csv_input = _assigned(reader) if reader else None
    csv_output = writer.value.func.value.id if writer else None
    if csv_input and _uses(fn.body[: fn.body.index(reader)], csv_input):
        return nothing
    if csv_output and not any(
        csv_output in _stored(n) and _call(n.value, "pd", {"DataFrame"})
        for n in ast.walk(fn)
        if isinstance(n, ast.Assign)
    ):
        return nothing
    fn.body = [s for s in fn.body if s not in (filename, path, reader)]
    return csv_input, csv_output, writer


def _convert_meeg(fn: ast.FunctionDef, metadata: dict, source: _Source):
    _check_function(fn, metadata, "meeg")
    start = int(bool(ast.get_docstring(fn)))
    if len(fn.body) < start + 2:
        raise ValueError("expected an unconditional load and save")
    _unwrap_conditional_io(fn, start)
    csv_input, csv_output, csv_save = _extract_csv_io(fn, source)
    inputs, outputs, loads = {}, {}, []
    for index, statement in enumerate(fn.body):
        name = _assigned(statement)
        kind = _io_call(statement.value, "meeg", "load_") if name else None
        if kind is None:
            continue
        if (
            name in inputs
            or kind not in _DATA_TYPES
            or statement.value.args
            or statement.value.keywords
        ):
            raise ValueError("unsupported or duplicate load")
        if _uses(fn.body[:index], name):
            raise ValueError("loaded variable is used before the load")
        inputs[name] = _DATA_TYPES[kind]
        loads.append(statement)
    saves = [
        n
        for n in ast.walk(fn)
        if isinstance(n, ast.Expr) and _io_call(n.value, "meeg", "save_")
    ]
    if not loads or len(saves) > 1 or not (saves or csv_save):
        raise ValueError("expected direct loads and at least one supported output")
    replace: dict[int, ast.AST | None] = {}
    if saves:
        save = saves[0]
        call, kind = save.value, _io_call(save.value, "meeg", "save_")
        if len(call.args) != 1 or call.keywords or not _is_name(call.args[0]):
            raise ValueError("unsupported save arguments")
        name = call.args[0].id
        if (
            kind not in _DATA_TYPES
            or inputs.get(name, _DATA_TYPES[kind]) != _DATA_TYPES[kind]
        ):
            raise ValueError("expected a save matching the loaded data type")
        if name not in inputs and fn.body[-1] is not save:
            raise ValueError("computed data must be saved at the end")
        if not _terminal_save(fn.body, save):
            raise ValueError("save is not terminal on its execution path")
        outputs[name] = _DATA_TYPES[kind]
        replace[id(save)] = ast.Pass()
    if csv_output:
        if csv_output in outputs:
            raise ValueError("CSV output conflicts with another output")
        outputs[csv_output] = "dataframe"
        if f"_exported_{csv_output}" in _names(fn):
            raise ValueError("CSV snapshot conflicts with an existing variable")
        replace[id(csv_save)] = _stmt(
            f"_exported_{csv_output} = {csv_output}.copy(deep=True)"
        )
    if any(isinstance(n, ast.Return) and n.value is not None for n in ast.walk(fn)):
        raise ValueError("return values need manual conversion")
    if set(outputs) - set(inputs) and _contains(fn, ast.Return):
        raise ValueError("early return may not produce the output")
    if csv_input:
        if csv_input in inputs:
            raise ValueError("CSV input conflicts with a loaded variable")
        inputs[csv_input] = "dataframe"
    fn.body = [s for s in fn.body if s not in loads]
    fn = _Replace(replace).visit(fn)
    attributes = {_attr(n, "meeg") for n in ast.walk(fn)} - {None}
    if attributes - {"name", "bad_channels"}:
        raise ValueError("additional meeg state or I/O needs manual conversion")
    if "name" in attributes:
        inputs["recording_name"] = "recording_name"
    if "bad_channels" in attributes:
        inputs["bad_channels"] = outputs["bad_channels"] = "bad_channels"
    parameters = [arg.arg for arg in fn.args.args[1:]]
    added = set(inputs) - {_assigned(s) for s in loads}
    if added & (_stored(fn) | set(parameters)) or set(inputs) & set(parameters):
        raise ValueError("an input conflicts with an existing variable or parameter")
    returned = [f"_exported_{n}" if n == csv_output else n for n in outputs]
    names = {"name": "recording_name", "bad_channels": "bad_channels"}
    for node in ast.walk(fn):
        if attr := _attr(node, "meeg"):
            replace[id(node)] = ast.Name(id=names[attr], ctx=node.ctx)
        elif isinstance(node, ast.Return):
            replace[id(node)] = ast.Return(value=_returned(returned))
    fn = _Replace(replace).visit(fn)
    if _uses([fn], "meeg"):
        raise ValueError("additional meeg state or I/O needs manual conversion")
    fn.args.args[:1] = [ast.arg(arg=name) for name in inputs]
    fn.body.append(ast.Return(value=_returned(returned)))
    params = {name: _function_parameter(name, source) for name in parameters}
    return _finish(fn, metadata, source, "file", inputs, outputs, params)


# --------------------------------------------------------------------------- #
# FSMRI label functions
# --------------------------------------------------------------------------- #


def _convert_labels(fn: ast.FunctionDef, metadata: dict, source: _Source):
    _check_function(fn, metadata, "fsmri")
    if _contains(fn, ast.Return):
        raise ValueError("return values need manual conversion")
    loads = [n for n in ast.walk(fn) if _call(n, "fsmri", {"get_labels"})]
    saves = [
        n
        for n in ast.walk(fn)
        if isinstance(n, ast.Expr) and _call(n.value, None, {"save"})
    ]
    if len(loads) != 1 or len(saves) != 1:
        raise ValueError("expected one label selection and one label save")
    load, save = loads[0], saves[0].value
    path = save.args[0] if len(save.args) == 1 and not save.keywords else None
    if len(load.args) != 1 or not _is_name(load.args[0]) or load.keywords:
        raise ValueError("unsupported label selection")
    if not (
        _is_join(path, source, "fsmri.subjects_dir")
        and _source_args(path)[1:3] == ["fsmri.name", "'label'"]
        and len(path.args) == 4
        and isinstance(path.args[3], ast.JoinedStr)
        and all(
            isinstance(part, ast.Constant)
            or (_is_name(part.value) and part.format_spec is None)
            for part in path.args[3].values
        )
    ):
        raise ValueError("unsupported label save path")
    if {"available_labels", "combined_labels", "_label"} & _names(fn):
        raise ValueError("label port conflicts with an existing variable")
    selection = load.args[0].id
    label = ast.unparse(save.func.value)
    fn = _Replace(
        {
            id(load): _expr(
                f"[_label for _label in available_labels if _label.name in {selection}]"
            ),
            id(saves[0]): _stmt(f"combined_labels.append({label})"),
        }
    ).visit(fn)
    if _uses([fn], "fsmri"):
        raise ValueError("additional MRI state or I/O needs manual conversion")
    fn.args.args[0] = ast.arg(arg="available_labels")
    fn.body.insert(int(bool(ast.get_docstring(fn))), _stmt("combined_labels = []"))
    fn.body.append(_stmt("return combined_labels"))
    params = {arg.arg: _function_parameter(arg.arg, source) for arg in fn.args.args[1:]}
    inputs, outputs = {"available_labels": "labels"}, {"combined_labels": "labels"}
    return _finish(fn, metadata, source, "file", inputs, outputs, params)


# --------------------------------------------------------------------------- #
# Group functions
# --------------------------------------------------------------------------- #


def _group_output(statement, source: _Source) -> tuple[str, str] | None:
    """Return (variable, port) for a group plot, figure or data save."""
    call = _expr_call(statement)
    if call is None:
        return None
    if _call(call, "group", {"plot_save"}):
        return _plot_figure(call), "figure"
    if (kind := _io_call(call, "group", "save_")) is not None:
        if kind not in _GROUP_TYPES or call.keywords or len(call.args) != 1:
            raise ValueError(f"unsupported group save {kind!r}")
        if not _is_name(call.args[0]):
            raise ValueError("unsupported group save arguments")
        return call.args[0].id, _GROUP_TYPES[kind]
    if (
        _call(call, None, {"savefig"})
        and len(call.args) == 1
        and _is_join(call.args[0], source, "group.save_dir")
    ):
        return call.func.value.id, "figure"
    return None


def _convert_group(fn: ast.FunctionDef, metadata: dict, source: _Source):
    _check_function(fn, metadata, "group")
    if _contains(fn, ast.Return):
        raise ValueError("group control flow needs manual conversion")
    reserved = {"group_data", "recording_names", "recording_name", "group_name"}
    if (reserved | {"sel_trials"}) & _names(fn):
        raise ValueError("group port conflicts with an existing variable")
    inputs, outputs, replace = {}, {}, {}
    # Iterations over the group's recordings become two list inputs.
    loops = [
        n
        for n in ast.walk(fn)
        if isinstance(n, ast.For) and _call(n.iter, "group", {"load_items"})
    ]
    item_types, recordings = set(), {}
    for loop in loops:
        options = {k.arg: ast.literal_eval(k.value) for k in loop.iter.keywords}
        if (
            loop.iter.args
            or loop.orelse
            or set(options) - {"data_type", "obj_type"}
            or options.get("obj_type", "MEEG") != "MEEG"
            or options.get("data_type") not in _GROUP_ITEMS
        ):
            raise ValueError("unsupported group data type")
        target = loop.target
        if not (
            isinstance(target, ast.Tuple)
            and len(target.elts) == 2
            and all(_is_name(item) for item in target.elts)
        ):
            raise ValueError("unsupported group iteration")
        item_types.add(_GROUP_ITEMS[options["data_type"]])
        recordings[id(target.elts[1])] = target.elts[1].id
        replace[id(loop.iter)] = _expr("zip(group_data, recording_names)")
        replace[id(target.elts[1])] = ast.Name(id="recording_name", ctx=ast.Store())
    if len(item_types) > 1:
        raise ValueError("mixed group data types need manual conversion")
    parents = _parents(fn)
    for node in ast.walk(fn):
        if not _is_name(node, set(recordings.values())) or id(node) in recordings:
            continue
        parent = parents.get(node)
        if (
            not isinstance(node.ctx, ast.Load)
            or _attr(parent, node.id, {"name"}) is None
        ):
            raise ValueError("recording object needs manual conversion")
        replace[id(parent)] = ast.Name(id="recording_name", ctx=ast.Load())
    if loops:
        inputs = {"group_data": item_types.pop(), "recording_names": "recording_names"}
    # Group-level loads, e.g. ``ga_evokeds = group.load_ga_evokeds()``.
    removed = []
    for index, statement in enumerate(fn.body):
        name = _assigned(statement)
        kind = _io_call(statement.value, "group", "load_") if name else None
        if kind is None:
            continue
        if kind not in _GROUP_TYPES or statement.value.args or statement.value.keywords:
            raise ValueError(f"unsupported group load {kind!r}")
        if name in inputs or _uses(fn.body[:index], name):
            raise ValueError("loaded variable is used before the load")
        inputs[name] = _GROUP_TYPES[kind]
        removed.append(statement)
    if not inputs:
        raise ValueError("expected group data loads")
    # Final plot or data saves become outputs.
    for index, statement in enumerate(fn.body):
        if output := _group_output(statement, source):
            break
    else:
        raise ValueError("expected a group plot or data save")
    for statement in fn.body[index:]:
        if output := _group_output(statement, source):
            outputs[output[0]] = output[1]
            removed.append(statement)
        elif not _is_show(statement, outputs):
            raise ValueError("code after saving needs manual conversion")
    fn.body = [s for s in fn.body if s not in removed]
    selected_trials = False
    for node in ast.walk(fn):
        if attr := _attr(node, "group", {"name", "sel_trials"}):
            new_name = "group_name" if attr == "name" else "sel_trials"
            replace[id(node)] = ast.Name(id=new_name, ctx=ast.Load())
            if attr == "name":
                inputs["group_name"] = "group_name"
            selected_trials |= attr == "sel_trials"
    fn = _Replace(replace).visit(fn)
    if _uses([fn], "group"):
        raise ValueError("additional group state or I/O needs manual conversion")
    params = {arg.arg: _function_parameter(arg.arg, source) for arg in fn.args.args[1:]}
    extra = []
    if selected_trials:
        extra = [ast.arg(arg="sel_trials")]
        params = {
            "sel_trials": {
                "gui": "ListGui",
                "default": [],
                "description": "Trials (evoked comments) to process",
            },
            **params,
        }
    fn.args.args[:1] = [ast.arg(arg=name) for name in inputs] + extra
    if loops:
        guard = _stmt(
            "if len(group_data) != len(recording_names):\n"
            '    raise ValueError("Group data and names must have equal lengths")'
        )
        fn.body.insert(int(bool(ast.get_docstring(fn))), guard)
    fn.body.append(ast.Return(value=_returned(outputs)))
    return _finish(fn, metadata, source, "group", inputs, outputs, params)


def _convert_project(fn: ast.FunctionDef, metadata: dict, source: _Source):
    """Convert supported plots over named groups with explicit data inputs."""
    _check_function(fn, metadata, None)
    if [arg.arg for arg in fn.args.args].count("ct") != 1:
        raise ValueError("unsupported project function signature")
    group_import = source.imports.get("Group")
    if not (
        isinstance(group_import, ast.ImportFrom)
        and group_import.module == "mne_pipeline_hd.pipeline.loading"
        and any(
            a.name == "Group" and a.asname in (None, "Group")
            for a in group_import.names
        )
    ):
        raise ValueError("unsupported group constructor")
    if _contains(fn, ast.Return):
        raise ValueError("project control flow needs manual conversion")
    if "group_data" in _names(fn):
        raise ValueError("group input conflicts with an existing variable")

    def is_group(call):
        return (
            isinstance(call, ast.Call)
            and _is_name(call.func, {"Group"})
            and len(call.args) == 2
            and _is_name(call.args[1], {"ct"})
            and not call.keywords
        )

    assignments = [n for n in ast.walk(fn) if _assigned(n) and is_group(n.value)]
    group_vars = {_assigned(n) for n in assignments}
    if not group_vars:
        raise ValueError("no named group data found")
    loads = [
        n
        for n in ast.walk(fn)
        if isinstance(n, ast.Call)
        and _is_name(
            n.func.value if isinstance(n.func, ast.Attribute) else None, group_vars
        )
        and n.func.attr in {"load_ga_con", "load_items"}
    ]
    saves = [
        s
        for s in fn.body
        if (call := _expr_call(s))
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "plot_save"
        and (is_group(call.func.value) or _is_name(call.func.value, group_vars))
    ]
    if len(loads) != 1 or len(saves) != 1 or fn.body[-1] is not saves[0]:
        raise ValueError("expected one group load and a final plot save")
    load, save = loads[0], saves[0]
    figure = _plot_figure(save.value)
    if load.args:
        raise ValueError("unsupported group load")
    replace = {id(save): None}
    for n in assignments:
        replace[id(n.value)] = n.value.args[0]
    item_loop = None
    if load.func.attr == "load_ga_con":
        if load.keywords:
            raise ValueError("unsupported group connectivity load")
        input_port = "group_connectivity"
    else:
        options = {k.arg: ast.literal_eval(k.value) for k in load.keywords}
        if (
            set(options) - {"data_type", "obj_type"}
            or options.get("obj_type", "MEEG") != "MEEG"
            or options.get("data_type") != "epochs"
        ):
            raise ValueError("unsupported group item data type")
        item_loops = [
            n for n in ast.walk(fn) if isinstance(n, ast.For) and n.iter is load
        ]
        if len(item_loops) != 1:
            raise ValueError("expected direct iteration over group items")
        item_loop = item_loops[0]
        target = item_loop.target
        if not (
            isinstance(target, ast.Tuple)
            and len(target.elts) == 2
            and all(_is_name(item) for item in target.elts)
        ):
            raise ValueError("unsupported group item target")
        item, recording = target.elts
        if sum(_is_name(n, {recording.id}) for n in ast.walk(fn)) != 1:
            raise ValueError("group recording objects need manual conversion")
        replace[id(target)] = item
        input_port = "group_epochs"
    replace[id(load)] = _expr(f"group_data[{ast.unparse(load.func.value)}]")
    allowed = {"name", "group_list", "load_ga_con", "load_items", "plot_save"}
    targets = {id(n.targets[0]) for n in assignments}
    parents = _parents(fn)
    for node in ast.walk(fn):
        if _is_name(node, group_vars) and id(node) not in targets:
            parent = parents.get(node)
            if (
                not isinstance(node.ctx, ast.Load)
                or _attr(parent, node.id, allowed) is None
            ):
                raise ValueError("group object needs manual conversion")
            if parent.attr == "name":
                replace[id(parent)] = ast.Name(id=node.id, ctx=ast.Load())
            elif parent.attr == "group_list" and item_loop is not None:
                replace[id(parent)] = _expr(f"group_data[{node.id}]")
        elif ast.unparse(node) == "ct.pr.sel_groups":
            replace[id(node)] = _expr("list(group_data)")
    fn = _Replace(replace).visit(fn)
    for arg in fn.args.args:
        if arg.arg == "ct":
            arg.arg = "group_data"
    if (
        _uses([fn], "ct")
        or _uses([fn], "Group")
        or any(_attr(n, var) for n in ast.walk(fn) for var in group_vars)
    ):
        raise ValueError("additional project or group state needs manual conversion")
    fn.body.append(ast.Return(value=ast.Name(id=figure, ctx=ast.Load())))
    inputs, params, notes = {"group_data": input_port}, {}, []
    for arg in fn.args.args:
        if arg.arg == "group_data":
            continue
        try:
            params[arg.arg] = _function_parameter(arg.arg, source)
        except ValueError as error:
            inputs[arg.arg] = arg.arg
            notes.append(f"\nInput {arg.arg!r} is required: {error}.")
    result = _finish(fn, metadata, source, "group", inputs, {figure: "figure"}, params)
    result[1]["description"] += "".join(notes)
    return result


_CONVERTERS = {
    "MEEG": _convert_meeg,
    "FSMRI": _convert_labels,
    "Group": _convert_group,
    "Other": _convert_project,
}


def _convert(function: ast.FunctionDef, metadata: dict, source: _Source):
    converter = _CONVERTERS.get(metadata.get("target"))
    if converter is None:
        raise ValueError(f"target {metadata.get('target')!r} is not supported")
    return converter(deepcopy(function), metadata, source)


# --------------------------------------------------------------------------- #
# Module export
# --------------------------------------------------------------------------- #


def _module_names(tree: ast.Module) -> dict[str, ast.stmt]:
    """Map names bound by module-level imports and literal constants to nodes."""
    names = {}
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                continue
            names.update(
                {_bound_name(alias): node for alias in node.names if alias.name != "*"}
            )
        elif name := _assigned(node):
            try:
                ast.literal_eval(node.value)
            except (ValueError, SyntaxError, TypeError):
                continue
            names[name] = node
    return names


def _operation_helpers(tree: ast.Module, taken) -> dict[str, ast.FunctionDef]:
    """Copy functions imported from ``mne_pipeline_hd.functions.operations``."""
    path = Path(__file__).parent.parent / "functions" / "operations.py"
    available = {
        node.name: node
        for node in ast.parse(path.read_text(encoding="utf-8")).body
        if isinstance(node, ast.FunctionDef)
    }
    helpers = {}
    for node in tree.body:
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "mne_pipeline_hd.functions.operations"
        ):
            for alias in node.names:
                name = alias.asname or alias.name
                if name not in taken and alias.name in available:
                    helpers[name] = deepcopy(available[alias.name])
                    helpers[name].name = name
    return helpers


def _render(
    tree: ast.Module,
    source_text: str,
    source: _Source,
    converted: list[ast.FunctionDef],
    needed: set[str],
    needed_helpers: set[str],
    operation_helpers: dict[str, ast.FunctionDef],
) -> str:
    """Assemble the plugin module from the converted functions."""
    body = []
    if ast.get_docstring(tree, clean=False) is not None:
        body.append(tree.body[0])
    body += [
        n
        for n in tree.body
        if isinstance(n, ast.ImportFrom) and n.module == "__future__"
    ]
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            aliases = [
                alias
                for alias in node.names
                if alias.name != "*"
                and _bound_name(alias) in needed
                and source.imports.get(_bound_name(alias)) is node
            ]
            if aliases:
                imported = deepcopy(node)
                imported.names = aliases
                body.append(imported)
        elif isinstance(node, ast.Assign) and any(
            source.imports[name] is node for name in needed
        ):
            body.append(node)
    body += [
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name in needed_helpers
    ]
    copied = [
        node for name, node in operation_helpers.items() if name in needed_helpers
    ]
    body += copied + converted
    prefix_lines = source_text.splitlines(keepends=True)[: tree.body[0].lineno - 1]
    for index in range(min(2, len(prefix_lines))):
        prefix_lines[index] = re.sub(
            r"coding[:=][ \t]*[-\w.]+", "coding: utf-8", prefix_lines[index]
        )
    prefix = "".join(prefix_lines)
    if copied:
        prefix += "# Helpers copied from mne_pipeline_hd.functions.operations:\n"
        prefix += "".join(
            f"# {line}\n" if line else "#\n"
            for line in _OPERATIONS_LICENSE.splitlines()
        )
        prefix += "\n"
    module = ast.fix_missing_locations(ast.Module(body=body, type_ignores=[]))
    return prefix + ast.unparse(module) + "\n"


def _write_new(contents: list[tuple[Path, str]]) -> None:
    """Write all files or none, never replacing existing files."""
    for path, _ in contents:
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")
    created = []
    try:
        for path, content in contents:
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                created.append(path)
                stream.write(content)
    except OSError:
        for path in created:
            path.unlink()
        raise


def export_custom_functions(
    source: Path, functions_csv: Path, parameter_csvs: list[Path], destination: Path
) -> tuple[list[str], dict[str, str]]:
    """Export supported functions and return exported names and skipped reasons.

    CSVs are ordered from general to custom, so later parameter definitions win.
    No custom source code is executed; existing output files are never replaced.
    """
    source_path, destination = Path(source), Path(destination)
    stem = source_path.stem
    if (
        source_path.suffix != ".py"
        or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", stem)
        or keyword.iskeyword(stem)
    ):
        raise ValueError(f"Invalid plugin module name: {stem!r}")
    with tokenize.open(source_path) as stream:
        source_text = stream.read()
    tree = ast.parse(source_text, filename=str(source_path))
    rows = _read_csv(Path(functions_csv))
    if not rows:
        raise ValueError(f"{functions_csv}: no functions configured")
    parameters = {}
    for path in parameter_csvs:
        parameters.update(_read_csv(Path(path)))
    settings_path = Path(__file__).parent.parent / "extra" / "default_settings.json"
    defaults = json.loads(settings_path.read_text(encoding="utf-8"))
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    helpers = {name: fn for name, fn in functions.items() if name not in rows}
    operation_helpers = _operation_helpers(tree, helpers.keys() | rows.keys())
    helpers.update(operation_helpers)
    context = _Source(
        parameters,
        _module_names(tree),
        helpers,
        {**defaults["settings"], **defaults["qsettings"]},
    )
    converted, config, skipped, needed, needed_helpers = [], {}, {}, set(), set()
    for name, metadata in rows.items():
        try:
            if name not in functions:
                raise ValueError("function not found in source")
            if metadata.get("module") not in ("", stem):
                raise ValueError("function belongs to a different module")
            fn, entry, used, helper_names = _convert(functions[name], metadata, context)
        except ValueError as error:
            skipped[name] = str(error)
        else:
            converted.append(fn)
            config[name] = entry
            needed.update(used)
            needed_helpers.update(helper_names)
    if not converted:
        return [], skipped
    code = _render(
        tree, source_text, context, converted, needed, needed_helpers, operation_helpers
    )
    _write_new(
        [
            (destination / source_path.name, code),
            (
                destination / f"{stem}_config.json",
                json.dumps(_encode_tuples(config), indent=4) + "\n",
            ),
        ]
    )
    return list(config), skipped


def main() -> int:
    """Run the conservative converter from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("functions_csv", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--parameters", type=Path, action="append", default=[])
    args = parser.parse_args()
    exported, skipped = export_custom_functions(
        args.source,
        args.functions_csv,
        [Path(__file__).parent.parent / "extra" / "parameters.csv", *args.parameters],
        args.destination,
    )
    print(f"Exported: {', '.join(exported) or 'none'}")
    for name, reason in skipped.items():
        print(f"Skipped {name}: {reason}")
    return int(bool(skipped))


if __name__ == "__main__":
    raise SystemExit(main())
