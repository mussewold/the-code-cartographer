import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import click
from rich.console import Console
from src.orchestrator import Orchestrator

console = Console()

@click.group()
def cli():
    """Brownfield Cartographer CLI"""
    pass

@cli.command()
@click.option('--path', required=True, help='Path to the local directory or GitHub URL to analyze.')
def analyze(path):
    """Analyzes a codebase and builds the module and lineage graphs."""
    console.print(f"[bold green]Starting analysis for path:[/bold green] {path}")
    
    if path.startswith("http://") or path.startswith("https://"):
        console.print("[cyan]Detecting GitHub URL. Cloning repository locally...[/cyan]")
        import tempfile
        import subprocess
        
        # Create a persistent temp directory for this repository to allow analysis
        repo_name = path.rstrip('/').split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
            
        target_dir = os.path.join(tempfile.gettempdir(), f"cartographer_{repo_name}")
        
        if not os.path.exists(target_dir):
            try:
                subprocess.run(['git', 'clone', '--depth', '1', path, target_dir], check=True, capture_output=True)
                console.print(f"[green]Successfully cloned to {target_dir}[/green]")
            except subprocess.CalledProcessError as e:
                console.print(f"[bold red]Failed to clone repository:[/bold red] {e.stderr.decode('utf-8')}")
                return
        else:
            console.print(f"[yellow]Using existing clone at {target_dir}[/yellow]")
            
        # Re-assign path to the local cloned directory
        path = target_dir
        
    orchestrator = Orchestrator()
    
    try:
        output_graph = orchestrator.run_pipeline(path)
        console.print(f"\n[bold green]Analysis Complete![/bold green]")
        console.print(f"Module Graph saved to: [bold blue]{output_graph}[/bold blue]")
    except Exception as e:
        console.print(f"[bold red]Pipeline failed:[/bold red] {e}")

