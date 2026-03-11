import tree_sitter
from tree_sitter_languages import get_language

python_lang = get_language('python')
parser = tree_sitter.Parser()
parser.set_language(python_lang)

code = b"""
import os, sys
from ..utils import helper
from src.models import ModuleNode
"""

tree = parser.parse(code)
q = python_lang.query("(import_statement) @imp (import_from_statement) @imp_from")
for node, tag in q.captures(tree.root_node):
    print(tag, node.type)
    for child in node.children:
        print("  ", child.type, repr(code[child.start_byte:child.end_byte]))

