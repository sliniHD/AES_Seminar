from crewai import Agent
from textwrap import dedent
from langchain.llms import OpenAI, Ollama
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from customTools import FileTools


# This is an example of how to define custom agents.
# You can define as many agents as you want.
# You can also define custom tasks in tasks.py
class CustomAgents:
    def __init__(self):
       # self.OpenAIGPT35 = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
       # self.Ollama = Ollama(model="openhermes")
       # self.OpenAIGPT4 = ChatOpenAI(model_name="gpt-4", temperature=0.7)
       self.GeminiPro = ChatGoogleGenerativeAI(
           model="gemini-2.0-flash",
           google_api_key="",  # oder via Umgebungsvariable
           temperature=0.7
       )
       self.GPT4O_Proxy = ChatOpenAI(
           model_name="gpt-4o",
           temperature=0.7,
           openai_api_base="http://188.245.32.59:4000/v1",
           openai_api_key="sk-"
       )
       self.GPT4OMINI_Proxy = ChatOpenAI(
           model_name="gpt-4o-mini",
           temperature=0.7,
           openai_api_base="http://188.245.32.59:4000/v1",
           openai_api_key="sk-"
       )

    def plannerAgent(self):
        return Agent(
            role="Senior Software Planner ",
            backstory=dedent(f"""
            You are a teamleader in high class tech company. Your job is it to lead a team of codes and assign task to them.
            You have also many experience in coding.
            """),
            goal=dedent(f"""Breakdown a Problem into coding tasks to fix the Problem"""),
            tools=[FileTools.read_file, FileTools.write_file, FileTools.git_add],
            allow_delegation=False,
            verbose=True,
            llm=self.GPT4O_Proxy,
        )

    def coderAgent(self):
        return Agent(
            role="Senior Software Engineer",
            backstory=dedent(f"""
            You are a Senior Software Engineer at a leading tech think tank.
            Your expertise in programming code. You do your best to produce perfect code
            """),
            goal=dedent(f"""
            Write the actual Code to fix the Problem to the codefiles. 
            Make sure the fix is minimal and only touches what's necessary to resolve the failing tests.
            """),
            tools=[FileTools.read_file, FileTools.write_file, FileTools.git_add],
            allow_delegation=False,
            verbose=True,
            llm=self.GPT4OMINI_Proxy,
        )

    def testAgent(self):
        return Agent(
            role="Software Quality Control Engineer",
            backstory=dedent(f"""
            You are a software engineer that specializes in checking code for errors. 
            You have an eye for detail and a knack for finding hidden bugs.
            You check for missing imports, variable declarations, mismatched brackets and syntax errors.
            You also check for security vulnerabilities, and logic errors"""),
            goal=dedent(f"""
            Ensure that the code does the job that it is supposed to do and fixes the Problem. 
            The fix will be verified by running the affected tests.
            """),
            tools=[FileTools.read_file, FileTools.write_file, FileTools.git_add],
            allow_delegation=False,
            verbose=True,
            llm=self.GPT4OMINI_Proxy,
        )
