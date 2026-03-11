# 🗺️ The Code Cartographer

**The Code Cartographer** is a powerful static analysis tool designed to map data flow and lineage across complex, multi-language codebases. It specializes in bridging the gap between SQL (dbt, procedural), Python data scripts, and Airflow orchestration to give you a unified view of your data's journey.

## 🚀 Key Features

- **🔍 Unified Data Lineage**: Automatically extracts relationships between database tables, S3 buckets, local files, and Airflow tasks.
- **🛠️ Hybrid SQL Parsing**: Intelligent parsing that handles complex Jinja templates and dbt-specific macros (`ref`, `source`) alongside standard SQL lineage.
- **🐍 Python Dataflow Analysis**: Uses Tree-sitter to identify I/O operations (Pandas, Spark, etc.) and link them to your datasets.
- **🌬️ Airflow & dbt Integration**: Understands Airflow task dependencies (`>>`) and dbt schema definitions to build a complete topological map.
- **💥 Impact Analysis (Blast Radius)**: Quickly identify all downstream dependents of a dataset change to prevent breaking changes.
- **📊 Interactive Visualization**: Generate interactive HTML graphs (Pyvis) or hierarchical PNGs (Graphviz) to explore your architecture.

## 📦 Installation

Ensure you have [uv](https://github.com/astral-sh/uv) installed, then:

```bash
# Clone the repository
git clone https://github.com/mussewold/the-code-cartographer.git
cd the-code-cartographer

# Setup dependencies
uv sync
```

## 🛠️ Usage

### 1. Analyze a Codebase

Point the cartographer at a local directory or a GitHub URL.

```bash
uv run python src/cli.py analyze --path https://github.com/mitodl/ol-data-platform
```

### 2. High-Level Insights

Get a summary of your data entry points (Sources) and terminal outputs (Sinks).

```bash
uv run python src/cli.py lineage-summary
```

### 3. Impact Analysis (Blast Radius)

Find exactly what will be affected if you modify a specific table or task.

```bash
uv run python src/cli.py blast-radius "db://stg_orders"
```

### 4. Visualization

Explore the codebase visually.

```bash
# Interactive HTML Graph
uv run python src/cli.py visualize

# Hierarchical Lineage PNG
uv run python src/cli.py visualize-lineage
```

## 🏗️ Architecture

The Cartographer is built with a modular analyzer pattern orchestrated by the `DataLineageGraph`:

- **Modular Analyzers**: Separate logic for `SQL`, `Python`, and `DAG/Config` parsing located in `src/analyzers/`.
- **Centralized Graph**: The `DataLineageGraph` class Coordinates parsing and provides advanced graph analytics (Sources, Sinks, Descendants).
- **Extensible Pipeline**: The `Orchestrator` manages the end-to-end flow from Git cloning to final graph persistence.

## 🧪 Testing

Run the analytical verification suite:

```bash
uv run python tests/test_lineage_analytics.py
```

---

_Mapping the digital wilderness, one dataset at a time._
