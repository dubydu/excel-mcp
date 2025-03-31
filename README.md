# Excel/CSV MCP Server

A Model Context Protocol (MCP) server for interacting with Excel (xls/xlsx) and CSV files.

## Features

- Query data using pandas queries
- Update existing records
- Delete records
- List columns
- Support for multiple file formats (xls, xlsx, csv)

## Setup

### Setting up a Virtual Environment

1. Create a virtual environment:
```bash
# On Windows
python -m venv venv

# On macOS/Linux
python -m venv .venv
```

2. Activate the virtual environment:
```bash
# On Windows
venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Start the server by running:

```bash
python src/server.py --file-path path/to/your/file.xls
```

### Available MCP Tools

1. **query** - Execute pandas queries on your data
   ```json
   {
       "query": "age > 30"
   }
   ```

2. **update_item** - Update existing records
   ```json
   {
       "index": 1,
       "data": {"name": "Updated Name"}
   }
   ```

3. **delete_item** - Delete records
   ```json
   {
       "index": 1,
       "id_column": "id"
   }
   ```

4. **list_columns** - List all columns in the file
   ```json
   {}
   ```

## Command Line Arguments

- `--file-path`: Path to the Excel/CSV file (default: "data/example.xls")

## MCP CLients Configuration

* 5ire
```json
{
  "name": "SQLite",
  "key": "sqlite",
  "command": "/absolute/path/to/excel-mcp/.venv/bin/python",
  "args": [
    "/absolute/path/to/excel-mcp/src/server.py",
    "--db-path",
    "/path/to/database.db"
  ]
}
```

* Claude Desktop
```json
{
  "mcpServers": {
    "sqlite-mcp": {
      "command": "/absolute/path/to/excel-mcp/.venv/bin/python",
      "args": [
        "/absolute/path/to/excel-mcp/src/server.py",
         "--db-path",
         "/path/to/database.db"
      ]
    }
  }
}
```

## Prerequisites

- Python 3.x
- pandas
- xlrd (for xls files)
- openpyxl (for xlsx files)
- mcp-python