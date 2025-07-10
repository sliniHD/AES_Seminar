# To know more about the Task class, visit: https://docs.crewai.com/concepts/tasks
from crewai import Task
from textwrap import dedent


class CustomTasks:
    def __tip_section(self):
        return "If you do your BEST WORK and fix the Problem, I'll give you a $10,000 commission!"

    def fixIssue(self, agent, directory, issue):
        return Task(
            description=dedent(
            f"""
            *Task* Fix the problem in the code project described by the issue below.
            *Description* You are working in a a git repository in the directory described in the next section. 
            Your goal is to fix the problem described below.
            All code changes must be saved to the files, so they appear in `git diff`.
            The fix will be verified by running the affected tests.
            
            **Parameters**
            - issue: {issue}
            - directory: {directory}
            {self.__tip_section()}
            """
            ),
            expected_output="The expected output of the task",
            agent=agent,
        )


    def planFix(self, agent, directory, issue):
        return Task(
            description=dedent(
                f"""
            *Task* Break down the following problem into concrete, feasible subtasks for developers.
            *Description* You are working in a Git project in the directory: `{directory}`. 
            Your task is to analyze the following problem and break it down into individual work steps for developers.

            **Parameters**
            - issue: {issue}
            - directory: {directory}

            {self.__tip_section()}
            """
            ),
            expected_output="A clear list of work steps or files/code areas to be changed.",
            agent=agent,
        )

    def implementFix(self, agent, directory, issue):
        return Task(
            description=dedent(
                f"""
            *Task* Implement the fix in the code based on the task scheduling.
            *Description* Work in the Git directory `{directory}`. The problem is described as follows: 
            `{issue}`

            You will receive a list of tasks that you need to implement. Change the code so that the error is fixed.
            Write the changes directly to the files so that they are traceable via `git diff`.

            **Notes**
            - The fix should be minimally invasive.
            - No unnecessary formatting or restructuring.
            - All changes must be syntactically correct and testable.
            - The changed files musst be added to git via git add

            {self.__tip_section()}
            """
            ),
            expected_output="Code changes in the relevant files that solve the problem.",
            agent=agent,
        )

    def reviewFix(self, agent, directory, issue):
        return Task(
            description=dedent(
                f"""
            *Task* Check and test the fix.
            *Description* You check the implemented code fix in the project directory `{directory}`. 
            Make sure that:
            - The fix is correct.
            - No new bugs have been introduced.
            - All affected tests are successful.
            - All files are added in the git repository. 

            You can understand the bug as follows: 
            `{issue}`

            If possible, run automated tests (`pytest` or other relevant frameworks) and provide feedback.

            {self.__tip_section()}
            """
            ),
            expected_output="An assessment of the quality of the fix and any feedback on remaining problems.",
            agent=agent,
        )


