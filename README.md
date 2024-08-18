# Claude-Pyrojects
_sorry, I suck at naming_

Claude-Pyrojects is a Python package that allows you to easily upload your entire project directory to a Claude project. By doing this, Claude can access your project files and utilize them effectively. This is particularly useful for leveraging Claude's capabilities in understanding and interacting with your codebase.

Special thanks to the creators of [ClaudeAPI](https://github.com/KoushikNavuluri/Claude-API), specifically [n0kovo](https://github.com/n0kovo)'s branch

## Features

- **Initialize Project**: Set up your project directory for integration with Claude by creating a `.ignore` file to specify folders and files that should be excluded from the upload.
- **Create Claude Project**: Automatically create a new project in Claude and upload the entire directory structure and files.
- **Update Project**: Reinitialize your Claude project by clearing existing files and re-uploading the current state of your project directory.
- **Flexible Ignoring**: Customize which folders, file types, and specific file names to exclude using the `claude_pyrojects.ignore` file.

## Prerequisites

- A Claude account (Claude Pro is recommended for the best experience).
- Python 3.6 or higher.
- An active Claude session key, which can be obtained from your Claude account.

## Installation

To install Claude-Pyrojects, use pip:

```bash
pip install claude-pyrojects
```

## Usage

### Step 1: Initialize the Project

The first step is to initialize the project. This will create the necessary configuration files, including the ignore file (claude_pyrojects.ignore) and save your session key.

Refer to [this](https://github.com/KoushikNavuluri/Claude-API?tab=readme-ov-file#usage) on how to get your session key.

```bash
python -m claude-pyrojects.cli init -K "your_session_key"
```

### Step 2: Create a New Project in Claude

Once your project is initialized, you can create a new project in Claude. This will upload your entire project directory, excluding any files and folders specified in the ignore file.

```bash
python -m claude-pyrojects.cli create -N "Your Project Name"
```

### Step 3: Update the Claude Project

As your project evolves, you might need to re-upload it to Claude to reflect the latest changes. The update command reinitializes the project by clearing all existing files and re-uploading the current state of your directory.

```bash
python -m claude-pyrojects.cli update
```

### Customizing the Ignore File

The claude_pyrojects.ignore file allows you to specify folders, file extensions, and specific filename substrings to exclude from the upload process.

Example `claude_pyrojects.ignore`:
```plaintext
ignore_folders=[".venv", ".idea", ".vscode"]
ignore_file_extensions=["pdf", "jpg", "png", "pyc"]
ignore_name_includes=["claude_pyrojects"]
```

- ignore_folders: List of folders to be ignored.
- ignore_file_extensions: List of file extensions to be ignored.
- ignore_name_includes: List of substrings that, if found in a filename, will cause the file to be ignored.

### Changing the Session Key

In order to change the session key, simply look for the `claude_pyrojects.key` file and replace it's contents with your new key

## Planned Features
- GitHub Integration: A GitHub app that automatically updates the Claude project whenever changes are pushed to the repository.

## Disclaimer

This project provides an unofficial API for Claude AI and is not affiliated with or endorsed by Claude AI or Anthropic. Use it at your own risk.

Please refer to the official [Claude AI documentation](https://claude.ai/docs) for more information on how to use Claude AI.
