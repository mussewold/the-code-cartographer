import logging
import re
import sqlglot
from sqlglot import exp
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SQLLineageAnalyzer:
    def parse_sql(self, sql_content: str, dialect: str = "postgres") -> List[Dict[str, Any]]:
        """
        Parses SQL content to extract data dependencies (SELECT/JOIN/WITH) and build
        lineage graph interactions.
        Returns a list of dependencies.
        """
        results = []
        # Hybrid approach: First extract dbt refs/sources via regex
        dbt_refs = re.findall(r'\{\{\s*ref\([\'"]([^\'"]+)[\'"]\)\s*\}\}', sql_content)
        for ref in dbt_refs:
            results.append({'action': 'READS', 'dataset': ref})
            
        dbt_sources = re.findall(r'\{\{\s*source\([\'"]([^\'"]+)[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\)\s*\}\}', sql_content)
        for src, table in dbt_sources:
            results.append({'action': 'READS', 'dataset': f"{src}_{table}"})

        # Now clean up for sqlglot
        cleaned_sql = sql_content
        cleaned_sql = re.sub(r'\{%.*?%\}', ' ', cleaned_sql, flags=re.DOTALL)
        cleaned_sql = re.sub(r'\{\{.*?\}\}', ' JINJA_VAR ', cleaned_sql, flags=re.DOTALL)
        
        # Handle placeholders and brackets
        cleaned_sql = re.sub(r'%s', '1', cleaned_sql)
        cleaned_sql = re.sub(r':[a-zA-Z_0-9]+', '1', cleaned_sql)
        cleaned_sql = re.sub(r'\?', '1', cleaned_sql)
        cleaned_sql = re.sub(r'\[([a-zA-Z_0-9 -]+)\]', r'"\1"', cleaned_sql)
        
        if not cleaned_sql.strip():
            return results
            
        parsed_queries = []
        dialects_to_try = [dialect, "duckdb", "snowflake", "bigquery", "mysql", "tsql", "sqlite"]
        success = False
        
        for d in dialects_to_try:
            try:
                parsed_queries = sqlglot.parse(cleaned_sql, read=d)
                success = True
                break
            except Exception:
                continue
                
        if not success:
            if "select" in cleaned_sql.lower() or "insert" in cleaned_sql.lower() or "update" in cleaned_sql.lower():
                snippet = cleaned_sql[:200].replace('\n', ' ')
                logger.debug(f"sqlglot failed to parse but regex might have captured dbt refs. Snippet: {snippet}...")
            return results

        # If sqlglot succeeded, extract standard lineage
        for stmt in parsed_queries:
            if not stmt:
                continue
            writes_to = set()
            if isinstance(stmt, exp.Create) and hasattr(stmt, 'this') and isinstance(stmt.this, exp.Table):
                target_table = stmt.this.name
                if stmt.this.db:
                    target_table = f"{stmt.this.db}.{target_table}"
                writes_to.add(target_table)
            elif isinstance(stmt, exp.Insert) and hasattr(stmt, 'this') and isinstance(stmt.this, exp.Table):
                target_table = stmt.this.name
                if getattr(stmt.this, 'db', None):
                    target_table = f"{stmt.this.db}.{target_table}"
                writes_to.add(target_table)
            
            for target in writes_to:
                results.append({'action': 'WRITES', 'dataset': target})
                
            for table in stmt.find_all(exp.Table):
                table_name = table.name
                if getattr(table, 'db', None):
                    table_name = f"{table.db}.{table_name}"
                if table_name in writes_to:
                    continue
                ctes = getattr(stmt.args.get("with"), "expressions", []) if getattr(stmt.args, "get", None) else []
                is_cte = any(cte.alias == table.name for cte in ctes)
                if not is_cte and table_name and table_name != "JINJA_VAR":
                    results.append({'action': 'READS', 'dataset': table_name})

        return results
