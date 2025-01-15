#!/usr/bin/env python3
"""Core functionality module for codebase search and manipulation.

This module provides the main interfaces and utilities for searching and
analyzing codebases, including cursor tools and search capabilities.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List

from .tools.cursor_tools import CursorToolManager

async def execute_codebase_search(parameters: Dict) -> List[Dict]:
    """Execute codebase search using ripgrep.

    Args:
        parameters (Dict): Search parameters including query and target directories

    Returns:
        List[Dict]: Search results in JSON format
    """
    try:
        # Build the ripgrep command
        cmd = ["rg", "--json", parameters["query"]]

        # Add target directories if specified
        if "target_directories" in parameters:
            cmd.extend(parameters["target_directories"])

        # Run the search
        process = subprocess.run(cmd, capture_output=True, text=True)

        # Parse the results
        results = []
        for line in process.stdout.splitlines():
            try:
                data = json.loads(line)
                if data["type"] == "match":
                    results.append({
                        "file": data["data"]["path"]["text"],
                        "line": data["data"]["line_number"],
                        "content": data["data"]["lines"]["text"].strip()
                    })
            except json.JSONDecodeError:
                continue

        return results

    except Exception as e:
        print(f"Error searching codebase: {str(e)}")
        return []

async def execute_read_file(parameters: Dict) -> str:
    """Execute file read"""
    path = Path(parameters["relative_workspace_path"])
    if not path.exists():
        return ""

    try:
        with open(path, "r") as f:
            lines = f.readlines()

        start = parameters["start_line_one_indexed"] - 1
        end = parameters["end_line_one_indexed_inclusive"]

        if parameters["should_read_entire_file"]:
            return "".join(lines)
        else:
            return "".join(lines[start:end])
    except Exception as e:
        print(f"Error reading file: {str(e)}")
        return ""

async def execute_edit_file(parameters: Dict) -> bool:
    """Execute file edit"""
    path = Path(parameters["target_file"])
    if not path.exists():
        return False

    try:
        with open(path, "r") as f:
            content = f.read()

        # Apply the edit
        lines = content.split("\n")
        edit_lines = parameters["code_edit"].split("\n")

        # Find the edit location
        edit_start = None
        for i, line in enumerate(lines):
            if line.strip() in [l.strip() for l in edit_lines[:3]]:
                edit_start = i
                break

        if edit_start is not None:
            # Replace the lines
            lines[edit_start:edit_start + len(edit_lines)] = edit_lines

            # Write back to file
            with open(path, "w") as f:
                f.write("\n".join(lines))

            return True
        else:
            print("Could not find edit location")
            return False

    except Exception as e:
        print(f"Error editing file: {str(e)}")
        return False

async def execute_list_dir(parameters: Dict) -> List[Dict]:
    """Execute directory listing"""
    path = Path(parameters["relative_workspace_path"])
    if not path.exists():
        return []

    try:
        results = []
        for item in path.iterdir():
            results.append({
                "type": "directory" if item.is_dir() else "file",
                "path": str(item.relative_to(Path.cwd())),
                "name": item.name
            })
        return results
    except Exception as e:
        print(f"Error listing directory: {str(e)}")
        return []

def register_cursor_tools(manager: CursorToolManager):
    """Register all available Cursor tools"""

    # Get tool schemas from the system prompt
    tool_schemas = [
        {
            "name": "codebase_search",
            "description": "Find snippets of code from the codebase most relevant to the search query.",
            "parameters": {
                "properties": {
                    "query": {
                        "description": "The search query to find relevant code.",
                        "type": "string"
                    },
                    "target_directories": {
                        "description": "Glob patterns for directories to search over",
                        "items": {"type": "string"},
                        "type": "array"
                    },
                    "explanation": {
                        "description": "One sentence explanation as to why this tool is being used.",
                        "type": "string"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": {
                "properties": {
                    "relative_workspace_path": {
                        "description": "The path of the file to read, relative to the workspace root.",
                        "type": "string"
                    },
                    "start_line_one_indexed": {
                        "description": "The one-indexed line number to start reading from.",
                        "type": "integer"
                    },
                    "end_line_one_indexed_inclusive": {
                        "description": "The one-indexed line number to end reading at.",
                        "type": "integer"
                    },
                    "should_read_entire_file": {
                        "description": "Whether to read the entire file.",
                        "type": "boolean"
                    },
                    "explanation": {
                        "description": "One sentence explanation as to why this tool is being used.",
                        "type": "string"
                    }
                },
                "required": [
                    "relative_workspace_path",
                    "start_line_one_indexed",
                    "end_line_one_indexed_inclusive",
                    "should_read_entire_file"
                ]
            }
        },
        {
            "name": "edit_file",
            "description": "Edit a file in the workspace.",
            "parameters": {
                "properties": {
                    "target_file": {
                        "description": "The path to the file to edit.",
                        "type": "string"
                    },
                    "instructions": {
                        "description": "Instructions for the edit.",
                        "type": "string"
                    },
                    "code_edit": {
                        "description": "The code to insert or modify.",
                        "type": "string"
                    },
                    "blocking": {
                        "description": "Whether to block until the edit is complete.",
                        "type": "boolean"
                    }
                },
                "required": [
                    "target_file",
                    "instructions",
                    "code_edit",
                    "blocking"
                ]
            }
        },
        {
            "name": "list_dir",
            "description": "List the contents of a directory.",
            "parameters": {
                "properties": {
                    "relative_workspace_path": {
                        "description": "Path to list contents of.",
                        "type": "string"
                    },
                    "explanation": {
                        "description": "One sentence explanation as to why this tool is being used.",
                        "type": "string"
                    }
                },
                "required": ["relative_workspace_path"]
            }
        }
    ]
    # Register each tool with its implementation
    tool_implementations = {
        "codebase_search": execute_codebase_search,
        "read_file": execute_read_file,
        "edit_file": execute_edit_file,
        "list_dir": execute_list_dir
    }

    for schema in tool_schemas:
        manager.register_tool(schema, tool_implementations.get(schema["name"]))

    return manager

def create_tool_manager() -> CursorToolManager:
    """Create and initialize a tool manager"""
    manager = CursorToolManager()
    register_cursor_tools(manager)
    return manager

"""Tool Management System"""

from typing import Dict, List
from .tools.cursor_tools import CursorToolManager

class ToolManager:
    """Manages all available tools and their interactions"""

    def __init__(self):
        self.cursor_tools = CursorToolManager()
        self.tools = {}
        self._load_tools()

    def _load_tools(self):
        """Load all available tools"""
        # Add cursor tools
        self.tools.update(self.cursor_tools.tools)

    def get_tool(self, name: str):
        """Get a specific tool by name"""
        return self.tools.get(name)
