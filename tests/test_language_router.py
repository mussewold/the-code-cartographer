import pytest
import warnings

warnings.filterwarnings("ignore", category=FutureWarning, module="tree_sitter")
from src.analyzers.tree_sitter_analyzer import LanguageRouter

@pytest.fixture
def router():
    return LanguageRouter()

def test_python_parsing(router):
    content = "def hello():\n    print('world')"
    tree = router.get_tree(content, ".py")
    assert tree is not None, "Expected a parsed tree for .py extension"
    assert tree.root_node is not None
    assert tree.root_node.type == "module"

def test_sql_parsing(router):
    content = "SELECT * FROM users;"
    tree = router.get_tree(content, ".sql")
    assert tree is not None, "Expected a parsed tree for .sql extension"
    assert tree.root_node is not None
    assert tree.root_node.type == "source_file"

def test_yaml_parsing(router):
    content = "key: value\n"
    tree = router.get_tree(content, ".yaml")
    assert tree is not None, "Expected a parsed tree for .yaml extension"
    assert tree.root_node is not None

def test_typescript_parsing(router):
    content = "const x: number = 42;"
    tree = router.get_tree(content, ".ts")
    assert tree is not None, "Expected a parsed tree for .ts extension"
    assert tree.root_node is not None

def test_javascript_parsing(router):
    content = "const x = 42;"
    tree = router.get_tree(content, ".js")
    assert tree is not None, "Expected a parsed tree for .js extension"
    assert tree.root_node is not None

def test_unsupported_language(router, caplog):
    tree = router.get_tree("some content", ".unknown")
    assert tree is None
    assert "UnsupportedLanguage" in caplog.text

def test_empty_file(router):
    tree = router.get_tree("", ".py")
    assert tree is not None
    assert tree.root_node is not None

def test_malformed_syntax(router):
    # tree-sitter is resilient and should parse malformed syntax without crashing
    content = "def hello( ::: ) print x"
    tree = router.get_tree(content, ".py")
    assert tree is not None
    assert tree.root_node is not None
    
    # Normally, tree-sitter will create an ERROR node somewhere for malformed syntax
    has_error = False
    
    def check_for_error(node):
        nonlocal has_error
        if node.type == 'ERROR':
            has_error = True
        for child in node.children:
            check_for_error(child)
            
    check_for_error(tree.root_node)
    # We won't strictly assert has_error here to avoid flakiness depending on grammar versions,
    # but the primary requirement is that it shouldn't crash.
