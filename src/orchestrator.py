import os
from typing import List
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from src.agents.surveyor import Surveyor
from src.graph.knowledge_graph import KnowledgeGraph

class Orchestrator:
    def __init__(self):
        self.surveyor = Surveyor()
        self.knowledge_graph = KnowledgeGraph()

    def run_pipeline(self, target_path: str):
        """Sequentially invokes the Surveyor Agent to build the structural skeleton."""
        
        # 1. Discover files
        # Right now we'll just discover python files for the skeleton
        python_files: List[str] = []
        if os.path.isfile(target_path):
            if target_path.endswith('.py') or target_path.endswith('.sql'):
                python_files.append(target_path)
        else:
            for root, dirs, files in os.walk(target_path):
                # skip virtual envs and hidden dirs by modifying dirs in-place
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '.venv']
                
                for file in files:
                    if (file.endswith('.py') or file.endswith('.sql')) and not file.startswith('.'):
                        python_files.append(os.path.join(root, file))

        output_graph_path = os.path.join(".cartography", "module_graph.json")

        if not python_files:
            return output_graph_path

        # 2. Analyze modules and build graph with Rich progress feedback
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            analyze_task = progress.add_task("[cyan]Surveying modules...", total=len(python_files))
            
            for file_path in python_files:
                progress.update(analyze_task, description=f"[cyan]Surveying: {os.path.basename(file_path)}")
                
                # Run Surveyor agent
                module_node = self.surveyor.analyze_module(file_path, base_path=target_path)
                
                # Add to knowledge graph
                self.knowledge_graph.add_module(module_node)
                
                progress.advance(analyze_task)
                
        # 3. Save graph
        self.knowledge_graph.save_module_graph(output_graph_path)
        
        return output_graph_path
