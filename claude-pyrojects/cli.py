import click
import os
import requests.exceptions
from datetime import datetime
from pathlib import Path
import sys
from .api import ClaudeAPI
from .config import ConfigManager

# ASCII Art Banner
BANNER = """
╔═══════════════════════════════════════════╗
║     Claude-Pyrojects Manager v0.2.0       ║
║   Upload your projects to Claude.ai 🚀    ║
╚═══════════════════════════════════════════╝
"""


def print_banner():
    """Print the application banner"""
    click.echo(click.style(BANNER, fg='cyan', bold=True))


def format_file_size(size):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}TB"


def get_directory_stats(directory_path, ignore_folders, ignore_extensions, ignore_name_includes):
    """Get statistics about the directory"""
    total_files = 0
    total_size = 0

    for root, dirs, files in os.walk(directory_path):
        # Remove ignored directories from dirs list to prevent os.walk from descending into them
        dirs[:] = [d for d in dirs if d not in ignore_folders]

        for file in files:
            if not any(file.endswith(ext) for ext in ignore_extensions) and \
                    not any(substring in file for substring in ignore_name_includes):
                total_files += 1
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                except:
                    pass

    return total_files, total_size


@click.group()
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.option('-q', '--quiet', is_flag=True, help='Minimal output')
@click.pass_context
def main(ctx, verbose, quiet):
    """Claude-Pyrojects: Seamlessly upload your projects to Claude.ai"""
    ctx.ensure_object(dict)
    ctx.obj['VERBOSE'] = verbose
    ctx.obj['QUIET'] = quiet

    if not quiet:
        print_banner()


@main.command()
@click.option('-K', '--session-key', required=True, help='Session key for Claude API.')
@click.pass_context
def init(ctx, session_key):
    """🔧 Initialize the Claude project by creating ignore and key files."""
    if not ctx.obj['QUIET']:
        click.echo(click.style("\n🔧 Initializing Claude-Pyrojects...", fg='cyan', bold=True))

    config = ConfigManager()

    # Initialize the ignore file
    config.initialize_ignore_file()
    click.echo(click.style("✅ Created ignore file", fg='green'))

    # Save the session key in claude_pyrojects.key file
    with open('claude_pyrojects.key', 'w') as key_file:
        key_file.write(session_key)
    click.echo(click.style("✅ Session key saved", fg='green'))

    # Create manifest file
    manifest_path = 'claude_pyrojects.manifest'
    if not os.path.exists(manifest_path):
        with open(manifest_path, 'w') as f:
            f.write('{"files": {}, "last_sync": null}')
        click.echo(click.style("✅ Created manifest file", fg='green'))

    click.echo(click.style("\n🎉 Initialization complete! You can now create a project with 'claude-pyrojects create'",
                           fg='green', bold=True))


@main.command()
@click.option('-N', '--project-name', required=True, help='Name of the new project.')
@click.option('-d', '--description', default='', help='Project description.')
@click.pass_context
def create(ctx, project_name, description):
    """🚀 Create a new Claude project and upload the project structure."""
    try:
        # Load session key from claude_pyrojects.key
        with open('claude_pyrojects.key', 'r') as key_file:
            session_key = key_file.read().strip()

        if not ctx.obj['QUIET']:
            click.echo(click.style(f"\n🚀 Creating project '{project_name}'...", fg='cyan', bold=True))

        api = ClaudeAPI(session_key)
        config = ConfigManager()

        # Get directory statistics
        directory_path = os.getcwd()
        ignore_folders, ignore_extensions, ignore_name_includes = config.load_ignore_rules()
        total_files, total_size = get_directory_stats(directory_path, ignore_folders, ignore_extensions,
                                                      ignore_name_includes)

        if not ctx.obj['QUIET']:
            click.echo(click.style(f"\n📊 Project Statistics:", fg='yellow'))
            click.echo(f"   📁 Files to upload: {total_files}")
            click.echo(f"   💾 Total size: {format_file_size(total_size)}")

            if not click.confirm(click.style("\n❓ Do you want to proceed?", fg='yellow')):
                click.echo(click.style("❌ Operation cancelled.", fg='red'))
                return

        # Create the project
        project = api.create_project(
            api.organization_id,
            project_name,
            is_private=True,
            description=description
        )

        config.save_config(api.organization_id, project['uuid'], project['name'])
        click.echo(click.style(f"✅ Project created successfully!", fg='green'))
        click.echo(f"   🆔 UUID: {project['uuid']}")

        # Upload files
        api.upload_directory_with_structure(project['uuid'], directory_path, config)

        # Initialize the manifest after first upload
        _, current_files = api.scan_directory_changes(
            directory_path, ignore_folders, ignore_extensions, ignore_name_includes
        )
        manifest = api.load_manifest()
        manifest['files'] = current_files
        api.save_manifest(manifest)

        click.echo(click.style("\n🎉 Project creation complete! Your files are now available in Claude.", fg='green',
                               bold=True))

    except FileNotFoundError:
        click.echo(click.style("❌ Session key not found. Please run 'claude-pyrojects init' first.", fg='red'))
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        click.echo(click.style(f"❌ Failed to create project: {e}", fg='red'))
        sys.exit(1)


