import os
from curl_cffi import requests
import json
import hashlib
from datetime import datetime
import time
from tqdm import tqdm
import click


class RateLimitHandler:
    """Handle rate limiting with exponential backoff"""

    def __init__(self, max_retries=5, initial_wait=1.0):
        self.max_retries = max_retries
        self.initial_wait = initial_wait

    def execute_with_retry(self, func, *args, **kwargs):
        """Execute function with retry logic"""
        wait_time = self.initial_wait
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    if attempt < self.max_retries - 1:
                        click.echo(click.style(
                            f"\n⚠️  Rate limited. Waiting {wait_time:.1f}s before retry (attempt {attempt + 1}/{self.max_retries})...",
                            fg='yellow'
                        ))
                        time.sleep(wait_time)
                        wait_time *= 2  # Exponential backoff
                        continue
                    else:
                        click.echo(click.style(
                            f"\n❌ Rate limit exceeded after {self.max_retries} attempts",
                            fg='red'
                        ))
                last_error = e
                raise
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    click.echo(click.style(
                        f"\n⚠️  Error occurred: {str(e)}. Retrying in {wait_time:.1f}s...",
                        fg='yellow'
                    ))
                    time.sleep(wait_time)
                    wait_time *= 1.5
                    continue
                raise

        if last_error:
            raise last_error


