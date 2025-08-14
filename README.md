# Claude-Pyrojects
_sorry, I suck at naming_

Claude-Pyrojects is a Python package that allows you to easily upload your entire project directory to a Claude project. By doing this, Claude can access your project files and utilize them effectively. This is particularly useful for leveraging Claude's capabilities in understanding and interacting with your codebase.

Special thanks to the creators of [ClaudeAPI](https://github.com/KoushikNavuluri/Claude-API), specifically [n0kovo](https://github.com/n0kovo)'s branch

## Features

- **Initialize Project**: Set up your project directory for integration with Claude by creating a `.ignore` file to specify folders and files that should be excluded from the upload.
- **Create Claude Project**: Automatically create a new project in Claude and upload the entire directory structure and files.
- **Update Project**: Reinitialize your Claude project by clearing existing files and re-uploading the current state of your project directory.
- **Flexible Ignoring**: Customize which folders, file types, specific file names, and relative paths to exclude using the `claude_pyrojects.ignore` file.

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

The claude_pyrojects.ignore file allows you to specify folders, file extensions, specific filename substrings, and relative paths to exclude from the upload process.

Example `claude_pyrojects.ignore`:
```plaintext
ignore_folders=[".venv", ".idea", ".vscode", "__pycache__", ".git"]
ignore_file_extensions=["pdf", "jpg", "png", "pyc", "manifest"]
ignore_name_includes=["claude_pyrojects", ".DS_Store"]
ignore_relative_paths=["docs/build", "tests/temp", "data/cache"]
```

#### Ignore Options Explained:

- **ignore_folders**: List of folder names to be ignored anywhere in the directory tree.
- **ignore_file_extensions**: List of file extensions to be ignored (without the dot).
- **ignore_name_includes**: List of substrings that, if found in a filename, will cause the file to be ignored.
- **ignore_relative_paths**: List of relative paths (from project root) to be ignored. This allows you to ignore specific subfolders like `"folder/subfolder"` or `"src/tests/fixtures"`.

#### Relative Path Examples:

```plaintext
ignore_relative_paths=[
    "docs/build",           # Ignores the build folder inside docs
    "tests/temp",           # Ignores the temp folder inside tests  
    "data/cache",           # Ignores the cache folder inside data
    "frontend/node_modules", # Ignores node_modules in frontend folder
    "src/generated"         # Ignores the generated folder inside src
]
```

**Note**: Relative paths are normalized to work across different operating systems (Windows, macOS, Linux). You can use either forward slashes `/` or backslashes `\` - they will be handled correctly.

### Changing the Session Key

In order to change the session key, simply look for the `claude_pyrojects.key` file and replace its contents with your new key

## Planned Features
- GitHub Integration: A GitHub app that automatically updates the Claude project whenever changes are pushed to the repository.

## Disclaimer

This project provides an unofficial API for Claude AI and is not affiliated with or endorsed by Claude AI or Anthropic. Use it at your own risk.

Please refer to the official [Claude AI documentation](https://claude.ai/docs) for more information on how to use Claude AI.

## GitAds Sponsored
[![Sponsored by GitAds](https://gitads.dev/v1/ad-serve?source=hcevikdotpy/claude-pyrojects@github)](https://gitads.dev/v1/ad-track?source=hcevikdotpy/claude-pyrojects@github)


<!-- GitAds-Verify: HVYDUCFSFZ1GH8LZOA2GDGH2987YH2FH -->