@cli.command()
def visualize():
    """Generates an interactive HTML representation of the module graph using Pyvis."""
    import json
    import networkx as nx
    from pyvis.network import Network
    
    graph_path = ".cartography/module_graph.json"
    out_path = ".cartography/module_graph.html"
    
    if not os.path.exists(graph_path):
        console.print(f"[bold red]Graph not found at {graph_path}. Run 'analyze' first.[/bold red]")
        return
        
    console.print("[cyan]Loading graph data...[/cyan]")
    with open(graph_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    G = nx.node_link_graph(data)
    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()
    
    console.print(f"[cyan]Visualizing {num_nodes} nodes and {num_edges} edges...[/cyan]")
    
    # Initialize Pyvis network
    net = Network(height="1000px", width="100%", bgcolor="#222222", font_color="white", notebook=False, directed=True)
    
    # Prepare nodes for Pyvis (ensure label attribute is present)
    for node, attrs in G.nodes(data=True):
        # Pyvis uses 'label' for the text on the node and 'title' for the hover tooltip
        attrs['label'] = attrs.get('name', node)
        attrs['title'] = f"File: {attrs.get('filepath', 'Unknown')}\nLOC: {attrs.get('loc', 0)}\nComplexity: {attrs.get('complexity', 0)}"
        
        # Color nodes by complexity
        complexity = attrs.get('complexity', 0)
        if complexity > 20: core_color = "#ff4444" # Red for complex
        elif complexity > 10: core_color = "#ffbb33" # Orange
        else: core_color = "#00C851" # Green
        
        attrs['color'] = core_color
        
    # Configure for scale
    if num_nodes > 2000:
        console.print("[yellow]Large graph detected. Using high-performance static layout...[/yellow]")
        net.toggle_physics(False)
        for node in G.nodes():
            G.nodes[node]['size'] = 5
    else:
        # Standard interactive settings
        net.force_atlas_2based()
        net.show_buttons(filter_=['physics'])
    
    # Load from NetworkX
    net.from_nx(G)
    
    # Add search and modular UI
    net.set_options("""
    var options = {
      "nodes": {
        "borderWidth": 2,
        "borderWidthSelected": 4,
        "font": {
          "size": 16,
          "face": "tahoma",
          "color": "white"
        }
      },
      "edges": {
        "color": {
          "inherit": true
        },
        "smooth": {"type": "continuous"}
      },
      "interaction": {
        "hover": true,
        "navigationButtons": true,
        "keyboard": true,
        "multiselect": true
      }
    }
    """)
    
    net.save_graph(out_path)
    console.print(f"[bold green]Interactive visualization saved to:[/bold green] [bold blue]{out_path}[/bold blue]")

@cli.command()
def visualize_lineage():
    """Generates a hierarchical Top-to-Bottom PDF/PNG using Graphviz."""
    import json
    import networkx as nx
    from graphviz import Digraph
    
    graph_path = ".cartography/module_graph.json"
    out_path = ".cartography/lineage_hierarchy"
    
    if not os.path.exists(graph_path):
        console.print(f"[bold red]Graph not found at {graph_path}. Run 'analyze' first.[/bold red]")
        return
        
    console.print("[cyan]Loading graph data...[/cyan]")
    with open(graph_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    G = nx.node_link_graph(data)
    num_nodes = G.number_of_nodes()
    
    console.print(f"[cyan]Generating hierarchical layout for {num_nodes} nodes...[/cyan]")
    
    dot = Digraph(comment='Code Cartographer Hierarchical View')
    dot.attr(rankdir='TB', size='20,20', ratio='fill')
    dot.attr('node', shape='box', style='rounded,filled', fontname='Helvetica', fontsize='12')
    
    for node, attrs in G.nodes(data=True):
        complexity = attrs.get('complexity', 0)
        if complexity > 20: fill = "#ffcccc"
        elif complexity > 10: fill = "#fff4cc"
        else: fill = "#ccffcc"
        
        label = attrs.get('name', node)
        dot.node(node, label, fillcolor=fill)
        
    for u, v in G.edges():
        dot.edge(u, v)
        
    try:
        dot.render(out_path, format='png', cleanup=True)
        console.print(f"[bold green]Hierarchical visualization saved to:[/bold green] [bold blue]{out_path}.png[/bold blue]")
    except Exception as e:
        console.print(f"[bold red]Graphviz rendering failed:[/bold red] {e}")
        console.print("[yellow]Make sure 'graphviz' system package is installed (e.g., sudo apt install graphviz)[/yellow]")

@cli.command()
def lineage_summary():
    """Prints analytical insights about the data lineage graph."""
    import json
    import networkx as nx
    from src.graph.lineage_graph import DataLineageGraph
    
    graph_path = ".cartography/lineage_graph.json"
    if not os.path.exists(graph_path):
        console.print(f"[bold red]Lineage graph not found at {graph_path}. Run 'analyze' first.[/bold red]")
        return
        
    with open(graph_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    dlg = DataLineageGraph(nx.node_link_graph(data))
    
    sources = dlg.find_sources()
    sinks = dlg.find_sinks()
    
    console.print(f"\n[bold cyan]Data Lineage Insights[/bold cyan]")
    console.print(f"[bold]Total Nodes:[/bold] {dlg.graph.number_of_nodes()}")
    console.print(f"[bold]Total Edges:[/bold] {dlg.graph.number_of_edges()}")
    
    console.print(f"\n[bold green]Sources (Entry Points):[/bold green]")
    for s in sources[:20]:
        console.print(f" - {s}")
    if len(sources) > 20:
        console.print(f" ... and {len(sources) - 20} more.")
        
    console.print(f"\n[bold red]Sinks (Exit Points):[/bold red]")
    for s in sinks[:20]:
        console.print(f" - {s}")
    if len(sinks) > 20:
        console.print(f" ... and {len(sinks) - 20} more.")

@cli.command()
@click.argument('node')
def blast_radius(node):
    """Shows all downstream dependents of a specific node."""
    import json
    import networkx as nx
    from src.graph.lineage_graph import DataLineageGraph
    
    graph_path = ".cartography/lineage_graph.json"
    if not os.path.exists(graph_path):
        console.print(f"[bold red]Lineage graph not found at {graph_path}.[/bold red]")
        return
        
    with open(graph_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    dlg = DataLineageGraph(nx.node_link_graph(data))
    downstream = dlg.blast_radius(node)
    
    console.print(f"\n[bold yellow]Blast Radius for {node}:[/bold yellow]")
    if not downstream:
        console.print("No downstream dependents found.")
    else:
        for d in downstream:
            console.print(f" - {d}")
        console.print(f"\n[bold]Total Impacted Nodes:[/bold] {len(downstream)}")

@cli.command()
def query():
    """Interactive mode for querying the parsed codebase context."""
    console.print("[yellow]Query mode (Navigator Agent) is not yet implemented.[/yellow]")

if __name__ == '__main__':
    cli()
