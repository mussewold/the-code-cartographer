import os
import subprocess
import logging
import warnings
from typing import List, Dict, Any

warnings.filterwarnings("ignore", category=FutureWarning, module="tree_sitter")

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

    def extract_git_velocity(self, path: str, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """
        Parses git log output to compute change frequency per file.
        Retrieves the top 20% of files that contain 80% (or more) of all cumulative changes.
        Returns a mapping: filepath -> {"commits": int, "is_core": bool}
        """
        abs_target_path = os.path.abspath(path)
        repo_dir = abs_target_path if os.path.isdir(abs_target_path) else os.path.dirname(abs_target_path)
        
        if not os.path.exists(os.path.join(repo_dir, ".git")):
            # If not a git repo, go up until find .git or root
            curr_dir = repo_dir
            while curr_dir and curr_dir != "/":
                if os.path.exists(os.path.join(curr_dir, ".git")):
                    repo_dir = curr_dir
                    break
                curr_dir = os.path.dirname(curr_dir)

        if not os.path.exists(os.path.join(repo_dir, ".git")):
            logger.warning(f"No .git directory found for path: {path}")
            return {}

        cmd = [
            "git", "log", f"--since={days} days ago", "--name-only", "--pretty=format:"
        ]

        try:
            result = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e}")
            return {}

        # Parse output
        lines = result.stdout.strip().split("\n")
        file_counts = {}
        for line in lines:
            if not line:
                continue
            
            # git log returns relative path from git root
            abs_path = os.path.abspath(os.path.join(repo_dir, line))
            
            # Try to match to requested path structure
            if abs_target_path in abs_path or os.path.commonpath([abs_target_path, abs_path]) == abs_target_path:
               # Only count if the modified file is within the requested analysis path
               file_counts[abs_path] = file_counts.get(abs_path, 0) + 1

        if not file_counts:
            return {}

        # 80/20 Rule Implementation
        sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
        total_commits = sum(count for _, count in sorted_files)
        target_commits = total_commits * 0.8

        cumulative_commits = 0
        velocity_data = {}
        
        # Determine the core based on accumulating up to 80% of all changes
        for filepath, count in sorted_files:
            cumulative_commits += count
            is_core = cumulative_commits <= target_commits
            # Edge case buffer: include the file that crosses the 80% threshold
            if not is_core and cumulative_commits - count < target_commits:
                is_core = True
                
            velocity_data[filepath] = {
                "commits": count,
                "is_core": is_core
            }

        return velocity_data

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
