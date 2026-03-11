import logging
from typing import Optional

try:
    import tree_sitter
    from tree_sitter_languages import get_language
except ImportError:
    tree_sitter = None
    get_language = None

logger = logging.getLogger(__name__)

class LanguageRouter:
    """Selects the correct tree-sitter grammar based on file extensions."""
    
    # Map file extensions to tree-sitter language names
    EXTENSION_MAP = {
        '.py': 'python',
        '.sql': 'sql',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.ts': 'typescript',
        '.js': 'javascript',
    }
    
    def __init__(self):
        self._parsers = {}
        
    def get_tree(self, file_content: str | bytes, extension: str) -> Optional["tree_sitter.Tree"]:
        """Returns a parsed tree_sitter.Tree object based on the given file extension."""
        if tree_sitter is None or get_language is None:
            logger.error("tree_sitter or tree_sitter_languages is not installed.")
            return None

        # Normalize extension
        ext = extension.lower()
        if not ext.startswith('.'):
            ext = f".{ext}"
            
        lang_name = self.EXTENSION_MAP.get(ext)
        
        if not lang_name:
            logger.warning(f"UnsupportedLanguage: No parser available for extension '{extension}'")
            return None
            
        try:
            if lang_name not in self._parsers:
                lang = get_language(lang_name)
                try:
                    parser = tree_sitter.Parser()
                    parser.set_language(lang)
                except Exception:
                    # tree-sitter >= 0.22
                    parser = tree_sitter.Parser(lang)
                self._parsers[lang_name] = parser
            
            parser = self._parsers[lang_name]
            
            # tree_sitter parsing requires bytes
            content_bytes = file_content.encode('utf-8') if isinstance(file_content, str) else file_content
            
            tree = parser.parse(content_bytes)
            return tree
            
        except Exception as e:
            logger.error(f"Error parsing file with extension {extension}: {e}")
            return None
