from pydantic import BaseModel, Field
from typing import List

class ModuleNode(BaseModel):
    id: str
    name: str
    filepath: str
    imports: List[str] = Field(default_factory=list)
    classes: List[dict] = Field(default_factory=list)
    functions: List[str] = Field(default_factory=list)
    loc: int = 0
    complexity: int = 0
    git_commits: int = 0
    is_high_velocity: bool = False

class DatasetNode(BaseModel):
    id: str
    name: str
    type: str  # e.g., table, file, topic
    source_file: str