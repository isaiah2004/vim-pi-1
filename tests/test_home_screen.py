import pytest
from unittest.mock import Mock, patch
import os
from pathlib import Path
import io
import pickle
from datetime import datetime

# Import the classes we want to test
from src.synchronize import Drive
from src.utils.Utils import Utils

# Mock the Google Drive API service
@pytest.fixture
def mock_drive_service():
    with patch('src.synchronize.build') as mock_build:
        mock_service = Mock()
        mock_build.return_value = mock_service
        yield mock_service

@pytest.fixture
def sample_drive():
    with patch('src.synchronize.build'):
        return Drive(credentials_path=Path("tests/mock_credentials"))

# Test Drive class initialization
def test_drive_init(sample_drive):
    assert isinstance(sample_drive, Drive)
    assert hasattr(sample_drive, '_Drive__service')

# Test list_files method
def test_list_files(sample_drive, mock_drive_service):
    mock_response = {
        'files': [
            {'id': '1', 'name': 'file1.txt', 'modifiedTime': '2023-01-01T00:00:00Z', 'mimeType': 'text/plain'},
            {'id': '2', 'name': 'folder1', 'modifiedTime': '2023-01-02T00:00:00Z', 'mimeType': 'application/vnd.google-apps.folder'}
        ]
    }
    mock_drive_service.files().list().execute.return_value = mock_response
    
    result = sample_drive.list_files('parent_folder_id')
    
    assert len(result['all']) == 2
    assert result['names'] == ['file1.txt', 'folder1']
    mock_drive_service.files().list.assert_called_once_with(
        q="'parent_folder_id' in parents",
        fields='files(id,name,modifiedTime,mimeType)'
    )

# Test download_file method
def test_download_file(sample_drive, mock_drive_service, tmp_path):
    file_id = 'test_file_id'
    filename = 'test_file.txt'
    local_path = tmp_path / 'test_folder'
    local_path.mkdir()
    
    mock_request = Mock()
    mock_drive_service.files().get_media.return_value = mock_request
    mock_drive_service.files().get().execute.return_value = {'modifiedTime': '2023-01-01T00:00:00Z'}
    
    with patch('src.synchronize.MediaIoBaseDownload') as mock_download:
        mock_download.return_value.next_chunk.side_effect = [(None, True)]
        
        sample_drive.download_file(filename, local_path, file_id)
    
    assert (local_path / filename).exists()
    mock_drive_service.files().get_media.assert_called_once_with(fileId=file_id)
    mock_drive_service.files().get.assert_called_once_with(fileId=file_id, fields='modifiedTime')

# Test upload_file method
def test_upload_file(sample_drive, mock_drive_service, tmp_path):
    folder_id = 'test_folder_id'
    filename = 'test_file.txt'
    local_path = tmp_path / 'test_folder'
    local_path.mkdir()
    (local_path / filename).write_text('Test content')
    
    mock_drive_service.files().create().execute.return_value = {'id': 'new_file_id'}
    
    with patch('src.synchronize.MediaFileUpload') as mock_upload:
        result = sample_drive.upload_file(filename, local_path, folder_id)
    
    assert result == {'id': 'new_file_id'}
    mock_drive_service.files().create.assert_called_once()
    mock_upload.assert_called_once_with(local_path / filename)

# Test upload_folder method
def test_upload_folder(sample_drive, mock_drive_service):
    folder_name = 'test_folder'
    parent_folder_id = 'parent_folder_id'
    
    mock_drive_service.files().create().execute.return_value = {'id': 'new_folder_id', 'name': folder_name}
    
    result = sample_drive.upload_folder(folder_name, parent_folder_id)
    
    assert result == 'new_folder_id'
    mock_drive_service.files().create.assert_called_once_with(
        body={'name': folder_name, 'parents': [parent_folder_id], 'mimeType': 'application/vnd.google-apps.folder'}
    )

# Test compare_files method
def test_compare_files(sample_drive):
    local_file_data = {'modifiedTime': 1000}
    remote_file_data = {'modifiedTime': 900}
    
    result = sample_drive.compare_files(local_file_data, remote_file_data)
    assert result == 'local'
    
    local_file_data = {'modifiedTime': 800}
    remote_file_data = {'modifiedTime': 900}
    
    result = sample_drive.compare_files(local_file_data, remote_file_data)
    assert result == 'remote'
    
    local_file_data = {'modifiedTime': 900}
    remote_file_data = {'modifiedTime': 900}
    
    result = sample_drive.compare_files(local_file_data, remote_file_data)
    assert result == False

