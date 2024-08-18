import os
from curl_cffi import requests
import json


class ClaudeAPI:
    BASE_URL = "https://claude.ai/api"
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'

    def __init__(self, session_key):
        self.session_key = session_key
        self.cookie = f"sessionKey={session_key}"
        self.organization_id = self._get_organization_id()

    def _get_organization_id(self):
        url = f"{self.BASE_URL}/organizations"
        headers = self._get_headers()
        response = requests.get(url, headers=headers, impersonate="chrome110")
        response.raise_for_status()
        organizations = response.json()

        for org in organizations:
            if 'chat' in org['capabilities'] or 'claude_pro' in org['capabilities']:
                return org['uuid']

        raise ValueError("No organization found with 'chat' or 'claude_pro' capabilities")

    def _get_headers(self, extra_headers=None):
        headers = {
            'User-Agent': self.USER_AGENT,
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://claude.ai/chats',
            'Content-Type': 'application/json',
            'Connection': 'keep-alive',
            'Cookie': self.cookie,
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def create_project(self, organization_id, project_name, is_private=True, description=""):
        url = f"{self.BASE_URL}/organizations/{organization_id}/projects"
        payload = {
            "name": project_name,
            "is_private": is_private,
            "description": description,
        }
        response = requests.post(
            url,
            headers=self._get_headers(),
            data=json.dumps(payload),
            impersonate="chrome110",
        )
        if response.status_code != 201:
            print(f"Request failed: {response.status_code}, {response.text}")
        response.raise_for_status()
        return response.json()

    def list_files_in_project(self, project_uuid):
        url = f"{self.BASE_URL}/organizations/{self.organization_id}/projects/{project_uuid}/docs"
        response = requests.get(url, headers=self._get_headers(), impersonate="chrome110")
        if response.status_code != 200:
            print(f"Request failed: {response.status_code}, {response.text}")
        response.raise_for_status()
        return response.json()

    def delete_file_from_project(self, project_uuid, file_uuid):
        url = f"{self.BASE_URL}/organizations/{self.organization_id}/projects/{project_uuid}/docs/{file_uuid}"
        response = requests.delete(url, headers=self._get_headers(), impersonate="chrome110")
        if response.status_code != 204:
            print(f"Failed to delete file {file_uuid}: {response.status_code}, {response.text}")
        response.raise_for_status()
        print(f"Deleted file {file_uuid}")

    def add_file_to_project(self, project_uuid, file_name, content):
        url = f"{self.BASE_URL}/organizations/{self.organization_id}/projects/{project_uuid}/docs"
        payload = {
            "file_name": file_name,
            "content": content,
        }
        response = requests.post(
            url,
            headers=self._get_headers(),
            data=json.dumps(payload),
            impersonate="chrome110",
        )
        if response.status_code != 201:
            print(f"Request failed: {response.status_code}, {response.text}")
        response.raise_for_status()
        return response.json()

    def generate_file_structure(self, directory_path, exclude_folders, exclude_extensions, exclude_name_includes):
        structure = []
        for root, dirs, files in os.walk(directory_path):
            dirs[:] = [d for d in dirs if d not in exclude_folders]

            level = root.replace(directory_path, '').count(os.sep)
            indent = ' ' * 4 * level
            structure.append(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 4 * (level + 1)
            for file in files:
                if not any(file.endswith(ext) for ext in exclude_extensions) and \
                        not any(substring in file for substring in exclude_name_includes):
                    structure.append(f"{subindent}{file}")
        return "\n".join(structure)

    def upload_directory_with_structure(self, project_uuid, directory_path, config_manager):
        ignore_folders, ignore_extensions, ignore_name_includes = config_manager.load_ignore_rules()

        structure_content = self.generate_file_structure(directory_path, ignore_folders, ignore_extensions,
                                                         ignore_name_includes)
        self.add_file_to_project(project_uuid, "PROJECT_STRUCTURE.txt", structure_content)
        print("Uploaded PROJECT_STRUCTURE.txt")

        for root, dirs, files in os.walk(directory_path):
            dirs[:] = [d for d in dirs if d not in ignore_folders]

            for file in files:
                if not any(file.endswith(ext) for ext in ignore_extensions) and \
                        not any(substring in file for substring in ignore_name_includes):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        relative_path = os.path.relpath(file_path, directory_path)
                        print(f"Uploading {relative_path}...")
                        response = self.add_file_to_project(project_uuid, relative_path, content)
                        print(f"Uploaded {relative_path}: {response}")

    def reinitialize_project_files(self, project_uuid, directory_path, exclude_extensions=None):
        if exclude_extensions is None:
            exclude_extensions = []

        files = self.list_files_in_project(project_uuid)
        file_uuids = [file['uuid'] for file in files]

        for file_uuid in file_uuids:
            self.delete_file_from_project(project_uuid, file_uuid)

        self.upload_directory_with_structure(project_uuid, directory_path, exclude_extensions)
