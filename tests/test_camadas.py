import ast
from pathlib import Path
import sys

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "src" / "manutencao"
LAYERS = {
    "dominio": {"dominio"},
    "aplicacao": {"aplicacao", "dominio"},
    "infraestrutura": {"infraestrutura", "aplicacao", "dominio"},
    "aapresentacao": {"aapresentacao", "aplicacao", "dominio"},
}


@pytest.mark.parametrize("layer", LAYERS)
def test_layer_imports_follow_dependency_rules(layer: str) -> None:
    external = {
        "aapresentacao": {"fastapi", "pydantic"},
        "infraestrutura": {"psycopg"},  # only the infrastructure talks to the database
    }.get(layer, set())
    for path in sorted((SOURCE / layer).rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level == 0, f"{path}:{node.lineno}: use absolute imports"
                modules = (
                    [f"manutencao.{alias.name}" for alias in node.names]
                    if node.module == "manutencao" else [node.module]
                )
            else:
                continue
            for module in modules:
                parts = module.split(".")
                if parts[0] == "manutencao":
                    allowed = len(parts) > 1 and parts[1] in LAYERS[layer]
                else:
                    allowed = parts[0] in sys.stdlib_module_names | external
                assert allowed, f"{path}:{node.lineno}: forbidden import {module}"
