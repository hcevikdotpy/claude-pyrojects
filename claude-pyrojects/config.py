import os
import json


class ConfigManager:
    def __init__(self, config_file='claude_pyrojects.config', ignore_file='claude_pyrojects.ignore'):
        self.config_file = config_file
        self.ignore_file = ignore_file

    def save_config(self, org_uuid, project_uuid, project_name):
        config = {
            'org_uuid': org_uuid,
            'project_uuid': project_uuid,
            'project_name': project_name,
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f)

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            return None

    def initialize_ignore_file(self):
        if not os.path.exists(self.ignore_file):
            default_content = ('ignore_folders=[".venv", ".idea", ".vscode"]\n'
                               'ignore_file_extensions=["pdf", "jpg", "png", "pyc"]\n'
                               'ignore_name_includes=["claude_pyrojects"]')
            with open(self.ignore_file, 'w') as f:
                f.write(default_content)
            print(f"{self.ignore_file} created with default values.")
        else:
            print(f"{self.ignore_file} already exists.")

    def load_ignore_rules(self):
        if os.path.exists(self.ignore_file):
            with open(self.ignore_file, 'r') as f:
                ignore_rules = {}
                exec(f.read(), {}, ignore_rules)
                return (
                    ignore_rules.get("ignore_folders", []),
                    ignore_rules.get("ignore_file_extensions", []),
                    ignore_rules.get("ignore_name_includes", [])
                )
        return [], [], []
