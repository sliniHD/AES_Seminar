from agents import Agent, Runner, function_tool
import os
import subprocess
import asyncio
import json
import requests
from dotenv import load_dotenv
from agents import set_default_openai_client, set_default_openai_key, set_tracing_disabled
from openai import AsyncOpenAI


API_URL = "http://localhost:8081/task/index/"  # API endpoint for SWE-Bench-Lite
LOG_FILE = "results.log"

set_tracing_disabled(True)
set_default_openai_key("sk-")
custom_client = AsyncOpenAI(base_url="http://188.245.32.59:4000/v1", api_key="sk-")
set_default_openai_client(custom_client)

@function_tool()
def read_file(path: str) -> str:
    """Read the contents of a file.

        Args:
            path: The path to the file to read.
        """
    print("filereader:" + path)
    if not os.path.exists(path):
        return f"File not found: {path}"
    with open(path, "r") as f:
        return f.read()


@function_tool(name_override="write_file_tool",
               description_override="Write or overwrites a complete file with given contet. Make sure you give the complete path to file. If the file already exists the tool overwrites it, make sure that the file is completed")
def write_file(path: str, content: str) -> str:
    """Writes conent to a file. The given content will be replace the comlete file.

            Args:
                path: The path to the file to read.
                content: The content to write.
            """
    print("filewriter:" + path)
    with open(path, "w") as f:
        f.write(content)
    return f"File written successfully: {path}"


@function_tool()
def git_add(repo_path: str, file_path: str) -> str:
    """Adds all changed files to the git repository.

            Args:
                repo_path: The path to the repository.
            """
    print("git add")
    full_path = os.path.join(repo_path, file_path)
    if not os.path.exists(full_path):
        return f"file doesn't exist: {full_path}"
    try:
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
        return f"all files added to staging area successfully:"
    except subprocess.CalledProcessError as e:
        return f"error executing git add: {str(e)}"

@function_tool()
def find_file(directory: str, filename: str, recursive: bool = True) -> str:
    """
    Searches a file i a given directory and returns the complete path.

    Args:
          directory: The path to the directory where to search.
          filename: The name of the file to search.
          recursive: Whether to search for subdirectories.
    """
    print("findfile: " + directory + "/" + filename)
    if not os.path.isdir(directory):
        return f"Directory not found: {directory}"

    for root, dirs, files in os.walk(directory):
        if filename in files:
            print("ez:" + os.path.join(root, filename))
            return os.path.join(root, filename)
        if not recursive:
            break  # Nur Top-Level-Verzeichnis durchsuchen

    return f"File '{filename}' not found in {directory}"

coderAgent = Agent(
    name="Coder Agent",
    handoff_description="Used to produce code to fix problems in code.",
    instructions="Write the actual Code to fix the Problem to the codefiles. Make sure the fix is minimal and only touches what's necessary to resolve the failing tests.",
    tools=[write_file, read_file, find_file],
    model="gpt-4o-mini"
)

testerAgent = Agent(
    name="Tester Agent",
    handoff_description="Used to check whether written code is valid.",
    instructions=" Ensure that the code does the job that it is supposed to do and fixes the Problem.",
    tools=[read_file, write_file, find_file],
    model="gpt-4o-mini"
)

plannerAgent = Agent(
    name="Plan Agent",
    instructions="You are the teamleader of a team of developers. You get probles taht you have to fix. Read in broken files with the read_file_tool. Breakdown a given Problem into coding tasks to fix it. After making a plan hand the coding tasks to the Coder Agent. You can verify his work using the Tester Agent. If there are furthermore errors hand the task again to the Coder Agent. When all the work is done use the git add tool to the changed files.",
    handoffs=[coderAgent, testerAgent],
    tools=[git_add,read_file, find_file],
    model="gpt-4o-mini"
)

async def run_task(index):
    api_url = f"{API_URL}{index}"
    print(f"Fetching test case {index} from {api_url}...")
    repo_dir = os.path.join("repos", f"repo_{index}")  # Use unique repo directory per task
    start_dir = os.getcwd()  # Remember original working directory

    try:
        response = requests.get(api_url)
        if response.status_code != 200:
            raise Exception(f"Invalid response: {response.status_code}")

        testcase = response.json()
        issue = testcase["Problem_statement"]
        git_clone = testcase["git_clone"]
        fail_tests = json.loads(testcase.get("FAIL_TO_PASS", "[]"))
        pass_tests = json.loads(testcase.get("PASS_TO_PASS", "[]"))
        instance_id = testcase["instance_id"]

        # Extract repo URL and commit hash
        parts = git_clone.split("&&")
        clone_part = parts[0].strip()
        checkout_part = parts[-1].strip() if len(parts) > 1 else None

        repo_url = clone_part.split()[2]

        print(f"Cloning repository {repo_url} into {repo_dir}...")
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        subprocess.run(["git", "clone", repo_url, repo_dir], check=True, env=env)

        if checkout_part:
            commit_hash = checkout_part.split()[-1]
            print(f"Checking out commit: {commit_hash}")
            subprocess.run(["git", "checkout", commit_hash], cwd=repo_dir, check=True, env=env)

        print("HIER: " + issue)
        result = await Runner.run(plannerAgent,
                          f"Work in the directory: repo_{index}. This is a Git repository. You can use the `read_file_tool` to read it, and `write_file_tool` to change it. Your goal is to fix the problem described below. The fix will be verified by running the affected tests. \n Problem description: \n {issue}",
                                  max_turns=50)
        print(result.final_output)

        print(f"Calling SWE-Bench REST service with repo: {repo_dir}")
        test_payload = {
            "instance_id": instance_id,
            "repoDir": f"/repos/repo_{index}",  # mount with docker
            "FAIL_TO_PASS": fail_tests,
            "PASS_TO_PASS": pass_tests
        }
        res = requests.post("http://localhost:8082/test", json=test_payload)
        res.raise_for_status()
        result_raw = res.json().get("harnessOutput", "{}")
        result_json = json.loads(result_raw)
        if not result_json:
            raise ValueError("No data in harnessOutput – possible evaluation error or empty result")
        instance_id = next(iter(result_json))
        tests_status = result_json[instance_id]["tests_status"]
        fail_pass_results = tests_status["FAIL_TO_PASS"]
        fail_pass_total = len(fail_pass_results["success"]) + len(fail_pass_results["failure"])
        fail_pass_passed = len(fail_pass_results["success"])
        pass_pass_results = tests_status["PASS_TO_PASS"]
        pass_pass_total = len(pass_pass_results["success"]) + len(pass_pass_results["failure"])
        pass_pass_passed = len(pass_pass_results["success"])

        # Log results
        os.chdir(start_dir)
        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"\n--- TESTCASE {index} ---\n")
            log.write(f"FAIL_TO_PASS passed: {fail_pass_passed}/{fail_pass_total}\n")
            log.write(f"PASS_TO_PASS passed: {pass_pass_passed}/{pass_pass_total}\n")
        print(f"Test case {index} completed and logged.")


    except Exception as e:
        os.chdir(start_dir)
        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"\n--- TESTCASE {index} ---\n")
            log.write(f"Error: {e}\n")
        print(f"Error in test case {index}: {e}")



if __name__ == "__main__":
    for i in range(24, 31):
        print(i)
        asyncio.run(run_task(i))
