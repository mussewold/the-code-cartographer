import os
import logging
from typing import List

from tree_sitter_languages import get_language
try:
    from src.analyzers.tree_sitter_analyzer import LanguageRouter
except ImportError:
    LanguageRouter = None
from src.models import ModuleNode

logger = logging.getLogger(__name__)

class Surveyor:
    def __init__(self):
        self.router = LanguageRouter() if LanguageRouter else None

    def analyze_module(self, path: str, base_path: str = None) -> ModuleNode:
        """Analyzes a module to extract imports, classes, functions, loc, and complexity."""
        path = os.path.abspath(path)
        base_name = os.path.basename(path)
        
        if not os.path.exists(path):
            logger.error(f"File not found: {path}")
            return ModuleNode(id=path, name=base_name, filepath=path)

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        ext = os.path.splitext(path)[1].lower()
        tree = self.router.get_tree(content, ext) if self.router else None

        loc = len(content.splitlines())
        
        # Calculate base module name for relative import resolution
        try:
            rel_path = os.path.relpath(path, base_path or os.getcwd())
        except ValueError:
            rel_path = path
        base_module = os.path.splitext(rel_path)[0].replace(os.sep, '.')

        module_node = ModuleNode(
            id=path,
            name=base_module,
            filepath=path,
            loc=loc,
            complexity=1 # Base complexity is 1
        )

        if not tree:
            return module_node

        if ext == '.py':
            self._analyze_python(tree, content, module_node, base_module)
            
        return module_node

    def _resolve_import(self, base_module: str, relative_name: str) -> str:
        """Resolves relative import paths to absolute module paths."""
        if not relative_name.startswith('.'):
            return relative_name
            
        parts = base_module.split('.')
        pkg = parts[:-1] # Package of the current module
        
        dots = 0
        while dots < len(relative_name) and relative_name[dots] == '.':
            dots += 1
            
        levels_up = dots - 1
        
        if levels_up > len(pkg):
            resolved_pkg = []
        else:
            resolved_pkg = pkg[:len(pkg) - levels_up] if len(pkg) - levels_up > 0 else []
            
        remaining = relative_name[dots:]
        if remaining:
            resolved_pkg.append(remaining)
            
        return '.'.join(resolved_pkg)

    def _analyze_python(self, tree, content: str, module_node: ModuleNode, base_module: str):
        content_bytes = content.encode('utf-8')
        lang = get_language('python')
        
        # 1. Functions (filter private ones starting with _)
        func_query = lang.query("(function_definition name: (identifier) @func_name)")
        for node, tag in func_query.captures(tree.root_node):
            name = content_bytes[node.start_byte:node.end_byte].decode('utf-8')
            if not name.startswith('_'):
                module_node.functions.append(name)
        
        # 2. Classes and Base Classes
        class_def_query = lang.query("(class_definition) @class")
        for node, tag in class_def_query.captures(tree.root_node):
            class_name = ""
            bases = []
            for child in node.children:
                if child.type == 'identifier':
                    class_name = content_bytes[child.start_byte:child.end_byte].decode('utf-8')
                elif child.type == 'argument_list':
                    # Extract base classes
                    for arg in child.children:
                        if arg.type == 'identifier' or arg.type == 'attribute':
                            bases.append(content_bytes[arg.start_byte:arg.end_byte].decode('utf-8'))
            if class_name:
                module_node.classes.append({"name": class_name, "bases": bases})

        # 3. Imports
        import_query_str = """
            (import_statement (dotted_name) @import_name)
            (import_from_statement) @import_from
        """
        import_query = lang.query(import_query_str)
        
        for node, tag in import_query.captures(tree.root_node):
            if tag == 'import_name':
                name = content_bytes[node.start_byte:node.end_byte].decode('utf-8')
                module_node.imports.append(name)
            elif tag == 'import_from':
                raw_module_name = ""
                for child in node.children:
                    if child.type == 'import':
                        break
                    if child.type in ('relative_import', 'dotted_name'):
                        raw_module_name = content_bytes[child.start_byte:child.end_byte].decode('utf-8')
                        break
                        
                if raw_module_name:
                    resolved = self._resolve_import(base_module, raw_module_name)
                    if resolved and resolved not in module_node.imports:
                        module_node.imports.append(resolved)

        # 4. Complexity
        branch_query = lang.query("""
            (if_statement) @branch
            (for_statement) @branch
            (while_statement) @branch
            (match_statement) @branch
            (except_clause) @branch
            (with_statement) @branch
            (list_comprehension) @branch
            (dictionary_comprehension) @branch
        """)
        branches = len(branch_query.captures(tree.root_node))
        module_node.complexity += branches
