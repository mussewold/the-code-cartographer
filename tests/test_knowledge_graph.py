import pytest
import os
import json
import networkx as nx
from src.graph.knowledge_graph import KnowledgeGraph
from src.models.nodes import ModuleNode

@pytest.fixture
def graph():
    return KnowledgeGraph()

def test_add_module(graph):
    node = ModuleNode(
        id="test_id",
        name="test_name",
        filepath="/tmp/test.py",
        imports=["os", "sys"]
    )
    graph.add_module(node)
    
    assert "test_name" in graph.graph.nodes
    out_edges = list(graph.graph.out_edges("test_name"))
    assert len(out_edges) == 2
    assert ("test_name", "os") in out_edges
    assert ("test_name", "sys") in out_edges

def test_save_module_graph_calculates_metrics(graph, tmp_path):
    # A imports B, B imports C, C imports A (Circular dependency SCC)
    # D is standalone (imports A)
    
    node_a = ModuleNode(id="A", name="A", filepath="/A.py", imports=["B"])
    node_b = ModuleNode(id="B", name="B", filepath="/B.py", imports=["C"])
    node_c = ModuleNode(id="C", name="C", filepath="/C.py", imports=["A"])
    node_d = ModuleNode(id="D", name="D", filepath="/D.py", imports=["A"])

    for node in [node_a, node_b, node_c, node_d]:
        graph.add_module(node)

    out_file = tmp_path / "module_graph.json"
    graph.save_module_graph(str(out_file))
    
    assert out_file.exists()
    
    with open(out_file, 'r') as f:
        data = json.load(f)
        
    assert "nodes" in data
    nodes_list = data["nodes"]
    
    # Check that pagerank and scc were calculated Let's find node A
    node_a_data = next(n for n in nodes_list if n["id"] == "A")
    assert "pagerank" in node_a_data
    assert "circular_dependency_group" in node_a_data
    
    # Ensure A, B, and C are in the SAME circular dependency group
    node_b_data = next(n for n in nodes_list if n["id"] == "B")
    node_c_data = next(n for n in nodes_list if n["id"] == "C")
    
    group_a = node_a_data["circular_dependency_group"]
    assert group_a == node_b_data["circular_dependency_group"]
    assert group_a == node_c_data["circular_dependency_group"]
    
    # D should not be in a circular dependency group
    node_d_data = next(n for n in nodes_list if n["id"] == "D")
    assert "circular_dependency_group" not in node_d_data
