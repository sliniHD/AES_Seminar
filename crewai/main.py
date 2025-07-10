import os
import asyncio
import json
import re

import requests
import subprocess

from crewai import Agent, Task, Crew, Process

from textwrap import dedent
from agents import CustomAgents
from tasks import CustomTasks


API_URL = "http://localhost:8081/task/index/"  # API endpoint for SWE-Bench-Lite
LOG_FILE = "results.log"

class FixCrew:
    def __init__(self, directory, issue):
        self.directory = directory
        self.issue = issue

    def run(self):
        # Define your custom agents and tasks in agents.py and tasks.py
        agents = CustomAgents()
        tasks = CustomTasks()

        # Define your custom agents and tasks here
        plannerAgent = agents.plannerAgent()
        coderAgent = agents.coderAgent()
        testAgent = agents.testAgent()

        # Custom tasks include agent name and variables as input
        planFix = tasks.planFix(
            plannerAgent,
            self.directory,
            self.issue,
        )

        implementFix = tasks.implementFix(
            coderAgent,
            self.directory,
            self.issue,
        )

        reviewFix = tasks.reviewFix(
            testAgent,
            self.directory,
            self.issue,
        )

        # Define your custom crew here
        crew = Crew(
            agents=[plannerAgent, coderAgent, testAgent],
            tasks=[planFix, implementFix, reviewFix],
            verbose=True,
        )

        result = crew.kickoff()
        return result


async def handle_task(index):
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

        fixCrew = FixCrew(repo_dir, issue)
        result = fixCrew.run()
        print(result)

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

    except Exception as e:
        os.chdir(start_dir)
        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"\n--- TESTCASE {index} ---\n")
            log.write(f"Error: {e}\n")
        print(f"Error in test case {index}: {e}")


# This is the main function that you will use to run your custom crew.
if __name__ == "__main__":
    print("## Welcome to Crew AI Template")
    print("-------------------------------")
    for i in range(1, 31):
        print(i)
        asyncio.run(handle_task(i))


