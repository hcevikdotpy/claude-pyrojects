import click
import os
import requests.exceptions
from .api import ClaudeAPI
from .config import ConfigManager


@click.group()
def main():
    pass


@main.command()
@click.option('-K', '--session-key', required=True, help='Session key for Claude API.')
def init(session_key):
    """Initialize the Claude project by creating ignore and key files."""
    config = ConfigManager()

    # Initialize the ignore file
    config.initialize_ignore_file()

    # Save the session key in claude_pyrojects.key file
    with open('claude_pyrojects.key', 'w') as key_file:
        key_file.write(session_key)
        click.echo("Session key saved in 'claude_pyrojects.key'.")

    click.echo("Initialization complete. Ignore file and session key saved.")


@main.command()
@click.option('-N', '--project-name', required=True, help='Name of the new project.')
def create(project_name):
    """Create a new Claude project and upload the project structure."""
    try:
        # Load session key from claude_pyrojects.key
        with open('claude_pyrojects.key', 'r') as key_file:
            session_key = key_file.read().strip()

        api = ClaudeAPI(session_key)
        config = ConfigManager()

        project = api.create_project(api.organization_id, project_name)
        config.save_config(api.organization_id, project['uuid'], project['name'])
        click.echo(f"Project '{project_name}' created with UUID: {project['uuid']}")

        directory_path = os.getcwd()  # Assuming the current directory is the project directory
        api.upload_directory_with_structure(project['uuid'], directory_path, config)
        click.echo("Project structure and files uploaded successfully.")
    except FileNotFoundError:
        click.echo("Session key not found. Please run 'claude-pyrojects init' first.")
    except requests.exceptions.RequestException as e:
        click.echo(f"Failed to create project: {e}")


@main.command()
@click.option('-D', '--directory-path', default=os.getcwd(), type=click.Path(exists=True),
              help='Path to the project directory to update. Defaults to the current directory.')
def update(directory_path):
    """Update the project by clearing all files and re-uploading the directory."""
    try:
        # Load session key from claude_pyrojects.key
        with open('claude_pyrojects.key', 'r') as key_file:
            session_key = key_file.read().strip()

        api = ClaudeAPI(session_key)
        config = ConfigManager()
        project_config = config.load_config()

        if project_config:
            project_uuid = project_config['project_uuid']

            api.reinitialize_project_files(project_uuid, directory_path, config)
            click.echo("Project updated successfully.")
        else:
            click.echo("Project not initialized. Please run 'claude-pyrojects create' first.")
    except FileNotFoundError:
        click.echo("Session key not found. Please run 'claude-pyrojects init' first.")
    except Exception as e:
        click.echo(f"Failed to update project: {e}")


if __name__ == '__main__':
    main()