# Test synchronize method
@pytest.mark.parametrize("local_files,drive_files,expected_uploads,expected_downloads", [
    (
        ['file1.txt'],
        {'all': [{'name': 'file2.txt', 'id': '2', 'modifiedTime': '2023-01-01T00:00:00Z', 'mimeType': 'text/plain'}], 'names': ['file2.txt']},
        ['file1.txt'],
        ['file2.txt']
    ),
    (
        ['file1.txt', 'file2.txt'],
        {'all': [
            {'name': 'file1.txt', 'id': '1', 'modifiedTime': '2023-01-01T00:00:00Z', 'mimeType': 'text/plain'},
            {'name': 'file2.txt', 'id': '2', 'modifiedTime': '2023-01-02T00:00:00Z', 'mimeType': 'text/plain'},
            {'name': 'file3.txt', 'id': '3', 'modifiedTime': '2023-01-03T00:00:00Z', 'mimeType': 'text/plain'}
        ], 'names': ['file1.txt', 'file2.txt', 'file3.txt']},
        [],
        ['file3.txt']
    )
])
def test_synchronize(sample_drive, mock_drive_service, tmp_path, local_files, drive_files, expected_uploads, expected_downloads):
    local_path = tmp_path / 'test_folder'
    local_path.mkdir()
    for file in local_files:
        (local_path / file).write_text('Test content')
    
    folder_id = 'test_folder_id'
    
    mock_drive_service.files().list().execute.return_value = {'files': drive_files['all']}
    
    with patch.object(sample_drive, 'upload_file') as mock_upload, \
         patch.object(sample_drive, 'download_file') as mock_download, \
         patch.object(Utils, 'get_local_file_timestamp', return_value=1000):
        
        sample_drive.synchronize(local_path, folder_id)
        
        assert mock_upload.call_count == len(expected_uploads)
        assert mock_download.call_count == len(expected_downloads)
        
        for file in expected_uploads:
            mock_upload.assert_any_call(file, local_path, folder_id)
        
        for file in expected_downloads:
            file_data = next(f for f in drive_files['all'] if f['name'] == file)
            mock_download.assert_any_call(file, local_path, file_data['id'])

# Test get_or_create_folder method
@pytest.mark.parametrize("folder_exists", [True, False])
def test_get_or_create_folder(sample_drive, mock_drive_service, folder_exists):
    folder_name = 'test_folder'
    
    if folder_exists:
        mock_drive_service.files().list().execute.return_value = {'files': [{'id': 'existing_folder_id', 'name': folder_name}]}
        expected_id = 'existing_folder_id'
    else:
        mock_drive_service.files().list().execute.return_value = {'files': []}
        mock_drive_service.files().create().execute.return_value = {'id': 'new_folder_id'}
        expected_id = 'new_folder_id'
    
    result = sample_drive.get_or_create_folder(folder_name)
    
    assert result == expected_id
    mock_drive_service.files().list.assert_called_once_with(
        q=f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and 'root' in parents",
        fields='files(id, name)'
    )
    
    if not folder_exists:
        mock_drive_service.files().create.assert_called_once_with(
            body={'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': ['root']},
            fields='id'
        )

# Test Utils class methods
def test_list_local_files(tmp_path):
    local_path = tmp_path / 'test_folder'
    local_path.mkdir()
    (local_path / 'file1.txt').write_text('Test content')
    (local_path / 'file2.txt').write_text('Test content')
    
    result = Utils.list_local_files(local_path)
    assert set(result) == {'file1.txt', 'file2.txt'}

def test_get_local_file_timestamp(tmp_path):
    file_path = tmp_path / 'test_file.txt'
    file_path.write_text('Test content')
    
    result = Utils.get_local_file_timestamp(file_path)
    assert isinstance(result, int)
    assert result > 0

def test_convert_datetime_timestamp():
    date_str = '2023-01-01T00:00:00Z'
    result = Utils.convert_datetime_timestamp(date_str)
    assert result == 1672531200  # Unix timestamp for 2023-01-01 00:00:00 UTC

def test_convert_timestamp_datetime():
    timestamp = 1672531200  # Unix timestamp for 2023-01-01 00:00:00 UTC
    result = Utils.convert_timestamp_datetime(timestamp)
    assert result == '2023-01-01T00:00:00Z'

# Integration test
def test_full_sync_workflow(sample_drive, mock_drive_service, tmp_path):
    local_path = tmp_path / 'test_folder'
    local_path.mkdir()
    (local_path / 'local_file.txt').write_text('Local content')
    
    folder_id = 'test_folder_id'
    
    # Mock list_files
    mock_drive_service.files().list().execute.return_value = {
        'files': [
            {'id': '1', 'name': 'remote_file.txt', 'modifiedTime': '2023-01-01T00:00:00Z', 'mimeType': 'text/plain'},
            {'id': '2', 'name': 'local_file.txt', 'modifiedTime': '2022-01-01T00:00:00Z', 'mimeType': 'text/plain'}
        ]
    }
    
    # Mock file operations
    mock_drive_service.files().get_media.return_value = io.BytesIO(b'Remote content')
    mock_drive_service.files().get().execute.return_value = {'modifiedTime': '2023-01-01T00:00:00Z'}
    mock_drive_service.files().create().execute.return_value = {'id': 'new_file_id'}
    mock_drive_service.files().update().execute.return_value = {'id': '2'}
    
    with patch.object(Utils, 'get_local_file_timestamp', return_value=1672531200):  # 2023-01-01 00:00:00 UTC
        sample_drive.synchronize(local_path, folder_id)
    
    # Check local files
    assert (local_path / 'local_file.txt').read_text() == 'Local content'
    assert (local_path / 'remote_file.txt').read_text() == 'Remote content'
    
    # Verify API calls
    mock_drive_service.files().list.assert_called_once()
    mock_drive_service.files().get_media.assert_called_once()
    mock_drive_service.files().create.assert_called_once()
    mock_drive_service.files().update.assert_called_once()

if __name__ == '__main__':
    pytest.main()