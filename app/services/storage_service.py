import os
from dotenv import load_dotenv

from b2sdk.v2 import InMemoryAccountInfo
from b2sdk.v2 import B2Api

from urllib.parse import quote

load_dotenv()


class B2Storage:

    def __init__(self):

        self.key_id = os.getenv("B2_KEY_ID")
        self.application_key = os.getenv("B2_APPLICATION_KEY")
        self.bucket_name = os.getenv("B2_BUCKET_NAME")

        # Initialize B2 API
        info = InMemoryAccountInfo()

        self.b2_api = B2Api(info)

        self.b2_api.authorize_account( 
            "production",
            self.key_id,
            self.application_key
        )

        account_info = self.b2_api.account_info

        self.auth_token = account_info.get_account_auth_token()

        self.download_url = account_info.get_download_url()


        # Get bucket
        self.bucket = self.b2_api.get_bucket_by_name(
            self.bucket_name
        )

        print("Backblaze B2 Connected")


    def upload_file(
        self,
        local_file_path,
        b2_file_name
    ):

        uploaded_file = self.bucket.upload_local_file(
            local_file=local_file_path,
            file_name=b2_file_name
        )

        file_url = (
            f"https://f005.backblazeb2.com/file/"
            f"{self.bucket_name}/{b2_file_name}"
        )

        return {
            "file_name": b2_file_name,
            "file_url": file_url
        }


    def list_files(self):

        files = []

        for file_version, folder_name in self.bucket.ls():

            file_name = file_version.file_name

            file_url = (
                f"https://f005.backblazeb2.com/file/"
                f"{self.bucket_name}/{file_name}"
            )

            files.append({
                "file_name": file_name,
                "file_url": file_url
            })

        return files
    
    
    def download_file(
        self,
        file_name,
        save_path
    ):

        downloaded_file = self.bucket.download_file_by_name(
            file_name
        )

        downloaded_file.save_to(save_path)

        return save_path
    
    def generate_file_url(self, file_name, bucket_name=None):
        bname = bucket_name or self.bucket_name
        return (
            f"https://f005.backblaze.com/file/"
            f"{bname}/{file_name}"
        )
    
    def generate_file_url_show(
        self,
        file_name,
        bucket_name=None
    ):
        bname = bucket_name or self.bucket_name
        encoded_file_name = quote(file_name)

        return (
            f"{self.download_url}/file/"
            f"{bname}/"
            f"{encoded_file_name}"
            f"?Authorization={self.auth_token}"
        )

    def list_files_in_bucket(self, bucket_name=None):
        """List files in a specific bucket."""

        if bucket_name and bucket_name != self.bucket_name:
            bucket = self.b2_api.get_bucket_by_name(
                bucket_name
            )
        else:
            bucket = self.bucket
            bucket_name = self.bucket_name

        files = []

        for file_version, folder_name in bucket.ls():

            file_name = file_version.file_name

            file_url = (
                f"https://f005.backblazeb2.com/file/"
                f"{bucket_name}/{file_name}"
            )

            files.append({
                "file_name": file_name,
                "file_url": file_url
            })

        return files

    def download_file_from_bucket(
        self,
        file_name,
        save_path,
        bucket_name=None
    ):
        """Download a file from a specific bucket."""

        if bucket_name and bucket_name != self.bucket_name:
            bucket = self.b2_api.get_bucket_by_name(
                bucket_name
            )
        else:
            bucket = self.bucket

        downloaded_file = bucket.download_file_by_name(
            file_name
        )

        downloaded_file.save_to(save_path)

        return save_path