@main.command()
@click.option('-D', '--directory-path', default=os.getcwd(), type=click.Path(exists=True),
              help='Path to the project directory to update. Defaults to the current directory.')
@click.option('-f', '--force', is_flag=True, help='Force full re-upload instead of incremental update.')
@click.option('-y', '--yes', is_flag=True, help='Skip confirmation prompts.')
@click.pass_context
def update(ctx, directory_path, force, yes):
    """🔄 Update the project by uploading only changed files (or force full re-upload)."""
    try:
        # Load session key from claude_pyrojects.key
        with open('claude_pyrojects.key', 'r') as key_file:
            session_key = key_file.read().strip()

        api = ClaudeAPI(session_key)
        config = ConfigManager()
        project_config = config.load_config()

        if project_config:
            project_uuid = project_config['project_uuid']
            project_name = project_config.get('project_name', 'Unknown')

            if not ctx.obj['QUIET']:
                click.echo(click.style(f"\n🔄 Updating project '{project_name}'...", fg='cyan', bold=True))

            if force or not os.path.exists('claude_pyrojects.manifest'):
                # Full re-upload
                if not yes and not ctx.obj['QUIET']:
                    click.echo(
                        click.style("\n⚠️  This will delete all existing files and re-upload everything.", fg='yellow'))
                    if not click.confirm(click.style("❓ Are you sure you want to continue?", fg='yellow')):
                        click.echo(click.style("❌ Operation cancelled.", fg='red'))
                        return

                api.reinitialize_project_files(project_uuid, directory_path, config)

                # Initialize manifest after full upload
                ignore_folders, ignore_extensions, ignore_name_includes = config.load_ignore_rules()
                _, current_files = api.scan_directory_changes(
                    directory_path, ignore_folders, ignore_extensions, ignore_name_includes
                )
                manifest = api.load_manifest()
                manifest['files'] = current_files
                api.save_manifest(manifest)

                click.echo(click.style("\n✅ Project fully updated!", fg='green', bold=True))
            else:
                # Incremental update
                api.incremental_update_project(project_uuid, directory_path, config)

        else:
            click.echo(click.style("❌ Project not initialized. Please run 'claude-pyrojects create' first.", fg='red'))
            sys.exit(1)

    except FileNotFoundError:
        click.echo(click.style("❌ Session key not found. Please run 'claude-pyrojects init' first.", fg='red'))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"❌ Failed to update project: {e}", fg='red'))
        if ctx.obj['VERBOSE']:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option('-D', '--directory-path', default=os.getcwd(), type=click.Path(exists=True),
              help='Path to the project directory. Defaults to the current directory.')
