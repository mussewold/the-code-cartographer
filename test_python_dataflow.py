import os
import sys
sys.path.insert(0, os.getcwd())

from src.analyzers.python_dataflow import PythonDataFlowAnalyzer
from tree_sitter_languages import get_language
from tree_sitter import Parser

code = """
import pandas as pd

df = pd.read_csv("data.csv")
df.to_csv(f"{prefix}_out.csv")
spark.read.parquet("s3://bucket/data")
df.write.parquet("s3://bucket/out")
db.execute("SELECT * FROM users")
"""

analyzer = PythonDataFlowAnalyzer()
parser = Parser()
parser.set_language(get_language('python'))
tree = parser.parse(code.encode('utf-8'))

results = analyzer.parse_io_calls(tree, code.encode('utf-8'))
for r in results:
    print(r)
