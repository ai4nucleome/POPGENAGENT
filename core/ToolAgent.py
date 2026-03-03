from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.prompts import ChatPromptTemplate
import bs4
from langchain_community.document_loaders import WebBaseLoader
from langchain.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_community.document_loaders.text import TextLoader
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain import hub
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.tools import ShellTool
import os

def Json_Format_Agent(json_string,api_key,base_url):
        os.environ['OPENAI_API_KEY'] = api_key
        # Create prompt template for JSON correction
        template = """
        You are an expert in JSON formatting.
        You cannot reply to anything other than json format.
        Do not reply to anything outside of json.
        You don't need to put json in the code block.
        You must strictly observe all the above rules.
        Do not delete any extra Spaces.
        Given the following potentially malformed JSON string, provide a correctly formatted JSON string:
        
        {json_string}
        
        Correct JSON:"""
        
        prompt = ChatPromptTemplate.from_template(template)
        
        # Use supported model
        llm = ChatOpenAI(model="claude-opus-4-1-20250805",base_url=base_url)
        parser = StrOutputParser()
        # Create LLMChain
        chain = prompt | llm|parser
        
        # Generate corrected JSON
        corrected_json = chain.invoke({"json_string": json_string})
        
        return corrected_json