@click.option('--detailed', is_flag=True, help='Show detailed file lists.')
@click.pass_context
def status(ctx, directory_path, detailed):
    """📊 Show what changes would be uploaded in the next update."""
    try:
        # Load session key to initialize API (needed for manifest loading)
        with open('claude_pyrojects.key', 'r') as key_file:
            session_key = key_file.read().strip()

        api = ClaudeAPI(session_key)
        config = ConfigManager()

        # Load project config to show project info
        project_config = config.load_config()

        if not ctx.obj['QUIET']:
            click.echo(click.style("\n📊 Project Status", fg='cyan', bold=True))
            if project_config:
                click.echo(f"   📦 Project: {project_config.get('project_name', 'Unknown')}")
                click.echo(f"   🆔 UUID: {project_config.get('project_uuid', 'Unknown')[:8]}...")

        if not os.path.exists('claude_pyrojects.manifest'):
            click.echo(click.style("\n❌ No sync history found. Run 'create' or 'update' first.", fg='red'))
            return

        changes, last_sync = api.get_status(directory_path, config)

        total_changes = len(changes['added']) + len(changes['modified']) + len(changes['deleted'])

        # Last sync information
        if last_sync:
            sync_time = datetime.fromisoformat(last_sync)
            time_ago = datetime.now() - sync_time

            if time_ago.days > 0:
                time_str = f"{time_ago.days} days ago"
            elif time_ago.seconds > 3600:
                time_str = f"{time_ago.seconds // 3600} hours ago"
            elif time_ago.seconds > 60:
                time_str = f"{time_ago.seconds // 60} minutes ago"
            else:
                time_str = "just now"

            click.echo(f"   ⏰ Last sync: {sync_time.strftime('%Y-%m-%d %H:%M:%S')} ({time_str})")

        if total_changes == 0:
            click.echo(click.style("\n✨ No changes detected. Project is up to date!", fg='green'))
        else:
            click.echo(click.style(f"\n📝 Pending changes: {total_changes} total", fg='yellow'))

            if changes['added']:
                click.echo(click.style(f"\n➕ Files to be added ({len(changes['added'])}):", fg='green'))
                files_to_show = changes['added'] if detailed else changes['added'][:5]
                for f in files_to_show:
                    click.echo(f"   + {f}")
                if not detailed and len(changes['added']) > 5:
                    click.echo(click.style(f"   ... and {len(changes['added']) - 5} more", fg='dim'))

            if changes['modified']:
                click.echo(click.style(f"\n✏️  Files to be updated ({len(changes['modified'])}):", fg='yellow'))
                files_to_show = changes['modified'] if detailed else changes['modified'][:5]
                for f in files_to_show:
                    click.echo(f"   * {f}")
                if not detailed and len(changes['modified']) > 5:
                    click.echo(click.style(f"   ... and {len(changes['modified']) - 5} more", fg='dim'))

            if changes['deleted']:
                click.echo(click.style(f"\n➖ Files to be deleted ({len(changes['deleted'])}):", fg='red'))
                files_to_show = changes['deleted'] if detailed else changes['deleted'][:5]
                for f in files_to_show:
                    click.echo(f"   - {f}")
                if not detailed and len(changes['deleted']) > 5:
                    click.echo(click.style(f"   ... and {len(changes['deleted']) - 5} more", fg='dim'))

            click.echo(click.style(f"\n💡 Run 'claude-pyrojects update' to sync these changes.", fg='cyan'))

    except FileNotFoundError:
        click.echo(click.style("❌ Session key not found. Please run 'claude-pyrojects init' first.", fg='red'))
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"❌ Error checking status: {e}", fg='red'))
        if ctx.obj['VERBOSE']:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.pass_context
def info(ctx):
    """ℹ️  Show information about the current project configuration."""
    try:
        config = ConfigManager()
        project_config = config.load_config()

        click.echo(click.style("\nℹ️  Claude-Pyrojects Configuration", fg='cyan', bold=True))

        # Check for key file
        if os.path.exists('claude_pyrojects.key'):
            click.echo(click.style("✅ Session key: Found", fg='green'))
        else:
            click.echo(click.style("❌ Session key: Not found", fg='red'))

        # Check for ignore file
        if os.path.exists('claude_pyrojects.ignore'):
            click.echo(click.style("✅ Ignore file: Found", fg='green'))
            ignore_folders, ignore_extensions, ignore_name_includes = config.load_ignore_rules()
            if ctx.obj['VERBOSE']:
                click.echo(f"   Ignored folders: {', '.join(ignore_folders)}")
                click.echo(f"   Ignored extensions: {', '.join(ignore_extensions)}")
                click.echo(f"   Ignored names: {', '.join(ignore_name_includes)}")
        else:
            click.echo(click.style("❌ Ignore file: Not found", fg='red'))

        # Check for manifest
        if os.path.exists('claude_pyrojects.manifest'):
            click.echo(click.style("✅ Manifest file: Found", fg='green'))
        else:
            click.echo(click.style("⚠️  Manifest file: Not found (will be created on first sync)", fg='yellow'))

        # Project info
        if project_config:
            click.echo(click.style("\n📦 Project Information:", fg='cyan'))
            click.echo(f"   Name: {project_config.get('project_name', 'Unknown')}")
            click.echo(f"   UUID: {project_config.get('project_uuid', 'Unknown')}")
            click.echo(f"   Organization: {project_config.get('org_uuid', 'Unknown')[:8]}...")
        else:
            click.echo(
                click.style("\n⚠️  No project configured yet. Run 'claude-pyrojects create' to set up a project.",
                            fg='yellow'))

    except Exception as e:
        click.echo(click.style(f"❌ Error getting info: {e}", fg='red'))
        sys.exit(1)


if __name__ == '__main__':
    main(obj={})