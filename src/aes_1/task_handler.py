# task_handler.py
import os
import json
import re
import requests
import subprocess

from crewai import Agent, Crew, Task
from crewai_tools import DirectoryReadTool, FileReadTool, FileWriteTool

API_URL = "http://localhost:8081/task/index/"
LOG_FILE = "results.log"

async def handle_task(index):
    api_url = f"{API_URL}{index}"
    print(f"Fetching test case {index} from {api_url}...")
    repo_dir = os.path.join("repos", f"repo_{index}")
    start_dir = os.getcwd()

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        testcase = response.json()

        prompt = testcase["Problem_statement"]
        git_clone = testcase["git_clone"]
        fail_tests = json.loads(testcase.get("FAIL_TO_PASS", "[]"))
        pass_tests = json.loads(testcase.get("PASS_TO_PASS", "[]"))
        instance_id = testcase["instance_id"]

        # Repo vorbereiten
        parts = git_clone.split("&&")
        repo_url = parts[0].split()[2]
        commit_hash = parts[1].split()[-1] if len(parts) > 1 else None

        subprocess.run(["git", "clone", repo_url, repo_dir], check=True)
        if commit_hash:
            subprocess.run(["git", "checkout", commit_hash], cwd=repo_dir, check=True)

        # CrewAI Agententeam definieren
        full_prompt = (
            f"Problem description:\n{prompt}\n"
            f"Arbeite im Ordner repo_{index}. Verwende git diff, speichere Änderungen und behebe den Bug so minimal wie möglich."
        )

        tools = [TerminalTool(cwd=repo_dir), FileTool(root_dir=repo_dir)]

        planner = Agent(
            role="Planner",
            goal="Analysiere das Problem und entwickle einen Bugfix-Plan.",
            backstory="Softwarearchitekt mit viel Erfahrung in Debugging.",
            tools=[],
            verbose=True
        )

        coder = Agent(
            role="Coder",
            goal="Implementiere den Fix im Code.",
            backstory="Pragmatischer Entwickler mit Fokus auf Korrektheit.",
            tools=tools,
            verbose=True
        )

        tester = Agent(
            role="Tester",
            goal="Führe Tests aus und überprüfe, ob der Bug behoben wurde.",
            backstory="Qualitätsprüfer mit Erfahrung in Testautomatisierung.",
            tools=[TerminalTool(cwd=repo_dir)],
            verbose=True
        )

        task = Task(
            description=full_prompt,
            expected_output="Bugfix und erfolgreiche Tests.",
            agents=[planner, coder, tester]
        )

        crew = Crew(agents=[planner, coder, tester], tasks=[task], verbose=True)
        result = crew.kickoff()
        print(result)

        # Ergebnis evaluieren
        payload = {
            "instance_id": instance_id,
            "repoDir": f"/repos/repo_{index}",
            "FAIL_TO_PASS": fail_tests,
            "PASS_TO_PASS": pass_tests
        }
        res = requests.post("http://localhost:8082/test", json=payload)
        res.raise_for_status()
        result_json = json.loads(res.json().get("harnessOutput", "{}"))

        instance_result = result_json.get(instance_id, {})
        fail_pass = instance_result.get("tests_status", {}).get("FAIL_TO_PASS", {})
        pass_pass = instance_result.get("tests_status", {}).get("PASS_TO_PASS", {})

        log_results(index, fail_pass, pass_pass)

    except Exception as e:
        os.chdir(start_dir)
        with open(LOG_FILE, "a") as log:
            log.write(f"\n--- TESTCASE {index} ---\n")
            log.write(f"Error: {e}\n")
        print(f"Error in test case {index}: {e}")


def log_results(index, fail_pass, pass_pass):
    with open(LOG_FILE, "a") as log:
        log.write(f"\n--- TESTCASE {index} ---\n")
        log.write(f"FAIL_TO_PASS passed: {len(fail_pass.get('success', []))}/"
                  f"{len(fail_pass.get('success', []) + fail_pass.get('failure', []))}\n")
        log.write(f"PASS_TO_PASS passed: {len(pass_pass.get('success', []))}/"
                  f"{len(pass_pass.get('success', []) + pass_pass.get('failure', []))}\n")
