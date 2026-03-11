# 🗺️ The Code Cartographer

**The Code Cartographer** is a static analysis tool that maps **data
lineage and data flow** across complex multi-language data platforms. It
bridges the gap between **SQL pipelines, Python data scripts, and
Airflow orchestration**, producing a unified knowledge graph of your
data ecosystem.

This tool helps data engineers and platform teams **understand
dependencies, analyze impact, and visualize data pipelines** across
their codebases.

---

# 🚀 Key Features

## 🔍 Unified Data Lineage

Automatically extracts relationships between:

- Database tables
- S3 buckets
- Local files
- Airflow tasks
- Python data pipelines

All dependencies are combined into a **single lineage graph**.

---

## 🛠 Hybrid SQL Parsing

Handles complex SQL environments including:

- dbt models
- Jinja templating
- dbt macros such as `ref()` and `source()`

It also supports traditional SQL lineage extraction.

---

## 🐍 Python Dataflow Analysis

Uses **Tree-sitter AST parsing** to analyze Python scripts and detect:

- Pandas reads/writes
- Spark operations
- File IO
- Database interactions

This allows the system to link Python transformations to datasets.

---

## 🌬 Airflow & dbt Awareness

Understands orchestration structures such as:

- Airflow DAG task dependencies (`>>`)
- dbt model relationships
- Configuration-driven pipelines

This enables building a **complete topological representation of the
pipeline architecture**.

---

## 💥 Impact Analysis (Blast Radius)

Determine downstream impact of modifying any dataset or task.

Example:

If table A changes → what breaks?

The Cartographer identifies all **dependent nodes in the lineage
graph**.

---

## 📊 Interactive Visualization

Generate visual representations of your data platform:

- Interactive HTML Graphs (Pyvis)
- Hierarchical Lineage Graphs (Graphviz)

These help engineers explore the system visually.

---

# 📦 Installation

This project uses **uv** for dependency management.

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

or

```bash
pip install uv
```

### Clone the Repository

```bash
git clone https://github.com/mussewold/the-code-cartographer.git
cd the-code-cartographer
```

### Install Dependencies

```bash
uv sync
```

---

# 🛠 Usage

## Analyze a Codebase

```bash
uv run python src/cli.py analyze --path https://github.com/mitodl/ol-data-platform
```

or

```bash
uv run python src/cli.py analyze --path ./my-data-repo
```

---

## Lineage Summary

```bash
uv run python src/cli.py lineage-summary
```

Outputs:

- Source datasets
- Terminal datasets
- Pipeline overview

---

## Blast Radius Analysis

```bash
uv run python src/cli.py blast-radius "db://stg_orders"
```

Returns **all downstream dependencies**.

---

# 📊 Visualization

## Interactive Graph

```bash
uv run python src/cli.py visualize
```

## Hierarchical Graph

```bash
uv run python src/cli.py visualize-lineage
```

---

# 🏗 Architecture

Core modules:

- **Orchestrator** → Controls analysis workflow
- **Analyzers** → SQL, Python, DAG parsing
- **Agents** → Higher-level reasoning modules
- **Graph Engine** → Stores lineage relationships
- **Models** → Node definitions

Directory overview:

    the-code-cartographer/
    ├── README.md
    ├── pyproject.toml
    ├── query_test.py
    ├── RECONNAISSANCE.md
    ├── test_python_dataflow.py
    ├── src/
    │   ├── cli.py
    │   ├── orchestrator.py
    │   ├── agents/
    │   │   ├── archivist.py
    │   │   ├── hydrologist.py
    │   │   ├── navigator.py
    │   │   ├── semanticist.py
    │   │   └── surveyor.py
    │   ├── analyzers/
    │   │   ├── dag_config_parser.py
    │   │   ├── python_dataflow.py
    │   │   ├── sql_lineage.py
    │   │   └── tree_sitter_analyzer.py
    │   ├── graph/
    │   │   ├── knowledge_graph.py
    │   │   └── lineage_graph.py
    │   └── models/
    │       ├── __init__.py
    │       └── nodes.py
    ├── tests/
    │   ├── test_hydrologist.py
    │   ├── test_knowledge_graph.py
    │   ├── test_language_router.py
    │   ├── test_lineage_analytics.py
    │   └── test_surveyor.py
    └── .cartography/
        ├── cartography_trace.jsonl
        ├── CODEBASE.md
        └── onboarding_brief.md

---

# 🧪 Testing

Run tests:

```bash
uv run pytest
```

---

# 🎯 Use Cases

- Data platform documentation
- Pipeline dependency discovery
- Impact analysis before schema changes
- Debugging broken pipelines
- Data governance
- Onboarding new engineers

---

# 🔮 Future Improvements

Planned enhancements:

- Spark DAG extraction
- Snowflake / BigQuery metadata integration
- OpenLineage compatibility
- Incremental graph updates
- Web UI for lineage exploration

---

# 📜 License

MIT License