class ClaudeAPI:
    BASE_URL = "https://claude.ai/api"
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'

    def __init__(self, session_key):
        self.session_key = session_key
        self.cookie = f"sessionKey={session_key}"
        self.rate_limit_handler = RateLimitHandler()
        self.organization_id = self._get_organization_id()
        self.manifest_file = 'claude_pyrojects.manifest'

    def _get_organization_id(self):
        url = f"{self.BASE_URL}/organizations"
        headers = self._get_headers()

        def _make_request():
            response = requests.get(url, headers=headers, impersonate="chrome110")
            response.raise_for_status()
            return response

        response = self.rate_limit_handler.execute_with_retry(_make_request)
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

        def _make_request():
            response = requests.post(
                url,
                headers=self._get_headers(),
                data=json.dumps(payload),
                impersonate="chrome110",
            )
            if response.status_code != 201:
                if response.status_code == 429:
                    raise requests.exceptions.HTTPError(response=response)
                click.echo(click.style(f"Request failed: {response.status_code}, {response.text}", fg='red'))
            response.raise_for_status()
            return response

        response = self.rate_limit_handler.execute_with_retry(_make_request)
        return response.json()

    def list_files_in_project(self, project_uuid):
        url = f"{self.BASE_URL}/organizations/{self.organization_id}/projects/{project_uuid}/docs"

        def _make_request():
            response = requests.get(url, headers=self._get_headers(), impersonate="chrome110")
            if response.status_code != 200:
                if response.status_code == 429:
                    raise requests.exceptions.HTTPError(response=response)
                click.echo(click.style(f"Request failed: {response.status_code}, {response.text}", fg='red'))
            response.raise_for_status()
            return response

        response = self.rate_limit_handler.execute_with_retry(_make_request)
        return response.json()

    def delete_file_from_project(self, project_uuid, file_uuid, file_name=""):
        url = f"{self.BASE_URL}/organizations/{self.organization_id}/projects/{project_uuid}/docs/{file_uuid}"

        def _make_request():
            response = requests.delete(url, headers=self._get_headers(), impersonate="chrome110")
            if response.status_code != 204:
                if response.status_code == 429:
                    raise requests.exceptions.HTTPError(response=response)
                click.echo(click.style(
                    f"Failed to delete file {file_name or file_uuid}: {response.status_code}, {response.text}",
                    fg='red'))
            response.raise_for_status()
            return response

        self.rate_limit_handler.execute_with_retry(_make_request)

    def add_file_to_project(self, project_uuid, file_name, content):
        url = f"{self.BASE_URL}/organizations/{self.organization_id}/projects/{project_uuid}/docs"
        payload = {
            "file_name": file_name,
            "content": content,
        }

        def _make_request():
            response = requests.post(
                url,
                headers=self._get_headers(),
                data=json.dumps(payload),
                impersonate="chrome110",
            )
            if response.status_code != 201:
                if response.status_code == 429:
                    raise requests.exceptions.HTTPError(response=response)
                click.echo(
                    click.style(f"Failed to upload {file_name}: {response.status_code}, {response.text}", fg='red'))
            response.raise_for_status()
            return response

        response = self.rate_limit_handler.execute_with_retry(_make_request)
        return response.json()

    def generate_file_structure(self, directory_path, exclude_folders, exclude_extensions, exclude_name_includes):
        structure = []
        total_files = 0

        # First pass to count files
        for root, dirs, files in os.walk(directory_path):
            dirs[:] = [d for d in dirs if d not in exclude_folders]
            for file in files:
                if not any(file.endswith(ext) for ext in exclude_extensions) and \
                        not any(substring in file for substring in exclude_name_includes):
                    total_files += 1

        click.echo(click.style(f"\n📊 Generating project structure ({total_files} files)...", fg='cyan'))

        # Second pass to build structure
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

        # Generate and upload structure file
        structure_content = self.generate_file_structure(directory_path, ignore_folders, ignore_extensions,
                                                         ignore_name_includes)
        self.add_file_to_project(project_uuid, "PROJECT_STRUCTURE.txt", structure_content)
        click.echo(click.style("✅ Uploaded PROJECT_STRUCTURE.txt", fg='green'))

        # Count total files to upload
        total_files = 0
        files_to_upload = []

        for root, dirs, files in os.walk(directory_path):
            dirs[:] = [d for d in dirs if d not in ignore_folders]
            for file in files:
                if not any(file.endswith(ext) for ext in ignore_extensions) and \
                        not any(substring in file for substring in ignore_name_includes):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, directory_path)
                    files_to_upload.append((file_path, relative_path))
                    total_files += 1

        # Upload files with progress bar
        click.echo(click.style(f"\n📤 Uploading {total_files} files...", fg='cyan'))

        with tqdm(total=total_files, desc="Uploading", unit="file",
                  bar_format='{l_bar}{bar:30}{r_bar}{bar:-10b}') as pbar:
            for file_path, relative_path in files_to_upload:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Update progress bar description
                    pbar.set_description(f"Uploading {relative_path[:40]}...")

                    response = self.add_file_to_project(project_uuid, relative_path, content)
                    pbar.update(1)

                except Exception as e:
                    pbar.write(click.style(f"❌ Failed to upload {relative_path}: {str(e)}", fg='red'))
                    pbar.update(1)

    def reinitialize_project_files(self, project_uuid, directory_path, config_manager):
        click.echo(click.style("\n🔄 Reinitializing project files...", fg='cyan'))

        # Delete existing files
        files = self.list_files_in_project(project_uuid)

        if files:
            click.echo(click.style(f"\n🗑️  Deleting {len(files)} existing files...", fg='yellow'))

            with tqdm(total=len(files), desc="Deleting", unit="file",
                      bar_format='{l_bar}{bar:30}{r_bar}{bar:-10b}') as pbar:
                for file in files:
                    file_name = file.get('file_name', 'Unknown')
                    pbar.set_description(f"Deleting {file_name[:40]}...")
                    self.delete_file_from_project(project_uuid, file['uuid'], file_name)
                    pbar.update(1)

        # Upload new files
        self.upload_directory_with_structure(project_uuid, directory_path, config_manager)

    def calculate_file_hash(self, file_path):
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def load_manifest(self):
        """Load the manifest file containing file hashes."""
        if os.path.exists(self.manifest_file):
            with open(self.manifest_file, 'r') as f:
                return json.load(f)
        return {'files': {}, 'last_sync': None}

    def save_manifest(self, manifest):
        """Save the manifest file."""
        manifest['last_sync'] = datetime.now().isoformat()
        with open(self.manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

    def scan_directory_changes(self, directory_path, ignore_folders, ignore_extensions, ignore_name_includes):
        """Scan directory and detect changes since last sync."""
        manifest = self.load_manifest()
        previous_files = manifest.get('files', {})
        current_files = {}
        changes = {
            'added': [],
            'modified': [],
            'deleted': []
        }

        # Count total files for progress bar (properly excluding ignored folders)
        total_files = 0
        for root, dirs, files in os.walk(directory_path):
            # Remove ignored directories from dirs list to prevent os.walk from descending into them
            dirs[:] = [d for d in dirs if d not in ignore_folders]

            for file in files:
                if not any(file.endswith(ext) for ext in ignore_extensions) and \
                        not any(substring in file for substring in ignore_name_includes):
                    total_files += 1

        if total_files > 0:
            click.echo(click.style(f"\n🔍 Scanning {total_files} files for changes...", fg='cyan'))

            with tqdm(total=total_files, desc="Scanning", unit="file",
                      bar_format='{l_bar}{bar:30}{r_bar}{bar:-10b}') as pbar:
                # Scan current files
                for root, dirs, files in os.walk(directory_path):
                    dirs[:] = [d for d in dirs if d not in ignore_folders]

                    for file in files:
                        if any(file.endswith(ext) for ext in ignore_extensions):
                            continue
                        if any(substring in file for substring in ignore_name_includes):
                            continue

                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, directory_path)

                        pbar.set_description(f"Scanning {relative_path[:40]}...")

                        try:
                            file_hash = self.calculate_file_hash(file_path)
                            current_files[relative_path] = {
                                'hash': file_hash,
                                'mtime': os.stat(file_path).st_mtime
                            }

                            if relative_path not in previous_files:
                                changes['added'].append(relative_path)
                            elif previous_files[relative_path]['hash'] != file_hash:
                                changes['modified'].append(relative_path)
                        except Exception as e:
                            pbar.write(click.style(f"❌ Error processing {relative_path}: {e}", fg='red'))

                        pbar.update(1)

        # Check for deleted files
        for file_path in previous_files:
            if file_path not in current_files:
                changes['deleted'].append(file_path)

        return changes, current_files

    def update_file_in_project(self, project_uuid, file_path, content):
        """Update a single file in the project."""
        # First, try to find and delete the existing file
        files = self.list_files_in_project(project_uuid)
        for file in files:
            if file['file_name'] == file_path:
                self.delete_file_from_project(project_uuid, file['uuid'], file_path)
                break

        # Upload the new version
        return self.add_file_to_project(project_uuid, file_path, content)

    def incremental_update_project(self, project_uuid, directory_path, config_manager):
        """Perform incremental update of project files."""
        ignore_folders, ignore_extensions, ignore_name_includes = config_manager.load_ignore_rules()

        # Get changes since last sync
        changes, current_files = self.scan_directory_changes(
            directory_path, ignore_folders, ignore_extensions, ignore_name_includes
        )

        # Count total changes
        total_changes = len(changes['added']) + len(changes['modified']) + len(changes['deleted'])

        if total_changes == 0:
            click.echo(click.style("\n✨ No changes detected since last sync.", fg='green'))
            return

        # Display change summary
        click.echo(click.style("\n📊 Detected changes:", fg='cyan'))
        if changes['added']:
            click.echo(click.style(f"  ➕ Added: {len(changes['added'])} files", fg='green'))
        if changes['modified']:
            click.echo(click.style(f"  ✏️  Modified: {len(changes['modified'])} files", fg='yellow'))
        if changes['deleted']:
            click.echo(click.style(f"  ➖ Deleted: {len(changes['deleted'])} files", fg='red'))

        # Handle deletions
        if changes['deleted']:
            click.echo(click.style(f"\n🗑️  Deleting {len(changes['deleted'])} files...", fg='yellow'))
            files = self.list_files_in_project(project_uuid)
            file_map = {f['file_name']: f['uuid'] for f in files}

            with tqdm(total=len(changes['deleted']), desc="Deleting", unit="file",
                      bar_format='{l_bar}{bar:30}{r_bar}{bar:-10b}') as pbar:
                for file_path in changes['deleted']:
                    if file_path in file_map:
                        pbar.set_description(f"Deleting {file_path[:40]}...")
                        self.delete_file_from_project(project_uuid, file_map[file_path], file_path)
                    pbar.update(1)

        # Handle additions and modifications
        files_to_process = changes['added'] + changes['modified']
        if files_to_process:
            action_msg = "📤 Uploading new and modified files..."
            click.echo(click.style(f"\n{action_msg}", fg='cyan'))

            with tqdm(total=len(files_to_process), desc="Uploading", unit="file",
                      bar_format='{l_bar}{bar:30}{r_bar}{bar:-10b}') as pbar:
                for file_path in files_to_process:
                    full_path = os.path.join(directory_path, file_path)
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()

                        action = "Adding" if file_path in changes['added'] else "Updating"
                        pbar.set_description(f"{action} {file_path[:40]}...")

                        if file_path in changes['modified']:
                            self.update_file_in_project(project_uuid, file_path, content)
                        else:
                            self.add_file_to_project(project_uuid, file_path, content)

                        pbar.update(1)

                    except Exception as e:
                        pbar.write(click.style(f"❌ Error processing {file_path}: {e}", fg='red'))
                        pbar.update(1)

        # Always update PROJECT_STRUCTURE.txt if there were any changes
        if changes['added'] or changes['deleted']:
            click.echo(click.style("\n📋 Updating PROJECT_STRUCTURE.txt...", fg='cyan'))
            structure_content = self.generate_file_structure(
                directory_path, ignore_folders, ignore_extensions, ignore_name_includes
            )
            self.update_file_in_project(project_uuid, "PROJECT_STRUCTURE.txt", structure_content)

        # Update manifest with current state
        manifest = self.load_manifest()
        manifest['files'] = current_files
        self.save_manifest(manifest)

        click.echo(click.style(f"\n✅ Incremental update completed. Synced {total_changes} changes.", fg='green'))

    def get_status(self, directory_path, config_manager):
        """Get status of changes without uploading."""
        ignore_folders, ignore_extensions, ignore_name_includes = config_manager.load_ignore_rules()
        changes, _ = self.scan_directory_changes(
            directory_path, ignore_folders, ignore_extensions, ignore_name_includes
        )
        manifest = self.load_manifest()
        return changes, manifest.get('last_sync')