import pytest
import pandas as pd
import os
from unittest.mock import patch, Mock
import sys
import json

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.server import (
    validate_file,
    read_file,
    write_file,
    excel_query,
    csv_query,
    update_item,
    delete_item
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

class TestQueryOperations:
    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    def test_excel_query_success(self, mock_read, mock_file_path, sample_excel_file):
        mock_file_path.return_value = sample_excel_file
        mock_read.return_value = SAMPLE_DATA
        
        result = excel_query("age > 30")
        assert result["success"] is True
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "Bob"

    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    def test_csv_query_success(self, mock_read, mock_file_path, sample_csv_file):
        mock_file_path.return_value = sample_csv_file
        mock_read.return_value = SAMPLE_DATA
        
        result = csv_query("age < 30")
        assert result["success"] is True
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "John"

    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    def test_query_invalid_syntax(self, mock_read, mock_file_path):
        mock_read.return_value = SAMPLE_DATA
        
        result = excel_query("invalid query")
        assert result["success"] is False
        assert "error" in result

class TestUpdateOperations:
    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    @patch('src.server.write_file')
    def test_excel_update_item_success(self, mock_write, mock_read, mock_file_path, sample_excel_file):
        mock_file_path.return_value = sample_excel_file
        mock_read.return_value = SAMPLE_DATA.copy()

        update_data = {"name": "Updated Name"}
        result = update_item(1, update_data)
        
        assert result["success"] is True
        assert mock_write.called

        # Verify the update was called with correct data
        call_args = mock_write.call_args[0]
        updated_df = call_args[0]
        assert updated_df.loc[1, "name"] == "Updated Name"

    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    @patch('src.server.write_file')
    def test_csv_update_item_success(self, mock_write, mock_read, mock_file_path, sample_csv_file):
        mock_file_path.return_value = sample_csv_file
        mock_read.return_value = SAMPLE_DATA.copy()

        update_data = {"age": 40}
        result = update_item(2, update_data)
        
        assert result["success"] is True
        assert mock_write.called
        
        # Verify the update was called with correct data
        call_args = mock_write.call_args[0]
        updated_df = call_args[0]
        assert updated_df.loc[2, "age"] == 40

    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    def test_excel_update_item_invalid_index(self, mock_read, mock_file_path, sample_excel_file):
        mock_file_path.return_value = sample_excel_file
        mock_read.return_value = SAMPLE_DATA.copy()
        
        result = update_item(999, {"name": "Test"})
        assert result["success"] is False
        assert "error" in result

    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    def test_csv_update_item_invalid_column(self, mock_read, mock_file_path, sample_csv_file):
        mock_file_path.return_value = sample_csv_file
        mock_read.return_value = SAMPLE_DATA.copy()
        
        result = update_item(1, {"invalid_column": "Test"})
        assert result["success"] is False
        assert "error" in result

class TestDeleteOperations:
    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    @patch('src.server.write_file')
    def test_excel_delete_item_success(self, mock_write, mock_read, mock_file_path, sample_excel_file):
        mock_file_path.return_value = sample_excel_file
        mock_read.return_value = SAMPLE_DATA.copy()
        
        print(mock_read.return_value)
        
        # Execute
        result = delete_item(1)  # Delete second row
        
        # Verify
        assert result["success"] is True
        assert "Item deleted successfully" in result["message"]
        
        # Verify write_file was called with correct DataFrame
        mock_write.assert_called_once()
        call_args = mock_write.call_args[0]
        updated_df = call_args[0]

        print(updated_df)

        assert len(updated_df) == len(SAMPLE_DATA) - 1
        assert 1 not in updated_df.index.tolist()

    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    @patch('src.server.write_file')
    def test_csv_delete_item_success(self, mock_write, mock_read, mock_file_path, sample_csv_file):
        """Test successful deletion of an item from CSV file"""
        mock_file_path.return_value = sample_csv_file
        initial_df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['John', 'Jane', 'Bob']
        })
        mock_read.return_value = initial_df.copy()
        
        result = delete_item(0)  # Delete first row
        
        assert result["success"] is True
        mock_write.assert_called_once()
        call_args = mock_write.call_args[0]
        updated_df = call_args[0]
        assert len(updated_df) == len(initial_df) - 1
        assert 0 not in updated_df.index.tolist()

    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    @patch('src.server.write_file')
    def test_delete_item_invalid_index(self, mock_write, mock_read, mock_file_path):
        """Test deletion with invalid index"""
        mock_read.return_value = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['John', 'Jane', 'Bob']
        })
        
        result = delete_item(999)  # Non-existent index
        
        assert result["success"] is False
        assert "error" in result
        assert "Index 999 not found" in result["error"]
        mock_write.assert_not_called()

    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    @patch('src.server.write_file')
    def test_delete_item_empty_file(self, mock_write, mock_read, mock_file_path):
        """Test deletion from empty file"""
        mock_read.return_value = pd.DataFrame()
        
        result = delete_item(0)
        
        assert result["success"] is False
        assert "error" in result
        assert "Empty file" in result["error"]
        mock_write.assert_not_called()

    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    @patch('src.server.write_file')
    def test_delete_last_item(self, mock_write, mock_read, mock_file_path):
        """Test deleting the last remaining item"""
        initial_df = pd.DataFrame({
            'id': [1],
            'name': ['John']
        }, index=[0])
        mock_read.return_value = initial_df.copy()
        
        result = delete_item(0)
        
        assert result["success"] is True
        mock_write.assert_called_once()
        call_args = mock_write.call_args[0]
        updated_df = call_args[0]
        assert len(updated_df) == 0

    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    def test_delete_item_file_error(self, mock_read, mock_file_path):
        """Test deletion when file operations fail"""
        mock_read.side_effect = Exception("File access error")
        
        result = delete_item(0)
        
        assert result["success"] is False
        assert "error" in result
        assert "File access error" in result["error"]

    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    @patch('src.server.write_file')
    def test_delete_multiple_items_sequential(self, mock_write, mock_read, mock_file_path):
        """Test deleting multiple items sequentially"""
        initial_df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['John', 'Jane', 'Bob']
        })
        mock_read.return_value = initial_df.copy()
        
        # Delete first item
        result1 = delete_item(0)
        assert result1["success"] is True
        
        # Update mock to return modified DataFrame
        mock_read.return_value = initial_df.drop(0)
        
        # Delete second item
        result2 = delete_item(1)
        assert result2["success"] is True
        
        # Verify final state
        assert mock_write.call_count == 2
        final_df = mock_write.call_args[0][0]
        assert len(final_df) == 1

    @patch('src.server.FILE_PATH')
    @patch('src.server.read_file')
    @patch('src.server.write_file')
    def test_delete_with_custom_index(self, mock_write, mock_read, mock_file_path):
        """Test deletion with custom index column"""
        initial_df = pd.DataFrame({
            'custom_id': ['A1', 'A2', 'A3'],
            'name': ['John', 'Jane', 'Bob']
        })
        mock_read.return_value = initial_df.copy()
        
        result = delete_item('A2', id_column='custom_id')
        
        assert result["success"] is True
        mock_write.assert_called_once()
        updated_df = mock_write.call_args[0][0]
        assert 'A2' not in updated_df['custom_id'].values