import logging
from typing import List, Dict, Any

try:
    from tree_sitter_languages import get_language
except ImportError:
    get_language = None

logger = logging.getLogger(__name__)

class PythonDataFlowAnalyzer:
    def __init__(self):
        if get_language:
            self.lang = get_language('python')
        else:
            self.lang = None
            logger.error("tree_sitter_languages is not available")

    def parse_io_calls(self, tree, content: bytes) -> List[Dict[str, Any]]:
        """
        Parses a python tree-sitter AST to find data I/O calls:
        - read_csv, to_csv etc
        - read_sql, execute
        - spark read/write
        Extracts the first argument.
        """
        if not self.lang or not tree:
            return []

        results = []
        
        query_str = """
        (call
          function: [
            (identifier) @func_name
            (attribute attribute: (identifier) @func_name)
          ]
          arguments: (argument_list) @args
        )
        """
        try:
            query = self.lang.query(query_str)
        except Exception as e:
            logger.error(f"Failed to create query: {e}")
            return []

        target_io_methods = {
            'read_csv': 'READS',
            'to_csv': 'WRITES',
            'read_sql': 'READS',
            'read_sql_table': 'READS',
            'read_sql_query': 'READS',
            'execute': 'TRANSFORMS', 
            'saveAsTable': 'WRITES',
            'parquet': 'READS',
            'csv': 'READS',
            'json': 'READS',
            'table': 'READS',
        }

        captures = query.captures(tree.root_node)
        
        current_func_name = None
        for node, tag in captures:
            if tag == 'func_name':
                current_func_name = content[node.start_byte:node.end_byte].decode('utf-8')
            elif tag == 'args' and current_func_name:
                if current_func_name in target_io_methods:
                    action = target_io_methods[current_func_name]
                    
                    first_arg_node = None
                    for child in node.children:
                        if child.type not in ('(', ')', ','):
                            first_arg_node = child
                            break
                            
                    if first_arg_node:
                        if first_arg_node.type in ('string', 'string_literal'):
                            arg_text = content[first_arg_node.start_byte:first_arg_node.end_byte].decode('utf-8')
                            is_dynamic = False
                            for child in first_arg_node.children:
                                if child.type == 'interpolation':
                                    is_dynamic = True
                                    break
                                    
                            if is_dynamic:
                                dataset_name = '[DYNAMIC_REFERENCE]'
                            else:
                                dataset_name = arg_text.strip('\'"fbr')
                                if arg_text.startswith(('f"', "f'", 'F"', "F'")):
                                    dataset_name = arg_text[2:-1]
                                elif arg_text.startswith(('r"', "r'", 'b"', "b'")):
                                    dataset_name = arg_text[2:-1]
                                else:
                                    dataset_name = arg_text.strip('\'"')
                        elif first_arg_node.type == 'identifier':
                            dataset_name = '[DYNAMIC_REFERENCE]'
                        else:
                            dataset_name = '[DYNAMIC_REFERENCE]'
                            
                        call_node = node.parent
                        if call_node and call_node.type == 'call':
                            func_node = call_node.child_by_field_name('function')
                            if func_node:
                                full_func_text = content[func_node.start_byte:func_node.end_byte].decode('utf-8')
                                if '.write.' in full_func_text or full_func_text.startswith('write.'):
                                    action = 'WRITES'
                        
                        results.append({
                            'dataset': dataset_name,
                            'action': action,
                            'method': current_func_name
                        })
                current_func_name = None

        return results
