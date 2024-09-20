import os
import time
import re
import calendar
from datetime import datetime
import pathlib
import pickle
import os
import io
from pathlib import Path

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account


class Utils:
    # Return list of all files in specified folder
    @classmethod
    def list_local_files(cls, local_path):
        return os.listdir(local_path)

    # Get last modification timestamp from local file
    @classmethod
    def get_local_file_timestamp(cls, path):
        unix_timestamp = os.path.getmtime(path)
        utc_datetime = cls.convert_timestamp_datetime(unix_timestamp)
        utc_timestamp = cls.convert_datetime_timestamp(utc_datetime)

        return int(unix_timestamp)

    # Convert Google's datetime to local timestamp
    @classmethod
    def convert_datetime_timestamp(cls, date):
        date = re.sub(r"\.\d+", "", date)
        time_object = time.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
        timestamp = calendar.timegm(time_object)

        return int(timestamp)

    # Convert local timestamp to Google Drive's datetime
    @classmethod
    def convert_timestamp_datetime(cls, timestamp):
        datetime_object = datetime.utcfromtimestamp(timestamp)

        return datetime_object.isoformat("T") + "Z"




class Drive:
    def __init__(self, credentials_path: Path = Path("."), use_service_account: bool = False):
        self.__service = self.__authenticate(credentials_path, use_service_account)

    def __authenticate(self, credentials_path: Path, use_service_account: bool):
        creds = None
        scopes = ['https://www.googleapis.com/auth/drive']

        if use_service_account:
            service_account_file = credentials_path / "service-account-key.json"
            if not service_account_file.exists():
                raise FileNotFoundError(f"Service account key file not found: {service_account_file}")
            creds = service_account.Credentials.from_service_account_file(
                str(service_account_file), scopes=scopes)
        else:
            token_path = credentials_path / 'token.pickle'
            credentials_file = credentials_path / "credentials.json"

            if token_path.exists():
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not credentials_file.exists():
                        raise FileNotFoundError(f"Credentials file not found: {credentials_file}")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(credentials_file), scopes
                    )
                    creds = flow.run_local_server(port=0)

                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)

        return build('drive', 'v3', credentials=creds)

    def get_service(self):
        return self.__service
    
    def delete_file_or_folder(self, file_id):
        try:
            self.__service.files().delete(fileId=file_id).execute()
            print(f"Deleted file or folder with ID: {file_id}")
        except Exception as e:
            print(f"An error occurred while deleting file or folder: {e}")

    # List all files inside specified Drive folder
    def list_files(self, folder_id):
        # Call API
        response = self.__service.files().list(q="'{}' in parents".format(folder_id),
                                               fields='files(id,name,modifiedTime,mimeType)').execute()

        # Return all file names
        files_dic = {"all": response.get('files', []), "names": []}
        for item in files_dic['all']:
            files_dic['names'].append(item['name'])

        return files_dic

    # Download file from drive to local folder
    def download_file(self, filename, local_path, file_id, update=False):
        local_absolute_path = Path(f"{local_path}") / f"{filename}"

        # Request for download API
        request = self.__service.files().get_media(fileId=file_id)

        # File stream
        fh = io.BytesIO()

        # Setup request and file stream
        downloader = MediaIoBaseDownload(fh, request)

        # Wait while file is being downloaded
        done = False
        while done is False:
            done = downloader.next_chunk()

        # Save download buffer to file
        with open(local_absolute_path, 'wb') as out:
            out.write(fh.getbuffer())

        # Change local modification time to match remote
        modified_time = self.__service.files().get(fileId=file_id, fields='modifiedTime').execute()['modifiedTime']
        modified_timestamp = Utils.convert_datetime_timestamp(modified_time)
        os.utime(local_absolute_path, (modified_timestamp, modified_timestamp))

        if update != False:
            print("\nLocal file '{}' updated successfully in folder '{}'.".format(filename, local_absolute_path))
        else:

            print("\nFile '{}' downloaded successfully in folder '{}'.".format(filename, local_absolute_path))

    # Upload file from local to drive folder
    def upload_file(self, filename, local_path, folder_id, update=False):
        local_absolute_path = Path(f"{local_path}") / f"{filename}"

        # Custom file metadata for upload (modification time matches local)
        modified_timestamp = Utils.get_local_file_timestamp(local_absolute_path)
        file_metadata = {'name': filename, 'modifiedTime': Utils.convert_timestamp_datetime(modified_timestamp),
                         'parents': [folder_id]}

        # File definitions for upload
        media = MediaFileUpload(local_absolute_path)

        # Send POST request for upload API
        try:
            if update != False:
                uploaded_file = self.__service.files().update(fileId=update, media_body=media).execute()
                print("\nRemote file '{}' updated successfully in folder '{}'.".format(filename, local_absolute_path))
            else:
                uploaded_file = self.__service.files().create(body=file_metadata, media_body=media,
                                                              fields='id').execute()
                print("\nFile '{}' uploaded successfully in folder '{}'.".format(filename, local_absolute_path))

            return uploaded_file
        except:
            print('\nError uploading file: {}'.format(filename))

            return False

    # Create folder with respective parent Folder ID
    def upload_folder(self, foldername, folder_id):
        # Custom folder metadata for upload
        folder_metadata = {'name': foldername, 'parents': [folder_id], 'mimeType': 'application/vnd.google-apps.folder'}

        try:
            # Send POST request for upload API
            uploaded_folder = self.__service.files().create(body=folder_metadata).execute()
            print('\nRemote folder created: {}'.format(uploaded_folder['name']))

            return uploaded_folder['id']
        except:
            print('\nError creating folder...')

            return False

    # Verifies if file was modified or not
    def compare_files(self, local_file_data, remote_file_data):
        modified = False

        if local_file_data['modifiedTime'] > remote_file_data['modifiedTime']:
            modified = 'local'
        elif local_file_data['modifiedTime'] < remote_file_data['modifiedTime']:
            modified = 'remote'

        return modified

    # Recursive method to synchronize all folder and files
    def synchronize(self, local_path, folder_id):
        print("------------- Synchronizing folder '{}' -------------".format(local_path), end="\r")

        # Check if local path exists, if not, creates folder
        if not os.path.exists(local_path):
            os.makedirs(local_path)

        # List remote and local files
        drive_files = self.list_files(folder_id)
        local_files = Utils.list_local_files(local_path)

        # Compare files with same name in both origins and check which is newer, updating
        same_files = list(set(drive_files['names']) & set(local_files))
        for sm_file in same_files:
            local_absolute_path = pathlib.Path(f"{local_path}") / f"{sm_file}"

            remote_file_data = next(
                item for item in drive_files['all'] if item["name"] == sm_file)  # Filter to respective file
            remote_file_data["modifiedTime"] = Utils.convert_datetime_timestamp(remote_file_data["modifiedTime"])

            local_file_data = {}
            local_file_data["name"] = sm_file
            local_file_data["modifiedTime"] = Utils.get_local_file_timestamp(local_absolute_path)

            # Checks if files were modified on any origin
            modified = self.compare_files(local_file_data, remote_file_data)

            if modified == 'local':
                if os.path.isdir(local_absolute_path):
                    self.synchronize(local_absolute_path, remote_file_data['id'])
                else:
                    self.upload_file(sm_file, local_path, folder_id, remote_file_data['id'])

            elif modified == 'remote':
                if remote_file_data["mimeType"] == 'application/vnd.google-apps.folder':
                    self.synchronize(local_absolute_path, remote_file_data['id'])
                else:
                    self.download_file(sm_file, local_path, remote_file_data['id'], True)

        # Compare different files in both origins and download/upload what is needed
        different_files = list(set(drive_files['names']) ^ set(local_files))
        for diff_file in different_files:
            # IF file is only on Google Drive (DOWNLOAD)
            if diff_file in drive_files['names']:
                for remote_file in drive_files['all']:
                    if remote_file['name'] == diff_file:
                        if remote_file['mimeType'] == 'application/vnd.google-apps.folder':
                            local_absolute_path = Path(f"{local_path}") / f"{diff_file}"
                            self.synchronize(local_absolute_path,
                                             remote_file['id'])  # Recursive to download files inside folders
                        else:
                            self.download_file(remote_file['name'], local_path, remote_file['id'])

            # IF file is only on local (UPLOAD)
            else:
                local_absolute_path = Path(f"{local_path}") / f"{diff_file}"

                # Check if path redirects to a file or folder
                if os.path.isdir(local_absolute_path):
                    created_folder_id = self.upload_folder(diff_file, folder_id)
                    if created_folder_id != False:
                        self.synchronize(local_absolute_path,
                                         created_folder_id)  # Recursive to upload files inside folders
                else:
                    self.upload_file(diff_file, local_path, folder_id)

    # Check if folder exists, if not, create it
    def get_or_create_folder(self, folder_name):
        # Search for the folder in the root directory (parent is 'root')
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and 'root' in parents"
        response = self.__service.files().list(q=query, fields='files(id, name)').execute()
        files = response.get('files', [])

        if files:
            # Folder exists, return its ID
            folder_id = files[0]['id']
            print(f"Folder '{folder_name}' found with ID: {folder_id}")
            return folder_id
        else:
            # Folder does not exist, create it
            folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder',
                               'parents': ['root']}
            created_folder = self.__service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = created_folder['id']
            print(f"Folder '{folder_name}' created with ID: {folder_id}")
            return folder_id
