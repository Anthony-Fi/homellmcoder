import re
import logging

class BuilderAgent:
    """
    Minimal agent to extract and execute shell commands from Coder agent output (JSON or markdown/text).
    """
    def __init__(self, executor_func):
        """
        executor_func: function(command: str, cwd: str) -> result dict
        """
        self.executor_func = executor_func

    def extract_commands(self, agent_output: str) -> list:
        """
        Extracts shell commands from code blocks, JSON, and plain text.
        Returns a list of (command_line, cwd) tuples.
        """
        commands = []
        # 1. Extract from JSON run_command actions
        try:
            import json
            data = json.loads(agent_output)
            if isinstance(data, dict) and "actions" in data:
                for action in data["actions"]:
                    if action.get("action") == "run_command":
                        commands.append((action["command_line"], action.get("cwd", ".")))
        except Exception as e:
            logging.debug(f"BuilderAgent: Could not parse JSON for run_command actions: {e}")
        # 2. Extract from markdown/code blocks or plain text (lines starting with $ or common install keywords)
        pattern = re.compile(r'(^|\n)\s*(?:\$\s*)?((pip|composer|npm|yarn|php|python|django-admin|rails|npx|git|apt|brew|make|docker|sudo)[^\n\r]*)', re.IGNORECASE)
        for match in pattern.finditer(agent_output):
            cmd = match.group(2).strip()
            if cmd and not any(cmd == c[0] for c in commands):
                commands.append((cmd, "."))
        return commands

    def run_all(self, agent_output: str, cwd: str = ".") -> list:
        """
        Extract and execute all commands sequentially.
        Returns a list of result dicts.
        """
        commands = self.extract_commands(agent_output)
        results = []
        for cmd, cmd_cwd in commands:
            logging.info(f"BuilderAgent: Executing command: {cmd} (cwd={cmd_cwd})")
            result = self.executor_func(cmd, cmd_cwd or cwd)
            results.append({"command": cmd, "cwd": cmd_cwd, "result": result})
        return results
