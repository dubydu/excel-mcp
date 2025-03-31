import pandas as pd
import time
import signal
import sys
import logging
from typing import Optional, Dict, Any, Literal
import os
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
import mcp.server.stdio
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """
The assistant's goal is to demonstrate the capabilities of the Excel/CSV MCP Server. This server allows interaction with Excel (xls/xlsx) and CSV files through various operations by using pandas (https://github.com/pandas-dev/pandas) and xlrd (https://github.com/python-excel/xlrd) libraries.

You have selected the MCP menu item (denoted by the paperclip icon) and chosen the 'excel-mcp' prompt.

This server provides tools to:
1. Query data from Excel/CSV files using pandas queries
2. Update existing records
3. Delete records
4. List columns
5. Handle both Excel (xls/xlsx) and CSV formats

Available tools and examples:

1. query: Execute pandas queries
   Example:
   ```
   Input: "query", {"query": "age > 30"}
   Output: Returns records where age is greater than 30
   ```

2. update_item: Update existing records
   Example:
   ```
   Input: "update_item", {
       "index": 1,
       "data": {"name": "Updated Name"}
   }
   Output: Updates the name of the record at index 1
   ```

3. delete_item: Delete records
   Example:
   ```
   Input: "delete_item", {"index": 1}
   Output: Deletes the record at index 1
   ```

Let's work with your file and perform some operations based on your needs.

<mcp>
Tools:
- Use query to search and filter data
- Use update_item to modify existing records
- Use delete_item to remove records

Resources:
- File content can be accessed and modified
- Changes are saved automatically
- Data integrity is maintained throughout operations
</mcp>

Would you like to:
1. Query existing data
2. Update records
3. Delete records

Please let me know your preferred operation and I'll guide you through the process.
"""

# File setup
FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "data/example.xls"))
ALLOWED_FORMATS = Literal["xls", "xlsx", "csv"]

def signal_handler(sig, frame):
    """Handle system signals to gracefully shut down the server."""
    print("Shutting down server...")
    sys.exit(0)

def setup_signal_handling():
    """Setup signal handling for graceful termination."""
    signal.signal(signal.SIGINT, signal_handler)

