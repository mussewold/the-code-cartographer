import pytest
import networkx as nx
import os
import json
from src.agents.hydrologist import HydrologistAgent
from src.models import ModuleNode, DatasetNode

def test_normalize_urn():
    agent = HydrologistAgent()
    assert agent._normalize_urn("users") == "db://users"
    assert agent._normalize_urn("data.csv") == "file://data.csv"
    assert agent._normalize_urn("db://schema.table") == "db://schema.table"
    assert agent._normalize_urn("[DYNAMIC_REFERENCE]") == "[DYNAMIC_REFERENCE]"

def test_python_analyzer(tmp_path):
    # Create mock python file
    py_file = tmp_path / "mock.py"
    py_content = """
import pandas as pd
df = pd.read_csv("input.csv")
df.to_csv("output.csv")
spark.read.parquet("s3://bucket/data")
db.execute("SELECT * FROM users")
task1 >> task2
"""
    py_file.write_text(py_content)
    
    graph = nx.DiGraph()
    module = ModuleNode(id="mock.py", name="mock", filepath=str(py_file))
    graph.add_node("mock.py", **module.model_dump())
    
    agent = HydrologistAgent(graph)
    result_graph = agent.analyze()
    
    assert result_graph.has_node("file://input.csv")
    assert result_graph.has_node("file://output.csv")
    assert result_graph.has_node("s3://bucket/data")
    assert result_graph.has_node("task://task1")
    assert result_graph.has_node("task://task2")
    
    assert result_graph.has_edge("file://input.csv", "mock.py") # READS
    assert result_graph.has_edge("mock.py", "file://output.csv") # WRITES
    assert result_graph.has_edge("s3://bucket/data", "mock.py") # READS
    assert result_graph.has_edge("mock.py", "db://SELECT * FROM users") # TRANSFORMS (since execute uses the raw string as table name in simple parser, wait no execute parser might do that)
    assert result_graph.has_edge("task://task1", "task://task2") # TRANSFORMS

def test_sql_analyzer(tmp_path):
    sql_file = tmp_path / "mock.sql"
    sql_content = """
    CREATE TABLE db.target AS
    SELECT a.*, b.val
    FROM db.source_a a
    JOIN source_b b ON a.id = b.id
    """
    sql_file.write_text(sql_content)
    
    graph = nx.DiGraph()
    module = ModuleNode(id="mock.sql", name="mock_sql", filepath=str(sql_file))
    graph.add_node("mock.sql", **module.model_dump())
    
    agent = HydrologistAgent(graph)
    result_graph = agent.analyze()
    
    assert result_graph.has_node("db://db.target")
    assert result_graph.has_node("db://db.source_a")
    assert result_graph.has_node("db://source_b")
    
    assert result_graph.has_edge("mock.sql", "db://db.target") # WRITES
    assert result_graph.has_edge("db://db.source_a", "mock.sql") # READS
    assert result_graph.has_edge("db://source_b", "mock.sql") # READS

def test_yaml_analyzer(tmp_path):
    yaml_file = tmp_path / "schema.yml"
    yaml_content = """
sources:
  - name: internal
    tables:
      - name: users
models:
  - name: transformed_users
    """
    yaml_file.write_text(yaml_content)
    
    graph = nx.DiGraph()
    module = ModuleNode(id="schema.yml", name="schema", filepath=str(yaml_file))
    graph.add_node("schema.yml", **module.model_dump())
    
    agent = HydrologistAgent(graph)
    result_graph = agent.analyze()
    
    assert result_graph.has_node("db://internal.users")
    assert result_graph.has_node("db://transformed_users")
    
    assert result_graph.has_edge("db://internal.users", "schema.yml") # Default READS
    assert result_graph.has_edge("db://transformed_users", "schema.yml") # Default READS
