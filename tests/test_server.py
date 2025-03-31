import pytest
import pandas as pd
import os
import sys
import json
from unittest.mock import patch, Mock, AsyncMock
import asyncio

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.server import (
    validate_file,
    read_file,
    write_file,
    handle_call_tool,
    handle_list_tools,
    handle_get_prompt,
    handle_list_prompts,
)

# Sample test data
SAMPLE_DATA = pd.DataFrame({
    'id': [1, 2, 3],
    'name': ['John', 'Jane', 'Bob'],
    'age': [25, 30, 35]
})

@pytest.fixture
def sample_excel_file(tmp_path):
    """Create a temporary Excel file for testing"""
    file_path = tmp_path / "test.xlsx"
    SAMPLE_DATA.to_excel(file_path, index=False)
    return str(file_path)

@pytest.fixture
def sample_csv_file(tmp_path):
    """Create a temporary CSV file for testing"""
    file_path = tmp_path / "test.csv"
    SAMPLE_DATA.to_csv(file_path, index=False)
    return str(file_path)

class TestFileValidation:
    def test_validate_file_excel(self, sample_excel_file):
        result = validate_file(sample_excel_file)
        assert result == "xlsx"

    def test_validate_file_csv(self, sample_csv_file):
        result = validate_file(sample_csv_file)
        assert result == "csv"

    def test_validate_file_nonexistent(self):
        result = validate_file("nonexistent.xlsx")
        assert result is None

    def test_validate_file_invalid_format(self, tmp_path):
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_text("test")
        result = validate_file(str(invalid_file))
        assert result is None

class TestFileOperations:
    def test_read_excel_file(self, sample_excel_file):
        df = read_file(sample_excel_file)
        pd.testing.assert_frame_equal(df, SAMPLE_DATA)

    def test_read_csv_file(self, sample_csv_file):
        df = read_file(sample_csv_file)
        pd.testing.assert_frame_equal(df, SAMPLE_DATA)

    def test_write_excel_file(self, tmp_path):
        file_path = str(tmp_path / "output.xlsx")
        write_file(SAMPLE_DATA, file_path)
        result_df = pd.read_excel(file_path)
        pd.testing.assert_frame_equal(result_df, SAMPLE_DATA)

    def test_write_csv_file(self, tmp_path):
        file_path = str(tmp_path / "output.csv")
        write_file(SAMPLE_DATA, file_path)
        result_df = pd.read_csv(file_path)
        pd.testing.assert_frame_equal(result_df, SAMPLE_DATA)

@pytest.mark.asyncio
class TestServerHandlers:
    # async def test_list_resources(self):
    #     resources = await handle_list_resources()
    #     assert len(resources) == 1
    #     assert resources[0].name == "Current Excel/CSV File"
    #     assert resources[0].uri.scheme == "file"

    async def test_list_prompts(self):
        prompts = await handle_list_prompts()
        assert len(prompts) == 1
        assert prompts[0].name == "excel-mcp"
        assert len(prompts[0].arguments) == 2

    async def test_get_prompt_valid(self):
        args = {
            "file_type": "xlsx",
            "operation": "query"
        }
        result = await handle_get_prompt("excel-mcp", args)
        assert isinstance(result.messages[0].content.text, str)
        assert len(result.messages) == 1

    async def test_get_prompt_invalid_name(self):
        with pytest.raises(ValueError, match="Unknown prompt"):
            await handle_get_prompt("invalid-prompt", {})

    async def test_get_prompt_missing_args(self):
        with pytest.raises(ValueError, match="Missing required argument"):
            await handle_get_prompt("excel-mcp", {})

    async def test_list_tools(self):
        tools = await handle_list_tools()
        assert len(tools) == 3
        tool_names = {tool.name for tool in tools}
        assert tool_names == {"query", "update_item", "delete_item"}

@pytest.mark.asyncio
class TestToolHandlers:
    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    async def test_query_tool(self, mock_read, mock_file_path, sample_excel_file):
        mock_file_path.return_value = sample_excel_file
        mock_read.return_value = SAMPLE_DATA

        result = await handle_call_tool("query", {"query": "age > 30"})
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Bob" in result[0].text

    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    @patch('src.server.write_file')
    async def test_update_item_tool(self, mock_write, mock_read, mock_file_path, sample_excel_file):
        mock_file_path.return_value = sample_excel_file
        mock_read.return_value = SAMPLE_DATA.copy()

        result = await handle_call_tool("update_item", {
            "index": 1,
            "data": {"name": "Updated Name"}
        })
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"
        assert "successfully" in result[0].text
        assert mock_write.called

    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    @patch('src.server.write_file')
    async def test_delete_item_tool(self, mock_write, mock_read, mock_file_path, sample_excel_file):
        mock_file_path.return_value = sample_excel_file
        mock_read.return_value = SAMPLE_DATA.copy()

        result = await handle_call_tool("delete_item", {
            "name": "John"
        })
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].type == "text"
        assert "successfully" in result[0].text
        assert mock_write.called

    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    @patch('src.server.write_file')
    async def test_list_columns(self, mock_write, mock_read, mock_file_path, sample_excel_file):
        mock_file_path.return_value = sample_excel_file
        mock_read.return_value = SAMPLE_DATA.copy()

        result = await handle_call_tool("list_columns", {})
        print(result[0].text)

    async def test_invalid_tool(self):
        result = await handle_call_tool("invalid_tool", {
            "index": 1
        })
        assert isinstance(result, list)
        assert len(result) == 1
        assert "Unknown tool" in result[0].text

    async def test_missing_arguments(self):
        result = await handle_call_tool("query", None)
        assert isinstance(result, list)
        assert len(result) == 1
        assert "Missing arguments" in result[0].text