def validate_file(file_path: str) -> Optional[str]:
    """
    Validate file existence and format.
    Returns the file format if valid, None otherwise.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None
        
    file_ext = file_path.split('.')[-1].lower()
    if file_ext not in ["xls", "xlsx", "csv"]:
        logger.error(f"Unsupported file format: {file_ext}")
        return None
        
    return file_ext

def read_file(file_path: str) -> pd.DataFrame:
    """Read the file based on its format"""
    file_ext = file_path.split('.')[-1].lower()
    try:
        if file_ext in ["xls", "xlsx"]:
            return pd.read_excel(file_path)
        else:  # csv
            return pd.read_csv(file_path)
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        raise

def write_file(df: pd.DataFrame, file_path: str):
    """Write the DataFrame back to file based on format"""
    file_ext = file_path.split('.')[-1].lower()
    try:
        if file_ext in ["xls", "xlsx"]:
            df.to_excel(file_path, index=False)
        else:  # csv
            df.to_csv(file_path, index=False)
    except Exception as e:
        logger.error(f"Error writing file: {str(e)}")
        raise

# Initialize the Server
server = Server("excel-mcp")

@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """Handle prompt listing"""
    logger.debug("Handling list_prompts request")
    return [
        types.Prompt(
            name="excel-mcp",
            description="A prompt to work with Excel (xls/xlsx) and CSV files using the Excel/CSV MCP Server",
            arguments=[
                types.PromptArgument(
                    name="file_type",
                    description="Type of file to work with (xls, xlsx, or csv)",
                    required=True,
                    choices=["xls", "xlsx", "csv"]
                ),
                types.PromptArgument(
                    name="operation",
                    description="Operation to perform (query, update, delete, list)",
                    required=True,
                    choices=["query", "update_item", "delete_item", "list_columns"]
                ) 
            ],
        )
    ]

@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict[str, str] | None = None) -> types.GetPromptResult:
    """Handle prompt requests for Excel/CSV operations"""
    logger.debug(f"Handling get_prompt request for {name} with args {arguments}")
    
    if name != "excel-mcp":
        raise ValueError(f"Unknown prompt: {name}")
        
    if not arguments or "file_type" not in arguments:
        raise ValueError("Missing required argument: file_type")
        
    file_type = arguments["file_type"].lower()
    if file_type not in ["xls", "xlsx", "csv"]:
        raise ValueError("File type must be one of: xls, xlsx, csv")
    
    # Handle xlsx same as xls
    if file_type == "xlsx":
        file_type = "xls"
    
    return types.GetPromptResult(
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=PROMPT_TEMPLATE.strip()
                )
            )
        ]
    )

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="query",
            description="Execute a query on Excel/CSV files using pandas",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Pandas query to execute"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="update_item",
            description="Update a row in Excel/CSV file",
            inputSchema={
                "type": "object", 
                "properties": {
                    "index": {"type": "integer", "description": "Row index to update"},
                    "data": {"type": "object", "description": "Data to update with"},
                },
                "required": ["index", "data"],
            },
        ),
        types.Tool(
            name="delete_item", 
            description="Delete a row from Excel/CSV file",
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "Row index to delete"},
                    "id_column": {"type": "string", "description": "Optional ID column name", "default": "id"},
                },
                "required": ["index"],
            },
        ),
        types.Tool(
            name="list_columns",
            description="List all columns in Excel/CSV file",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, 
    arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests"""
    try:
        if not arguments:
            if not name == "list_columns":
                raise ValueError("Missing arguments")

        if name == "query":
            df = read_file(FILE_PATH)
            result = df.query(arguments["query"])
            return [types.TextContent(type="text", text=str(result.to_dict('records')))]

        elif name == "update_item":
            df = read_file(FILE_PATH)
            index = arguments["index"]
            data = arguments["data"]
            
            if index not in df.index:
                return [types.TextContent(type="text", text=f"Error: Index {index} not found")]
                
            for column, value in data.items():
                if column not in df.columns:
                    return [types.TextContent(type="text", text=f"Error: Column {column} not found")]
                df.loc[index, column] = value
                
            write_file(df, FILE_PATH)
            return [types.TextContent(type="text", text="Item updated successfully")]

        elif name == "delete_item":
            df = read_file(FILE_PATH)
            index = arguments["index"]
            id_column = arguments.get("id_column", "id")
            
            if df.empty:
                return [types.TextContent(type="text", text="Error: Empty file")]
            
            if id_column != "id":
                if id_column not in df.columns:
                    return [types.TextContent(type="text", text=f"Error: Column {id_column} not found")]
                if index not in df[id_column].values:
                    return [types.TextContent(type="text", text=f"Error: Index {index} not found")]
                df = df[df[id_column] != index]
            else:
                if index not in df.index:
                    return [types.TextContent(type="text", text=f"Error: Index {index} not found")]
                df = df.drop(index)
            
            write_file(df, FILE_PATH)
            return [types.TextContent(type="text", text="Item deleted successfully")]
        
        elif name == "list_columns":
            df = read_file(FILE_PATH)
            results = df.columns.to_list()
            return [types.TextContent(type="text", text=f"{results}")]
            
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Excel/CSV MCP Server')
    parser.add_argument(
        '--file-path',
        default="data/example.xls",
        help='Path to Excel/CSV file'
    )
    return parser.parse_args()

async def main():
    """Main entry point for the MCP server."""
    args = parse_arguments()
    
    global FILE_PATH
    FILE_PATH = os.path.abspath(args.file_path)
    
    if not validate_file(FILE_PATH):
        sys.exit(1)

    setup_signal_handling()
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running with stdio transport")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="excel-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    try:
        import asyncio
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Error: {e}")
        time.sleep(5)