import os
import json
import hashlib
from datetime import datetime
from pathlib import Path


class FileChangeTracker:
    def __init__(self, manifest_file='claude_pyrojects.manifest'):
        self.manifest_file = manifest_file
        self.manifest = self.load_manifest()

    def load_manifest(self):
        """Load the manifest file containing file hashes and metadata."""
        if os.path.exists(self.manifest_file):
            with open(self.manifest_file, 'r') as f:
                return json.load(f)
        return {'files': {}, 'last_sync': None}

    def save_manifest(self):
        """Save the manifest file."""
        self.manifest['last_sync'] = datetime.now().isoformat()
        with open(self.manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2)

    def calculate_file_hash(self, file_path):
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def get_file_metadata(self, file_path):
        """Get file metadata including hash and modification time."""
        stat = os.stat(file_path)
        return {
            'hash': self.calculate_file_hash(file_path),
            'mtime': stat.st_mtime,
            'size': stat.st_size
        }

    def scan_directory(self, directory_path, ignore_folders, ignore_extensions, ignore_name_includes):
        """Scan directory and return current file states."""
        current_files = {}

        for root, dirs, files in os.walk(directory_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_folders]

            for file in files:
                # Skip ignored files
                if any(file.endswith(ext) for ext in ignore_extensions):
                    continue
                if any(substring in file for substring in ignore_name_includes):
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, directory_path)

                try:
                    current_files[relative_path] = self.get_file_metadata(file_path)
                except Exception as e:
                    print(f"Error processing {relative_path}: {e}")

        return current_files

    def get_changes(self, directory_path, ignore_folders, ignore_extensions, ignore_name_includes):
        """Compare current state with manifest and return changes."""
        current_files = self.scan_directory(directory_path, ignore_folders, ignore_extensions, ignore_name_includes)
        previous_files = self.manifest.get('files', {})

        changes = {
            'added': [],
            'modified': [],
            'deleted': []
        }

        # Check for new and modified files
        for file_path, metadata in current_files.items():
            if file_path not in previous_files:
                changes['added'].append(file_path)
            elif previous_files[file_path]['hash'] != metadata['hash']:
                changes['modified'].append(file_path)

        # Check for deleted files
        for file_path in previous_files:
            if file_path not in current_files:
                changes['deleted'].append(file_path)

        return changes, current_files

    def update_manifest(self, current_files):
        """Update manifest with current file states."""
        self.manifest['files'] = current_files
        self.save_manifest()
