import pandas as pd
import time
import signal
import sys
import logging
from typing import Optional, Dict, Any, Literal
import os
from mcp.server.fastmcp import FastMCP
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File setup
FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "db/example.xls"))
ALLOWED_FORMATS = Literal["xls", "xlsx", "csv"]

def signal_handler(sig, frame):
    """
    Handle system signals to gracefully shut down the server.
    """
    print("Shutting down server...")
    sys.exit(0)

def setup_signal_handling():
    """
    Setup signal handling for graceful termination.
    """
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
    """
    Read the file based on its format
    """
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
    """
    Write the DataFrame back to file based on format
    """
    file_ext = file_path.split('.')[-1].lower()
    try:
        if file_ext in ["xls", "xlsx"]:
            df.to_excel(file_path, index=False)
        else:  # csv
            df.to_csv(file_path, index=False)
    except Exception as e:
        logger.error(f"Error writing file: {str(e)}")
        raise

# Initialize the FastMCP server
mcp = FastMCP()

@mcp.tool(name="excel_query", description="Execute a query on Excel file (xls/xlsx)")
def excel_query(query: str) -> Dict[str, Any]:
    """
    Execute a pandas query on Excel file
    """
    try:
        df = read_file(FILE_PATH)
        result = df.query(query)
        return {"success": True, "results": result.to_dict('records')}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool(name="csv_query", description="Execute a query on CSV file")
def csv_query(query: str) -> Dict[str, Any]:
    """
    Execute a pandas query on CSV file
    """
    try:
        df = read_file(FILE_PATH)
        result = df.query(query)
        return {"success": True, "results": result.to_dict('records')}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool(name="update_item", description="Update a row in file")
def update_item(index: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a row in file by index"""
    try:
        df = read_file(FILE_PATH)
        
        # Check if index exists in DataFrame
        if index not in df.index:
            return {
                "success": False,
                "error": f"Index {index} not found in file"
            }
            
        for column, value in data.items():
            if column not in df.columns:
                return {
                    "success": False,
                    "error": f"Column {column} not found in file"
                }
            df.loc[index, column] = value
            
        write_file(df, FILE_PATH)
        return {"success": True, "message": "Item updated successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool(name="delete_item", description="Delete a row from file")
def delete_item(index: Any, id_column: str = "id") -> Dict[str, Any]:
    """
    Delete a row from file by index
    """
    try:
        df = read_file(FILE_PATH)
        
        # Check if file is empty
        if df.empty:
            return {
                "success": False,
                "error": "Empty file"
            }
        
        # If using custom index column
        if id_column != "id":
            if id_column not in df.columns:
                return {
                    "success": False,
                    "error": f"Column {id_column} not found"
                }
            if index not in df[id_column].values:
                return {
                    "success": False,
                    "error": f"Index {index} not found"
                }
            df = df[df[id_column] != index]
        else:
            # Using default index
            if index not in df.index:
                return {
                    "success": False,
                    "error": f"Index {index} not found"
                }
            df = df.drop(index)
        
        write_file(df, FILE_PATH)
        return {
            "success": True,
            "message": "Item deleted successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description='Excel/CSV MCP Server')
    parser.add_argument(
        '--file-path',
        default="./db/example.xls",
        help='Path to Excel/CSV file'
    )
    parser.add_argument(
        '--host',
        default="127.0.0.1",
        help='Host address to bind the server'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Port number to bind the server'
    )
    return parser.parse_args()

def main():
    """
    Main entry point for the MCP server.
    """
    args = parse_arguments()
    
    # Update FILE_PATH with command line argument
    global FILE_PATH
    FILE_PATH = os.path.abspath(args.file_path)
    
    print(f"File path: {FILE_PATH}")
    setup_signal_handling()
    
    if not validate_file(FILE_PATH):
        sys.exit(1)

    print(f"Starting MCP server for Excel/CSV on {args.host}:{args.port}")
    mcp.run()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error: {e}")
        # Sleep before exiting to give time for error logs
        time.sleep(5)