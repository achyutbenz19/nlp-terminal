from typing import Type
from langchain_community.tools.shell.tool import ShellInput
import platform
import threading
import subprocess
import time
import queue
from langchain_core.tools import BaseTool
from pydantic import BaseModel
task_output_queues = {}
background_tasks = {}


def _get_platform() -> str:
    """Get platform."""
    system = platform.system()
    if system == "Darwin":
        return "MacOS"
    return system

class AsyncShellTool(BaseTool):
    """Tool to run shell commands."""

    name: str = "long running terminal"
    """Name of tool."""

    description: str = f"Run long running shell commands on this {_get_platform()} machine. Use this to run commands that take a long time/infinite to complete."
    """Description of tool."""

    args_schema: Type[BaseModel] = ShellInput

    ask_human_input: bool = False
    """
    If True, prompts the user for confirmation (y/n) before executing 
    a command generated by the language model in the bash shell.
    """

    def __init__(self):
        pass

    def _run(self, command: str) -> str:
        output_queue = queue.Queue()
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # Start capturing output in a separate thread
        threading.Thread(target=self._capture_output, args=(process, output_queue), daemon=True).start()

        # Wait for 1 second to capture initial output
        time.sleep(2)

        # Collect output after 1 second
        initial_output = self._collect_output(output_queue)

        if process.poll() is None:  # If the task is still running
            # Handle as a background task
            background_tasks[process.pid] = process
            task_output_queues[process.pid] = output_queue
            return initial_output + "\n[Task continues running in the background]"
        else:
            # Task completed within 1 second
            return initial_output

    def _capture_output(self, process, output_queue):
        for line in iter(process.stdout.readline, ''):
            output_queue.put(line)
        process.stdout.close()

    def _collect_output(self, output_queue):
        output = []
        while not output_queue.empty():
            output.append(output_queue.get())
        return ''.join(output)

    def get_background_task_output(self, pid):
        # Method to retrieve output for a specific background task
        if pid in task_output_queues:
            return self._collect_output(task_output_queues[pid])
        else:
            return "No background task with the specified PID."

# Example usage
if __name__ == "__main__":
    tool = AsyncShellTool()
    print(tool._run("top"))
