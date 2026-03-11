import networkx as nx
import json
import os
from typing import List
from src.models import ModuleNode

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_module(self, module: ModuleNode):
        self.graph.add_node(module.name, **module.model_dump())
        
        # Add edges for imports
        for imp in module.imports:
            self.graph.add_edge(module.name, imp, type="imports")

    def save_module_graph(self, path: str):
        if len(self.graph.nodes) > 0:
            # Calculate PageRank
            pagerank = nx.pagerank(self.graph)
            nx.set_node_attributes(self.graph, pagerank, "pagerank")
            
            # Calculate Strongly Connected Components (Circular Dependencies)
            scc = list(nx.strongly_connected_components(self.graph))
            scc_dict = {}
            for group_id, component in enumerate(scc):
                if len(component) > 1: # Only care about circular dependencies (groups > 1)
                    for node in component:
                        scc_dict[node] = group_id
            nx.set_node_attributes(self.graph, scc_dict, "circular_dependency_group")

        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Convert to dictionary for easy serialization
        data = nx.node_link_data(self.graph)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
