import sys
import os
import networkx as nx

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.graph.lineage_graph import DataLineageGraph

def test_analytics():
    g = nx.DiGraph()
    # Source -> Middle -> Sink
    g.add_edge("s3://raw-data", "task://loader")
    g.add_edge("task://loader", "db://staging_table")
    g.add_edge("db://staging_table", "task://transformer")
    g.add_edge("task://transformer", "db://final_table")
    g.add_edge("db://final_table", "task://exporter")
    g.add_edge("task://exporter", "s3://reports")
    
    # Another branch
    g.add_edge("db://looker_config", "task://exporter")
    
    dlg = DataLineageGraph(g)
    
    print("--- Testing find_sources ---")
    sources = dlg.find_sources()
    print(f"Sources: {sources}")
    assert "s3://raw-data" in sources
    assert "db://looker_config" in sources
    
    print("\n--- Testing find_sinks ---")
    sinks = dlg.find_sinks()
    print(f"Sinks: {sinks}")
    assert "s3://reports" in sinks
    
    print("\n--- Testing blast_radius ---")
    blast = dlg.blast_radius("db://staging_table")
    print(f"Blast radius of staging_table: {blast}")
    expected = {"task://transformer", "db://final_table", "task://exporter", "s3://reports"}
    assert expected.issubset(blast)
    
    print("\n--- All tests passed! ---")

if __name__ == "__main__":
    test_analytics()
