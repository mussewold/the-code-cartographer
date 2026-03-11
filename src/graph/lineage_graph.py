import logging
import networkx as nx
from typing import List, Dict, Any, Tuple, Set, Optional

from src.analyzers.python_dataflow import PythonDataFlowAnalyzer
from src.analyzers.sql_lineage import SQLLineageAnalyzer
from src.analyzers.dag_config_parser import DAGConfigAnalyzer

logger = logging.getLogger(__name__)

class DataLineageGraph:
    def __init__(self, graph: Optional[nx.DiGraph] = None):
        self.graph = graph if graph is not None else nx.DiGraph()
        self.python_analyzer = PythonDataFlowAnalyzer()
        self.sql_analyzer = SQLLineageAnalyzer()
        self.dag_analyzer = DAGConfigAnalyzer()

    # --- Orchestration Delegation ---

    def parse_python_io(self, tree, content: bytes) -> List[Dict[str, Any]]:
        return self.python_analyzer.parse_io_calls(tree, content)

    def parse_sql_lineage(self, sql_content: str, dialect: str = "postgres") -> List[Dict[str, Any]]:
        return self.sql_analyzer.parse_sql(sql_content, dialect)

    def parse_airflow_dags(self, tree, content: bytes) -> List[Tuple[str, str]]:
        return self.dag_analyzer.parse_airflow_dags(tree, content)

    def parse_dbt_schema(self, filepath: str) -> List[Dict[str, Any]]:
        return self.dag_analyzer.parse_dbt_schema(filepath)

    # --- Analytics ---

    def blast_radius(self, node: str) -> Set[str]:
        """Find all downstream dependents (BFS/DFS)"""
        if not self.graph.has_node(node):
            return set()
        return set(nx.descendants(self.graph, node))

    def find_sources(self) -> List[str]:
        """Nodes with in-degree=0"""
        return [n for n, d in self.graph.in_degree() if d == 0]

    def find_sinks(self) -> List[str]:
        """Nodes with out-degree=0"""
        return [n for n, d in self.graph.out_degree() if d == 0]
