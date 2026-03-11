import os
import json
import logging
import networkx as nx
from typing import Dict, Any, List

from src.models import DatasetNode
from src.graph.lineage_graph import DataLineageGraph

try:
    from tree_sitter_languages import get_language
    import tree_sitter
except ImportError:
    get_language = None
    tree_sitter = None

logger = logging.getLogger(__name__)

class HydrologistAgent:
    def __init__(self, graph: nx.DiGraph = None):
        self.graph = graph if graph is not None else nx.DiGraph()
        self.lineage_graph = DataLineageGraph(self.graph)
        self.parsers = {}
        
    def _get_parser(self, lang_name: str):
        if not get_language or not tree_sitter:
            return None
        if lang_name not in self.parsers:
            try:
                lang = get_language(lang_name)
                try:
                    parser = tree_sitter.Parser()
                    parser.set_language(lang)
                except Exception:
                    parser = tree_sitter.Parser(lang)
                self.parsers[lang_name] = parser
            except Exception as e:
                logger.error(f"Error loading parser for {lang_name}: {e}")
                self.parsers[lang_name] = None
        return self.parsers[lang_name]

    def _normalize_urn(self, dataset: str) -> str:
        if dataset == "[DYNAMIC_REFERENCE]":
            return dataset
        if dataset.startswith("db://") or dataset.startswith("s3://") or dataset.startswith("file://") or dataset.startswith("task://"):
            return dataset
        if dataset.endswith(".csv") or dataset.endswith(".parquet") or dataset.endswith(".json"):
            return f"file://{dataset}"
        return f"db://{dataset}"

    def analyze(self):
        """
        Iterates over the existing ModuleNodes in the graph, extracts data dependencies,
        creates DatasetNodes, and adds READS, WRITES, and TRANSFORMS edges.
        """
        if not self.graph:
            return self.graph

        nodes_to_process = [(n, d) for n, d in self.graph.nodes(data=True) if 'filepath' in d]
        
        for node_id, data in nodes_to_process:
            filepath = data.get('filepath')
            if not filepath or not os.path.exists(filepath):
                continue
                
            ext = os.path.splitext(filepath)[1].lower()
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Error reading file {filepath}: {e}")
                continue
                
            dependencies = []
            dag_dependencies = []
            
            if ext == '.py':
                parser = self._get_parser('python')
                if parser:
                    code_bytes = content.encode('utf-8')
                    tree = parser.parse(code_bytes)
                    dependencies = self.lineage_graph.parse_python_io(tree, code_bytes)
                    dag_dependencies = self.lineage_graph.parse_airflow_dags(tree, code_bytes)
            elif ext == '.sql':
                dependencies = self.lineage_graph.parse_sql_lineage(content)
            elif ext in ('.yaml', '.yml'):
                if 'schema' in os.path.basename(filepath):
                    dependencies = self.lineage_graph.parse_dbt_schema(filepath)
                    
            for dep in dependencies:
                action = dep.get('action', 'READS')
                raw_dataset = dep.get('dataset')
                
                if not raw_dataset:
                    continue
                    
                urn = self._normalize_urn(raw_dataset)
                
                if not self.graph.has_node(urn):
                    dataset_node = DatasetNode(
                        id=urn,
                        name=raw_dataset,
                        type="file" if urn.startswith("file://") else "table",
                        source_file=filepath
                    )
                    self.graph.add_node(urn, **dataset_node.model_dump())
                
                if action == 'READS':
                    self.graph.add_edge(urn, node_id, type="READS")
                elif action == 'WRITES':
                    self.graph.add_edge(node_id, urn, type="WRITES")
                elif action == 'TRANSFORMS':
                    self.graph.add_edge(node_id, urn, type="TRANSFORMS")
                    
            for up, down in dag_dependencies:
                task_up = f"task://{up}"
                task_down = f"task://{down}"
                
                for t in (task_up, task_down):
                    if not self.graph.has_node(t):
                        dataset_node = DatasetNode(
                            id=t,
                            name=t.replace("task://", ""),
                            type="task",
                            source_file=filepath
                        )
                        self.graph.add_node(t, **dataset_node.model_dump())
                
                self.graph.add_edge(task_up, task_down, type="TRANSFORMS")
                
        return self.graph

    def run_and_save(self, input_graph_path: str, output_graph_path: str):
        """Utility to load graph, analyze, and save to output."""
        if not os.path.exists(input_graph_path):
            logger.error(f"Input graph {input_graph_path} does not exist.")
            return

        with open(input_graph_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.graph = nx.node_link_graph(data)
            
        
        self.analyze()
        
        # Ensure dir
        os.makedirs(os.path.dirname(output_graph_path), exist_ok=True)
        data = nx.node_link_data(self.graph)
        with open(output_graph_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def save_lineage_graph(self, output_path: str):
        """Saves a graph containing only DatasetNodes and their relationships."""
        lineage_graph = nx.DiGraph()
        
        # Add all nodes that are DatasetNodes
        for node, data in self.graph.nodes(data=True):
            if 'type' in data and data['type'] in ('table', 'file', 'topic', 'task', 'source', 'model'):
                lineage_graph.add_node(node, **data)
        
        # Add edges between these nodes or between them and modules
        # We want the full lineage, so we include edges connected to DatasetNodes
        for u, v, data in self.graph.edges(data=True):
            if lineage_graph.has_node(u) or lineage_graph.has_node(v):
                # Ensure the other end is also in the graph (could be a ModuleNode)
                if not lineage_graph.has_node(u):
                    lineage_graph.add_node(u, **self.graph.nodes[u])
                if not lineage_graph.has_node(v):
                    lineage_graph.add_node(v, **self.graph.nodes[v])
                lineage_graph.add_edge(u, v, **data)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        data = nx.node_link_data(lineage_graph)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
