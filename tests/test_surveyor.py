import os
import pytest
from src.agents.surveyor import Surveyor

@pytest.fixture
def surveyor():
    return Surveyor()

def test_surveyor_python_analysis(surveyor, tmp_path):
    # Create a dummy python file
    content = """
import os, sys
from ..utils import helper
from typing import List, Dict

class BaseTest:
    pass

class TestClass(BaseTest):
    def test_method(self):
        if True:
            pass
        for i in range(10):
            pass

def public_function():
    return [x for x in range(5)]

def _private_function():
    pass
    """
    
    # Let's create a structure like src/agents/dummy.py so relative imports can be resolved
    src_dir = tmp_path / "src"
    agents_dir = src_dir / "agents"
    agents_dir.mkdir(parents=True)
    
    dummy_file = agents_dir / "dummy.py"
    dummy_file.write_text(content)
    
    # Change cwd so rel_path calculation works as expected
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    try:
        module_node = surveyor.analyze_module(str(dummy_file))
        
        assert module_node is not None
        assert module_node.loc == 21, f"Expected 21, got {module_node.loc}"
        
        # Functions: should include test_method, public_function. Should NOT include _private_function
        assert "public_function" in module_node.functions
        assert "test_method" in module_node.functions
        assert "_private_function" not in module_node.functions
        
        # Classes: should include TestClass and BaseTest
        class_names = [c["name"] for c in module_node.classes]
        assert "BaseTest" in class_names
        assert "TestClass" in class_names
        
        test_class = next(c for c in module_node.classes if c["name"] == "TestClass")
        assert "BaseTest" in test_class["bases"]
        
        # Imports: expected os, sys, typing, and resolved src.utils (from ..utils)
        assert "os" in module_node.imports
        assert "sys" in module_node.imports
        assert "typing" in module_node.imports
        
        # from ..utils import helper
        # base_module is src.agents.dummy
        # ..utils means src.utils
        assert "src.utils" in module_node.imports
        
        # Complexity = 1 (base) + 1 (if) + 1 (for) + 1 (list comp) = 4
        assert module_node.complexity == 4, f"Expected 4, got {module_node.complexity}"
        
    finally:
        os.chdir(original_cwd)
