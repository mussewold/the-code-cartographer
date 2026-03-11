import logging
import yaml
import os
from typing import List, Dict, Any, Tuple

try:
    from tree_sitter_languages import get_language
except ImportError:
    get_language = None

logger = logging.getLogger(__name__)

class DAGConfigAnalyzer:
    def __init__(self):
        if get_language:
            self.lang = get_language('python')
        else:
            self.lang = None
            logger.error("tree_sitter_languages is not available")

    def parse_airflow_dags(self, tree, content: bytes) -> List[Tuple[str, str]]:
        """
        Parses python code for Airflow DAGs, looking for the `>>` bitwise shift operator.
        """
        if not self.lang or not tree:
            return []
            
        results = []
        query_str = """
        (binary_operator
            left: (_) @left
            operator: ">>"
            right: (_) @right
        )
        """
        try:
            query = self.lang.query(query_str)
        except Exception as e:
            logger.error(f"Failed to create query: {e}")
            return []
            
        captures = query.captures(tree.root_node)
        nodes = {}
        for node, tag in captures:
            nodes[tag] = content[node.start_byte:node.end_byte].decode('utf-8')
            if len(nodes) == 2:
                results.append((nodes['left'].strip(), nodes['right'].strip()))
                nodes = {}
                
        return results

    def parse_dbt_schema(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Parses a dbt schema.yml file to extract models and sources.
        """
        if not os.path.exists(filepath):
            return []
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to parse dbt schema {filepath}: {e}")
            return []
            
        results = []
        if not data or not isinstance(data, dict):
            return results
            
        if 'sources' in data and isinstance(data['sources'], list):
            for source in data['sources']:
                source_name = source.get('name')
                tables = source.get('tables', [])
                if isinstance(tables, list):
                    for table in tables:
                        table_name = table.get('name')
                        if source_name and table_name:
                            results.append({
                                'type': 'source',
                                'dataset': f"db://{source_name}.{table_name}"
                            })
                    
        if 'models' in data and isinstance(data['models'], list):
            for model in data['models']:
                model_name = model.get('name')
                if model_name:
                    results.append({
                        'type': 'model',
                        'dataset': f"db://{model_name}"
                    })
                
        return results
