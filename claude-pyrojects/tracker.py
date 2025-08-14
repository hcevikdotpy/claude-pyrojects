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

    def _should_ignore_path(self, relative_path, ignore_relative_paths):
        """Check if a relative path should be ignored based on ignore_relative_paths rules"""
        # Normalize the path for cross-platform compatibility
        normalized_path = os.path.normpath(relative_path).replace('\\', '/')

        for ignore_path in ignore_relative_paths:
            # Normalize the ignore path too
            normalized_ignore = os.path.normpath(ignore_path).replace('\\', '/')

            # Check if the path starts with the ignore pattern
            if normalized_path.startswith(normalized_ignore):
                # Make sure it's a complete directory match (not partial)
                if len(normalized_path) == len(normalized_ignore) or \
                        normalized_path[len(normalized_ignore)] in ['/', '\\']:
                    return True
        return False

    def scan_directory(self, directory_path, ignore_folders, ignore_extensions, ignore_name_includes,
                       ignore_relative_paths=[]):
        """Scan directory and return current file states."""
        current_files = {}

        for root, dirs, files in os.walk(directory_path):
            # Calculate relative path for this directory
            rel_root = os.path.relpath(root, directory_path)
            if rel_root == '.':
                rel_root = ''

            # Check if this directory should be ignored by relative path
            if rel_root and self._should_ignore_path(rel_root, ignore_relative_paths):
                dirs.clear()  # Don't descend into this directory
                continue

            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_folders]

            # Also filter out directories that would be ignored by relative path
            dirs[:] = [d for d in dirs if not self._should_ignore_path(
                os.path.join(rel_root, d) if rel_root else d, ignore_relative_paths)]

            for file in files:
                # Skip ignored files
                if any(file.endswith(ext) for ext in ignore_extensions):
                    continue
                if any(substring in file for substring in ignore_name_includes):
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, directory_path)

                # Check if file would be ignored by relative path
                if self._should_ignore_path(relative_path, ignore_relative_paths):
                    continue

                try:
                    current_files[relative_path] = self.get_file_metadata(file_path)
                except Exception as e:
                    print(f"Error processing {relative_path}: {e}")

        return current_files

    def get_changes(self, directory_path, ignore_folders, ignore_extensions, ignore_name_includes,
                    ignore_relative_paths=[]):
        """Compare current state with manifest and return changes."""
        current_files = self.scan_directory(directory_path, ignore_folders, ignore_extensions, ignore_name_includes,
                                            ignore_relative_paths)
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