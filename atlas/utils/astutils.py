import ast
import inspect
from typing import Union, List

import astunparse
import copy


def parse(code, wrap_module=False):
    return ast.parse(code) if wrap_module else ast.parse(code).body[0]


def parse_obj(obj):
    src = inspect.getsource(obj).strip()
    return parse(src)


def parse_file(fname: str) -> ast.Module:
    with open(fname, 'r') as f:
        return ast.parse(f.read().strip())


def to_source(node: ast.AST) -> str:
    return astunparse.unparse(node)


def copy_asts(asts: Union[ast.AST, List[ast.AST]]):
    if isinstance(asts, list):
        return [copy_asts(i) for i in asts]

    return copy.deepcopy(asts)


def attr_to_qual_name(node: ast.Attribute):
    accesses = [node.attr]
    while isinstance(node.value, ast.Attribute):
        node = node.value
        accesses.append(node.attr)

    accesses.append(node.value.id)
    return '.'.join(reversed(accesses))


def get_all_names(n: ast.AST) -> List[str]:
    return [node.id for node in ast.walk(n) if isinstance(node, ast.Name)]


def preorder_traversal(node: ast.AST):
    yield node
    for field, val in ast.iter_fields(node):
        if isinstance(val, list):
            for i in val:
                if i is not None:
                    yield from preorder_traversal(i)
        elif isinstance(val, ast.AST):
            yield from preorder_traversal(val)
