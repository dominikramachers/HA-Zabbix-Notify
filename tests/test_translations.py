"""hassfest rejects curly braces in translations unless they are valid placeholders."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

TRANSLATIONS = sorted(
    (Path(__file__).parent.parent / "custom_components" / "zabbix_notify" / "translations").glob("*.json")
)
IDENTIFIER = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")


def _strings(node, path=""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _strings(value, f"{path}.{key}")
    elif isinstance(node, str):
        yield path, node


@pytest.mark.parametrize("file", TRANSLATIONS, ids=lambda f: f.name)
def test_placeholders_are_identifiers(file):
    for path, text in _strings(json.loads(file.read_text(encoding="utf-8"))):
        for placeholder in re.findall(r"\{([^}]*)\}", text):
            assert IDENTIFIER.fullmatch(placeholder), f"{file.name}{path}: {{{placeholder}}}"
