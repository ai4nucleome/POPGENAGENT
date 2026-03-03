"""
GenAgent - Population Genetics Analysis Intelligent Agent Framework
====================================================================
This module provides an intelligent agent framework for automating
population genetics analysis workflows.
Main features include: plan generation, task execution, debugging, and knowledge base management.

Optimized version v2.0 - Improved code structure, error handling, and execution efficiency
"""

import os
import subprocess
import json
import re
import logging
from datetime import datetime
import uuid
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain import hub
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader, TextLoader, PyPDFLoader
from langchain_chroma import Chroma
from langchain_community.tools import ShellTool

from .prompts import PLAN_PROMPT, PLAN_EXAMPLES, TASK_PROMPT, TASK_EXAMPLES, DEBUG_EXAMPLES, DEBUG_PROMPT
from .utils import normalize_keys, load_tool_links
from .ToolAgent import Json_Format_Agent

from langchain_community.llms import Ollama
from .CheckAgent import CheckAgent
from .ollama import OllamaEmbeddings

from mem0 import Memory
from backend.utils import update_execute_agent_status, update_execute_agent_status_and_attempt, update_execute_agent_stage

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - [%(funcName)s] %(message)s'
)
logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Task execution status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class StepResult:
    """Step execution result"""
    step_number: int
    success: bool
    output_files: List[str]
    error_message: Optional[str] = None
    retry_count: int = 0


class StopTaskException(Exception):
    """Exception raised when the user requests to stop a task"""
    pass


class GenAgent:
    """
    Population Genetics Analysis Intelligent Agent
    
    Main features:
    - Automatically generate analysis plans
    - Execute analysis tasks
    - Intelligent debugging and error handling
    - Knowledge base management and retrieval
    
    Attributes:
        api_key: OpenAI API key
        base_url: API base URL
        model: Model name to use
        executor: Whether to execute scripts
        repeat: Maximum retry count
    """
    
    # Class-level constants
    DEFAULT_MODEL = "claude-opus-4-1-20250805-thinking"
    TOOL_MODEL = "claude-opus-4-1-20250805"
    EMBEDDING_MODEL = "text-embedding-3-large"
    MAX_OUTPUT_LENGTH = 5000
    MAX_EMBEDDING_TOKENS = 30000
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        Model: str = DEFAULT_MODEL,
        excutor: bool = False,
        Repeat: int = 5,
        tools_dir: str = "tools",
        output_dir: str = './output',
        id: str = '001',
        chroma_db_dir: str = './chroma_db'
    ):
        """
        Initialize GenAgent
        
        Args:
            api_key: OpenAI API key
            base_url: API base URL
            Model: Model name to use
            excutor: Whether to execute generated scripts
            Repeat: Maximum retry count on task failure
            tools_dir: Tool configuration file directory
            output_dir: Output file directory
            id: Task ID ('000' means auto-generate a new ID)
            chroma_db_dir: Chroma vector database persistence directory
        """
        # Set environment variables
        os.environ['USER_AGENT'] = 'GenAgent/2.0'
        os.environ['OPENAI_API_KEY'] = api_key
        
        # Basic configuration
        self.api_key = api_key
        self.base_url = base_url
        self.model = Model
        self.tools_dir = tools_dir
        self.doc_dir = "knowledge"
        self.excutor = excutor
        self.repeat = Repeat
        self.output_dir = output_dir
        self.chroma_db_dir = chroma_db_dir
        
        # State management
        self.stop_flag = False
        self.current_step = 0
        self.execution_status = ExecutionStatus.PENDING
        
        # Initialize task ID
        self.id = self._initialize_task_id(id)
        
        # Load tool configuration
        tools_info, self.tool_names = self._load_tools_from_files()
        
        # Initialize prompts
        self._initialize_prompts()
        
        # Initialize agents
        self._initialize_agents()
        
        # Initialize vector stores
        self._initialize_vector_stores()
        
        # Initialize CheckAgent
        self.check_agent = CheckAgent(
            api_key=api_key, 
            base_url=base_url, 
            model=self.TOOL_MODEL
        )
        
        logger.info(f"GenAgent initialization complete, task ID: {self.id}")
    
    def _initialize_task_id(self, id: str) -> str:
        """Initialize task ID"""
        if id == '000':
            new_id = self._generate_new_id()
            logger.info(f"Generated new task ID: {new_id}")
            return new_id
        else:
            # Set temporary id first for loading files
            self.id = id
            self._load_existing_files()
            return id
    
    def _initialize_prompts(self):
        """Initialize prompt templates"""
        self.PLAN_prompt = PLAN_PROMPT.format(tool_names=self.tool_names)
        self.TASK_prompt = TASK_PROMPT.format(tool_names=self.tool_names)
        self.DEBUG_prompt = DEBUG_PROMPT.format(tool_names=self.tool_names)
        
        self.PLAN_examples = PLAN_EXAMPLES
        self.TASK_examples = TASK_EXAMPLES
        self.DEBUG_examples = DEBUG_EXAMPLES
    
    def _initialize_agents(self):
        """Initialize all agents"""
        self.DEBUG_agent = self._create_agent(self.DEBUG_prompt, self.DEBUG_examples)
        self.TASK_agent = self._create_agent(self.TASK_prompt, self.TASK_examples)
        self.PLAN_agent = self._create_agent(self.PLAN_prompt, self.PLAN_examples)
    
    def _initialize_vector_stores(self):
        """Initialize vector stores"""
        self.embeddings = OpenAIEmbeddings(
            model=self.EMBEDDING_MODEL, 
            base_url=self.base_url
        )
        
        # Collection names
        self.collection1_name = "popgen_collection1"  # Plan knowledge base
        self.collection2_name = "popgen_collection2"  # Task knowledge base
        
        # Initialize Chroma vector stores
        self.vectorstore = Chroma(
            collection_name=self.collection1_name,
            embedding_function=self.embeddings,
            persist_directory=os.path.join(self.chroma_db_dir, "collection1")
        )
        self.vectorstore_tool = Chroma(
            collection_name=self.collection2_name,
            embedding_function=self.embeddings,
            persist_directory=os.path.join(self.chroma_db_dir, "collection2")
        )
        
        # RAG retrieval configuration
        self.plan_rag_k = 3  # Plan knowledge base retrieval count (reduced to avoid always retrieving full workflows)
        self.task_rag_k = 6  # Task knowledge base retrieval count
        
        # Plan workflow type keyword mapping (for precise matching of focused workflows)
        self.plan_workflow_keywords = {
            'qc_only': ['quality control only', 'qc only', 'filtering only', 'just qc', 'just filtering', 'only qc', 'only filtering'],
            'pca_only': ['pca only', 'pca analysis only', 'just pca', 'only pca', 'principal component only'],
            'admixture_only': ['admixture only', 'just admixture', 'only admixture', 'admixture analysis only'],
            'diversity_stats': ['diversity only', 'roh only', 'heterozygosity only', 'ld decay only', 'genetic diversity only', 'just roh', 'just diversity'],
            'treemix_fstats': ['treemix only', 'f-statistics only', 'just treemix', 'treemix and f-statistics', 'treemix and admixtools'],
            'kinship_only': ['kinship only', 'king only', 'relatedness only', 'just kinship', 'remove related only'],
        }
        
        # Task type keyword mapping
        self.task_type_keywords = {
            'viz_pca': ['pca', 'principal component', 'pc1', 'pc2', 'evec', 'eval', 'eigenvalue', 'scatter plot'],
            'viz_admixture': ['admixture', 'ancestry', 'k value', 'structure', '.Q', 'bar plot', 'stacked'],
            'viz_roh': ['roh', 'runs of homozygosity', 'homozygosity', '.hom', 'inbreeding'],
            'viz_het': ['heterozygosity', 'het', 'inbreeding coefficient', 'F coefficient', '.het'],
            'viz_lddecay': ['ld decay', 'linkage disequilibrium', 'ld curve', 'r2'],
            'viz_treemix': ['treemix', 'migration', 'population tree', 'phylogenetic', '.treeout'],
            'smartpca': ['smartpca', 'eigenstrat', 'convertf', 'geno', 'snp', 'ind'],
            'admixture_run': ['admixture', 'cv error', 'cross validation', 'k='],
            'plink_qc': ['quality control', 'filtering', 'maf', 'geno', 'mind', 'biallelic'],
            'king': ['king', 'kinship', 'related', 'kin0', 'relatedness'],
            'treemix_run': ['treemix', 'migration edge', 'bootstrap', 'frq.gz']
        }
        
        # Load knowledge data
        self.Load_PLAN_RAG()
        self.Load_Tool_RAG()

    def _generate_new_id(self):
        existing_ids = []
        for file_name in os.listdir(self.output_dir):
            match = re.match(r'^(\d{3})_', file_name)
            if match:
                existing_ids.append(int(match.group(1)))

        new_id = min(set(range(1, max(existing_ids, default=0) + 2)) - set(existing_ids))
        return f'{new_id:03d}'

    def _load_existing_files(self):
        # Load PLAN and step files for the specified ID
        plan_file = os.path.join(self.output_dir, f'{self.id}_PLAN.json')
        if os.path.exists(plan_file):
            self.plan_data = self.load_progress(self.output_dir, f'{self.id}_PLAN.json')
        else:
            print(f"No PLAN file found for ID: {self.id}")

        # Additional logic can be added here to load other needed files

    def check_stop(self):
        """Check if the task needs to be stopped"""
        if self.stop_flag:
            print(f"Task {self.id} is being stopped by user request.")
            try:
                update_execute_agent_stage(self.id, "PAUSED")
            except Exception as e:
                print(f"Error updating stage for task {self.id}: {e}")
            raise StopTaskException(f"Task {self.id} was stopped by user request.")

    def stop(self):
        """Set the stop flag to request task stop"""
        self.stop_flag = True
        print(f"Stop flag set for task {self.id}")
    
    def is_stopped(self):
        """Check if the task has been requested to stop"""
        return self.stop_flag

    def _load_tools_from_files(self):
        tool_files = [f for f in os.listdir(self.tools_dir) if f.endswith(".config")]
        tool_strings = []
        tool_names = []

        for file in tool_files:
            tool_name = file.split(".")[0]
            tool_names.append(tool_name)

            with open(os.path.join(self.tools_dir, file), "r", encoding='utf-8') as f:
                tool_description = f.read().strip()
                tool_strings.append(f"    {tool_name}: {tool_description}")

        return "\n".join(tool_strings), ", ".join(tool_names)

    def add_documents_if_not_exists(self, documents, collection, collection_name):
        """
        Add documents to the vector database if the document ID does not exist.
        :param documents: List of dicts, each requiring 'page_content' and 'metadata' keys
        :param collection: Chroma vector database collection
        :param collection_name: String, collection name
        """
        new_texts = []
        new_metadatas = []
        new_ids = []
        for doc in documents:
            doc_id = doc['metadata'].get("id")
            if not doc_id:
                # If no ID exists, generate a unique ID
                doc_id = str(uuid.uuid4())
                doc['metadata']['id'] = doc_id

            # Use get method to check if document exists
            existing_docs = collection.get(ids=[doc_id])
            if not existing_docs['documents']:
                # Use conservative truncation for add_texts to ensure stability
                truncated_text = self._truncate_for_embedding(doc['page_content'], max_tokens=30000, enable_truncation=True)
                new_texts.append(truncated_text)
                new_metadatas.append(doc['metadata'])
                new_ids.append(doc_id)

        if new_texts:
            collection.add_texts(texts=new_texts, metadatas=new_metadatas, ids=new_ids)
            logging.info(f"Added {len(new_texts)} new documents to {collection_name}")

    def Load_PLAN_RAG(self):
        """
        Load knowledge entries from a JSON file and store them in the Chroma vector database.
        Each JSON entry is stored and retrieved as an independent unit.
        """
        json_file_path = os.path.join(self.doc_dir, "Plan_Knowledge.json")

        if not os.path.exists(json_file_path):
            raise FileNotFoundError(f"JSON file not found: {json_file_path}")

        with open(json_file_path, "r", encoding="utf-8") as file:
            knowledge_data = json.load(file)

        if not isinstance(knowledge_data, list):
            raise ValueError("JSON file format error: should contain a list of knowledge entries")

        documents = [
            {
                "page_content": entry["content"],
                "metadata": entry.get("metadata", {})
            }
            for entry in knowledge_data
        ]
        self.add_documents_if_not_exists(documents, self.vectorstore, self.collection1_name)
        logging.info("Loaded PLAN_RAG data.")
        # Chroma auto-persists, no need to explicitly call persist()

    def Load_Tool_RAG(self):
        """
        Load knowledge entries from JSON and txt files, and store them in the Chroma vector database.
        Supports two formats:
        1. JSON file: Task_Konwledge.json
        2. TXT files: all .txt files under the doc/tool/ folder
        """
        documents = []
        
        # 1. Load JSON file (maintain backward compatibility)
        json_file_path = os.path.join(self.doc_dir, "Task_Konwledge.json")
        if os.path.exists(json_file_path):
            try:
                with open(json_file_path, "r", encoding="utf-8") as file:
                    knowledge_data = json.load(file)

                if isinstance(knowledge_data, list):
                    json_documents = [
                        {
                            "page_content": entry["content"],
                            "metadata": entry.get("metadata", {})
                        }
                        for entry in knowledge_data
                    ]
                    documents.extend(json_documents)
                    logging.info(f"Loaded {len(json_documents)} documents from JSON file.")
                else:
                    logging.warning("JSON file format error: should contain a list of knowledge entries")
            except Exception as e:
                logging.error(f"Error loading JSON file: {e}")
        else:
            logging.info("JSON file not found, skipping JSON loading.")

        # 2. Load TXT files
        tool_dir = os.path.join(self.doc_dir, "tool")
        if os.path.exists(tool_dir):
            txt_files = [f for f in os.listdir(tool_dir) if f.endswith('.txt')]
            for txt_file in txt_files:
                try:
                    txt_file_path = os.path.join(tool_dir, txt_file)
                    with open(txt_file_path, "r", encoding="utf-8") as file:
                        content = file.read().strip()
                        print(content)
                    
                    if content:  # Only add non-empty content
                        # Use filename (without extension) as source
                        source_name = os.path.splitext(txt_file)[0]
                        txt_document = {
                            "page_content": content,
                            "metadata": {
                                "source": source_name,
                                "file_type": "txt",
                                "file_path": txt_file_path
                            }
                        }
                        documents.append(txt_document)
                        logging.info(f"Loaded document from TXT file: {txt_file}")
                except Exception as e:
                    logging.error(f"Error loading TXT file {txt_file}: {e}")
        else:
            logging.info("Tool folder not found, skipping TXT file loading.")

        # 3. Add all documents to the vector database
        if documents:
            self.add_documents_if_not_exists(documents, self.vectorstore_tool, self.collection2_name)
            logging.info(f"Total loaded {len(documents)} documents to Tool_RAG.")
        else:
            logging.warning("No documents found to load into Tool_RAG.")
        
        # Chroma auto-persists, no need to explicitly call persist()

    def _create_agent(self, prompt_template, examples):
        model = ChatOpenAI(model=self.model, base_url=self.base_url)

        example_prompt = ChatPromptTemplate.from_messages([
            ("human", "{input}"),
            ("ai", "{output}")
        ])

        few_shot_prompt = FewShotChatMessagePromptTemplate(
            example_prompt=example_prompt,
            examples=examples
        )

        parser = StrOutputParser()

        final_prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_template),
            few_shot_prompt,
            ("human", "{input}")
        ])

        agent = final_prompt | model | parser
        return agent

    def shell_writing(self, commands, step):
        shell_script_path = os.path.join(self.output_dir, f"{self.id}_Step_{step}.sh")

        code_prefix = [
            'which python',
            'conda config --set show_channel_urls false',
            'conda config --add channels conda-forge',
            'conda config --add channels bioconda',
            'mkdir -p ./output/'+str(self.id)
        ]

        with open(shell_script_path, "w", encoding="utf-8") as file:
            # Write prefix commands first
            file.write("#!/bin/bash\n")
            for command in code_prefix:
                file.write(command + "\n")

            # Write the actual shell commands
            for command in commands:
                file.write(f"{command}\n")
        return shell_script_path

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Simple text truncation"""
        return text if len(text) <= max_length else text[:max_length] + '...'
    
    def _detect_workflow_type(self, goal: str) -> Optional[str]:
        """
        Detect whether the goal matches a specific focused workflow type.
        If matched, return the workflow_type string; otherwise return None (indicating full workflow).
        
        Priority: keyword exact match > default full workflow
        """
        goal_lower = goal.lower()
        
        # If contains words like "complete", "comprehensive", "full", "all", treat as full workflow
        full_keywords = ['complete', 'comprehensive', 'full pipeline', 'all analyses', 'all advanced', 'entire', 'whole']
        if any(kw in goal_lower for kw in full_keywords):
            return None  # Full workflow
        
        # Check if it matches a specific focused workflow
        for workflow_type, keywords in self.plan_workflow_keywords.items():
            for kw in keywords:
                if kw in goal_lower:
                    return workflow_type
        
        # Further check: if the goal mentions only one analysis type, treat as focused
        analysis_mentions = {
            'pca_only': ['pca', 'principal component'],
            'admixture_only': ['admixture', 'ancestry proportion'],
            'diversity_stats': ['roh', 'heterozygosity', 'ld decay', 'genetic diversity'],
            'treemix_fstats': ['treemix', 'f-statistics', 'f3', 'f4', 'd-statistics'],
            'qc_only': ['quality control', 'filtering', 'qc'],
            'kinship_only': ['kinship', 'relatedness', 'king'],
        }
        
        matched = []
        for wtype, keywords in analysis_mentions.items():
            if any(kw in goal_lower for kw in keywords):
                matched.append(wtype)
        
        # Only return focused when exactly one analysis type matches
        if len(matched) == 1:
            return matched[0]
        
        return None  # Multiple analyses or undetermined, use full workflow
    
    def _identify_task_type(self, description: str) -> List[str]:
        """
        Identify task types based on task description, used to enhance RAG retrieval
        
        Args:
            description: Task description text
            
        Returns:
            List of matched task types
        """
        description_lower = description.lower()
        matched_types = []
        
        for task_type, keywords in self.task_type_keywords.items():
            for keyword in keywords:
                if keyword.lower() in description_lower:
                    matched_types.append(task_type)
                    break
        
        return matched_types
    
    def _is_visualization_task(self, description: str) -> bool:
        """
        Determine whether the task is a visualization task
        
        Args:
            description: Task description
            
        Returns:
            Whether it is a visualization task
        """
        viz_keywords = [
            'visualization', 'visualize', 'plot', 'plotting', 'figure', 'chart',
            'graph', 'draw', 'generate plot', 'create plot', 'make plot',
            'png', 'pdf', 'image'
        ]
        description_lower = description.lower()
        return any(kw.lower() in description_lower for kw in viz_keywords)
    
    def _enhanced_rag_search(
        self, 
        query: str, 
        vectorstore, 
        k: int = 3,
        task_types: List[str] = None,
        is_visualization: bool = False
    ) -> str:
        """
        Enhanced RAG retrieval method combining semantic search and keyword matching
        
        Args:
            query: Search query
            vectorstore: Vector store
            k: Number of documents to retrieve
            task_types: List of task types
            is_visualization: Whether it is a visualization task
            
        Returns:
            Concatenated string of retrieved document contents
        """
        all_docs = []
        seen_ids = set()
        
        # 1. Semantic similarity search
        try:
            semantic_docs = vectorstore.similarity_search(query, k=k)
            for doc in semantic_docs:
                doc_id = doc.metadata.get('id', str(hash(doc.page_content[:100])))
                if doc_id not in seen_ids:
                    all_docs.append(doc)
                    seen_ids.add(doc_id)
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
        
        # 2. Exact matching based on task type
        if task_types:
            for task_type in task_types:
                try:
                    type_docs = vectorstore.similarity_search(
                        task_type.replace('_', ' '), 
                        k=2
                    )
                    for doc in type_docs:
                        doc_id = doc.metadata.get('id', str(hash(doc.page_content[:100])))
                        if doc_id not in seen_ids:
                            all_docs.append(doc)
                            seen_ids.add(doc_id)
                except Exception as e:
                    logger.warning(f"Task type search failed for {task_type}: {e}")
        
        # 3. If it is a visualization task, additionally search for visualization-related knowledge
        if is_visualization:
            viz_queries = ['visualization template', 'plot code', 'matplotlib seaborn']
            for vq in viz_queries:
                try:
                    viz_docs = vectorstore.similarity_search(vq, k=2)
                    for doc in viz_docs:
                        doc_id = doc.metadata.get('id', str(hash(doc.page_content[:100])))
                        # Prioritize documents containing complete code templates
                        if doc_id not in seen_ids:
                            if '```python' in doc.page_content or '```r' in doc.page_content.lower():
                                all_docs.insert(0, doc)  # Code templates first
                            else:
                                all_docs.append(doc)
                            seen_ids.add(doc_id)
                except Exception as e:
                    logger.warning(f"Visualization search failed: {e}")
        
        # 4. Deduplicate and limit result count
        max_docs = k * 2 if is_visualization else k + 2
        final_docs = all_docs[:max_docs]
        
        # 5. Concatenate document contents
        if final_docs:
            result_content = "\n\n---\n\n".join([doc.page_content for doc in final_docs])
            logger.info(f"Enhanced RAG retrieved {len(final_docs)} documents")
            return result_content
        else:
            logger.warning("No documents retrieved from enhanced RAG search")
            return ""
    
    def _truncate_for_embedding(
        self, 
        text: str, 
        max_tokens: int = MAX_EMBEDDING_TOKENS, 
        enable_truncation: bool = True
    ) -> str:
        """
        Intelligently truncate text to fit embedding model token limits
        
        Args:
            text: Text to truncate
            max_tokens: Maximum token count (default 30000, suitable for text-embedding-3-large)
            enable_truncation: Whether to enable truncation
            
        Returns:
            Truncated text
        """
        if not text or not enable_truncation:
            return text
        
        # Use more accurate token estimation (mixed CJK/English ~0.75 tokens/char)
        estimated_tokens = len(text) * 0.75
        
        if estimated_tokens <= max_tokens:
            return text
        
        logger.warning(f"Text too long ({estimated_tokens:.0f} tokens), truncating to {max_tokens} tokens")
        
        # Calculate maximum character count
        max_chars = int(max_tokens / 0.75)
        truncated = text[:max_chars]
        
        # Smart sentence breaking: truncate at natural delimiters
        delimiters = ['\n\n', '\n', '。', '.', '！', '!', '？', '?', '；', ';']
        for delimiter in delimiters:
            last_pos = truncated.rfind(delimiter)
            if last_pos > max_chars * 0.7:  # Keep at least 70% of content
                return truncated[:last_pos + len(delimiter)]
        
        return truncated + '...'
    
    def _format_shell_output(self, stdout: str, stderr: str, max_length: int = MAX_OUTPUT_LENGTH) -> Tuple[str, str]:
        """Format shell output with length limit"""
        formatted_stdout = stdout[:max_length] if len(stdout) > max_length else stdout
        formatted_stderr = stderr[:max_length] if len(stderr) > max_length else stderr
        return formatted_stdout, formatted_stderr

    def save_progress(self, step_data, output_dir, file_name):
        file_name = f"{self.id}_{file_name}"
        file_path = os.path.join(output_dir, file_name)

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Write data
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(step_data, file, indent=4)

    def load_progress(self, output_dir, file_name):
        file_name = f"{self.id}_{file_name}"
        file_path = os.path.join(output_dir, file_name)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                step_data = json.load(file)
            return step_data
        return None

    def _get_output_files(self):
        output_files = []
        output_dir_path = os.path.join(self.output_dir, str(self.id))

        # Iterate over all files in the output directory
        for root, dirs, files in os.walk(output_dir_path):
            for file in files:
                if file.endswith(('.json', '.sh', '.txt')):  # Filter by file type as needed
                    output_files.append(os.path.join(root, file))

        return output_files

    def _archive_existing_plan(self):
        """
        Archive the existing PLAN.json to ./doc/ and excute_agent_plan_history.json
        """
        plan_file = os.path.join(self.output_dir, "PLAN.json")
        if os.path.exists(plan_file):
            # Generate timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Copy to ./doc/ directory
            archived_plan_path = os.path.join(self.doc_dir, f"PLAN_{self.id}_{timestamp}.json")
            with open(plan_file, "r", encoding="utf-8") as src, open(archived_plan_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())
            logging.info(f"Archived existing PLAN.json to {archived_plan_path}")

            # Append to excute_agent_plan_history.json
            history_plan_file = os.path.join(self.doc_dir, "excute_agent_plan_history.json")  # Changed to doc_dir
            if not os.path.exists(history_plan_file):
                with open(history_plan_file, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=4, ensure_ascii=False)

            with open(history_plan_file, "r", encoding="utf-8") as f:
                history_plans = json.load(f)

            with open(plan_file, "r", encoding="utf-8") as f:
                current_plan = json.load(f)

            history_entry = {
                "id": self.id,
                "timestamp": timestamp,
                "plan": current_plan
            }
            history_plans.append(history_entry)

            with open(history_plan_file, "w", encoding="utf-8") as f:
                json.dump(history_plans, f, indent=4, ensure_ascii=False)

            logging.info(f"Added existing PLAN.json to history with ID {self.id}")

    def _archive_existing_steps(self):
        """
        Archive existing step output files to excute_agent_task_history.json
        """
        history_task_file = os.path.join(self.doc_dir, "excute_agent_task_history.json")  # Changed to doc_dir
        if not os.path.exists(history_task_file):
            with open(history_task_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=4, ensure_ascii=False)

        steps = []
        for file in os.listdir(self.output_dir):
            debug_match = re.match(rf"^{self.id}_DEBUG_Output_(\d+)\.json$", file)
            shell_match = re.match(rf"^{self.id}_Step_(\d+)\.sh$", file)
            if debug_match:
                step_num = int(debug_match.group(1))
                with open(os.path.join(self.output_dir, file), "r", encoding="utf-8") as f:
                    debug_data = json.load(f)
                steps.append({
                    "step_number": step_num,
                    "type": "debug_output",
                    "content": debug_data
                })
            elif shell_match:
                step_num = int(shell_match.group(1))
                with open(os.path.join(self.output_dir, file), "r", encoding="utf-8") as f:
                    shell_commands = f.read()
                steps.append({
                    "step_number": step_num,
                    "type": "shell_script",
                    "content": shell_commands
                })

        # Read existing task history
        with open(history_task_file, "r", encoding="utf-8") as f:
            history_tasks = json.load(f)

        # Read current plan
        current_plan = self.load_progress(self.output_dir, "PLAN.json")

        history_entry = {
            "id": self.id,
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "steps": steps,
            "plan": current_plan
        }

        history_tasks.append(history_entry)

        with open(history_task_file, "w", encoding="utf-8") as f:
            json.dump(history_tasks, f, indent=4, ensure_ascii=False)

        logging.info(f"Archived existing steps to task history with ID {self.id}")

    def save_execution_history(self, asking, mode=0):
        """
        Save execution history to ./history/{id}/execute.json
        
        mode:
        - 0: New plan mode, add a new history record (containing asking and new plan)
        - 1: Execution mode, update the execute section of the last record
        
        Format:
        [
            {
                "asking": "user's request",
                "plan": "generated plan",
                "execute": {
                    "steps": [
                        {
                            "step_number": 1,
                            "shell": "shell script content",
                            "debug": "debug output content"
                        }
                    ],
                    "status": "completed"
                }
            }
        ]
        """
        # Ensure history/{id} directory exists
        formatted_id = str(self.id).zfill(3)
        history_dir = os.path.join('./history', formatted_id)
        os.makedirs(history_dir, exist_ok=True)
        
        execute_file_path = os.path.join(history_dir, 'execute.json')
        
        # Read existing history or create new
        if os.path.exists(execute_file_path):
            with open(execute_file_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
        else:
            history = []
        
        if mode == 0:  # New plan mode
            # Read the current PLAN
            plan_data = self.load_progress(self.output_dir, "PLAN.json")
            
            # Create a new history entry
            history_entry = {
                "asking": asking,
                "plan": plan_data,
                "execute": {
                    "steps": [],
                    "status": "pending"
                }
            }
            
            # Add new record
            history.append(history_entry)
            
        elif mode == 1:  # Execution mode
            if not history:
                logging.error("No history found to update execution steps")
                return
            
            # Get the last record
            last_entry = history[-1]
            
            # Collect all step files
            base_output_path = os.path.join(os.getcwd(), 'output')
            steps = []
            
            # Get all step files and sort
            step_files = []
            for file in os.listdir(base_output_path):
                if file.startswith(f"{formatted_id}_Step_") and file.endswith(".sh"):
                    step_num = int(re.search(r'_Step_(\d+)\.sh$', file).group(1))
                    step_files.append((step_num, file))
            step_files.sort()  # Sort by step number
            
            # Process each step
            for step_num, _ in step_files:
                step_results = {
                    "step_number": step_num
                }
                
                # Read shell script
                shell_file = os.path.join(base_output_path, f"{formatted_id}_Step_{step_num}.sh")
                if os.path.exists(shell_file):
                    with open(shell_file, 'r', encoding='utf-8') as f:
                        step_results["shell"] = f.read()
                
                # Read debug output
                debug_file = os.path.join(base_output_path, f"{formatted_id}_DEBUG_Output_{step_num}.json")
                if os.path.exists(debug_file):
                    with open(debug_file, 'r', encoding='utf-8') as f:
                        step_results["debug"] = json.load(f)
                
                steps.append(step_results)
            
            # Update the execute section of the last record
            last_entry["execute"] = {
                "steps": steps,
                "status": "completed" if steps else "pending"
            }
            
            # Update the last entry in history
            history[-1] = last_entry
        
        # Save updated history
        with open(execute_file_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
        
        logging.info(f"Saved execution history for ID {self.id} in mode {mode}")

    def execute_PLAN(self, goal, datalist):
        """
        Generate a new PLAN, overwriting the previous PLAN.json, while archiving the old plan and step outputs to history.
        """
        plan_file_path = os.path.join(self.output_dir, "PLAN.json")
        existing_plan = self.load_progress(self.output_dir, "PLAN.json")
        print(existing_plan)
        print()
        if existing_plan:
            self._archive_existing_plan()
            # self._archive_existing_steps()
            logging.info("existing PLAN found.")
        else:
            logging.info("No existing PLAN found. Proceeding to generate a new PLAN.")
        # Generate new PLAN
        logging.info("Generating a new PLAN.")
        update_execute_agent_status_and_attempt(self.id, 1, 0)
        
        # Detect if the goal matches a specific focused workflow
        detected_workflow = self._detect_workflow_type(goal)
        
        # Use enhanced RAG retrieval to get related documents
        task_types = self._identify_task_type(goal)
        is_viz = self._is_visualization_task(goal)
        
        if detected_workflow:
            # Focused workflow: prioritize retrieving matched focused workflow
            logging.info(f"Detected focused workflow type: {detected_workflow}")
            search_query = f"Focused Workflow {detected_workflow} {goal}"
            rag_k = 2  # Retrieve fewer documents to avoid mixing in full workflows
        else:
            # General/full workflow
            search_query = goal
            rag_k = self.plan_rag_k
        
        related_docs_content = self._enhanced_rag_search(
            query=search_query,
            vectorstore=self.vectorstore,
            k=rag_k,
            task_types=task_types,
            is_visualization=is_viz
        )
        logging.info(f"Plan RAG retrieved content length: {len(related_docs_content)}, workflow: {detected_workflow or 'full'}")
        # Build reference content: use only related document content as reference
        combined_reference = related_docs_content

        PLAN_input = {
            "input": json.dumps({
                "id": self.id,
                "goal": goal,
                "datalist": datalist,
                "related_docs": combined_reference
            })
        }
        PLAN_results = self.PLAN_agent.invoke(PLAN_input)
        print(PLAN_results)
        PLAN_results = Json_Format_Agent(PLAN_results, self.api_key, self.base_url)
        
        update_execute_agent_status_and_attempt(self.id, 0, 0)
        try:
            PLAN_results_dict = normalize_keys(json.loads(PLAN_results.strip().strip('"')))
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse PLAN_results: {e}")
            return {}

        # Save new PLAN, overwriting previous PLAN.json
        self.save_progress(PLAN_results_dict, self.output_dir, "PLAN.json")
        logging.info("Saved new PLAN.json.")
        update_execute_agent_stage(self.id, "PLAN")
        # Save to execution history, mode=0 indicates new plan
        self.save_execution_history(goal, mode=0)

        logging.info("_____________________________________________________")
        logging.info(json.dumps(PLAN_results_dict, indent=4, ensure_ascii=False))
        logging.info("_____________________________________________________")
        
        return PLAN_results_dict

    def get_all_files_in_output_folder(self):
        """
        Get all file paths under the output/{id} folder
        """
        output_folder = os.path.join(self.output_dir, self.id)
        if not os.path.exists(output_folder):
            print(f"Folder {output_folder} does not exist.")
            return []

        # Iterate over all files
        all_files = []
        for root, dirs, files in os.walk(output_folder):
            for file in files:
                file_path = os.path.join(root, file)
                all_files.append(file_path)
        return all_files

    def execute_TASK(self, datalist):
        PLAN_results_dict = self.load_progress(self.output_dir, f"PLAN.json")
        PLAN_results_dict = normalize_keys(PLAN_results_dict)
        TASK_agent = self.TASK_agent
        step_datalist = datalist
        if self.excutor:
            DEBUG_agent = self.DEBUG_agent
        ids = self.id
        # Get paths of all generated files and add them to step['input filename']
        
        all_output_files = self.get_all_files_in_output_folder()
        print(f"All files in output/{ids}: {all_output_files}")

        for i in range(1, len(PLAN_results_dict['plan']) + 1):
            print("Step:", i)
            self.check_stop()
            if self.stop_flag:
                break
            step = PLAN_results_dict['plan'][i - 1]

            if self.excutor:
                DEBUG_output_dict = self.load_progress(self.output_dir, f"DEBUG_Output_{i}.json")

                if DEBUG_output_dict and DEBUG_output_dict.get("stats", True):
                    print(f"Step {i} already completed. Continuing.")
                    step_datalist = DEBUG_output_dict['output_filename'] + step_datalist
                    continue

            # tool_name = step['tools']
            # tool_links = load_tool_links(tool_name, self.tools_dir)
            update_execute_agent_status_and_attempt(self.id, 1, 0)
            
            # Use enhanced RAG retrieval to get related documents
            step_description = step.get('description', '')
            step_tools = step.get('tools', '')
            combined_query = f"{step_description} {step_tools}"
            
            # Identify task type
            task_types = self._identify_task_type(combined_query)
            is_viz = self._is_visualization_task(step_description)
            
            # Enhanced retrieval
            related_docs_content = self._enhanced_rag_search(
                query=combined_query,
                vectorstore=self.vectorstore_tool,
                k=self.task_rag_k,
                task_types=task_types,
                is_visualization=is_viz
            )
            
            logging.info(f"Task RAG retrieved content for step {i}, is_viz={is_viz}, types={task_types}")
            # Add traversed file paths to step['input filename']
            additional_files = self.get_all_files_in_output_folder()
            step['input_filename'].extend(additional_files)

            self.check_stop()
            if self.stop_flag:
                break

            # print(step['input_filename'])

            generated_files = self._get_output_files()
            step['input_filename'].extend(generated_files)
            step['input_filename'] = list(set(step['input_filename']))  # Deduplicate
            print(step['input_filename'])

            # Repeat Test count
            retry_count = 0
            # JSON error
            Json_Error = False
            # Context reset counter
            context_reset_count = 0
            max_context_resets = 1  # Maximum 1 context reset

            while retry_count < self.repeat:
                if retry_count == 0 or Json_Error:

                    self.check_stop()
                    if self.stop_flag:
                        break
                    # Extract file paths from datalist
                    # Assume step['input_filename'] already exists and is a list
                    new_input_filenames = [item.split(':')[0] for item in step_datalist]
                    update_execute_agent_stage(self.id, "EXECUTE")
                    # Update step['input_filename'], ensuring no duplicate file paths
                    step['input_filename'] = list(set(step['input_filename'] + new_input_filenames))
                    # print(step['input_filename'])

                    TASK_input = {
                        "input": json.dumps({
                            "task": step,
                            "id": ids,
                            "related_docs": related_docs_content,  # Use related_docs_content
                        })
                    }
                    TASK_results = TASK_agent.invoke(TASK_input)
                    TASK_results = Json_Format_Agent(TASK_results, self.api_key, self.base_url)
                    PRE_DEBUG_output = []
                    try:
                        TASK_results = json.loads(TASK_results)
                        TASK_results = TASK_results.get("shell", "")
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to parse TASK_results: {e}")
                        TASK_results = ""

                    # If not executing, skip subsequent steps
                    if not self.excutor:
                        shell_script_path = self.shell_writing(TASK_results, i)
                        break

                else:
                    TASK_results = DEBUG_output_dict.get("shell", "")

                # Write as sh script
                shell_script_path = self.shell_writing(TASK_results, i)
                # Execute script
                update_execute_agent_status(self.id)
                update_execute_agent_status_and_attempt(self.id, 3, retry_count+1)

                self.check_stop()
                if self.stop_flag:
                    break
                result = subprocess.run(["bash", shell_script_path], capture_output=True, text=True)

                self.check_stop()
                if self.stop_flag:
                    break
                max_output_length = 5000  # Set maximum output character count

                result_stdout = result.stdout[:max_output_length] if len(result.stdout) > max_output_length else result.stdout
                result_stderr = result.stderr[:max_output_length] if len(result.stderr) > max_output_length else result.stderr

                DEBUG_input = {
                    "input": json.dumps({
                        "task": step,
                        "pre debug": PRE_DEBUG_output,
                        "result": result_stderr if result.returncode != 0 else result_stdout,
                        "related_docs": related_docs_content,
                        "id": ids,
                        "shell": TASK_results,
                    })
                }

                self.save_progress(DEBUG_input, self.output_dir, f"DEBUG_Input_{i}.json")
                DEBUG_output = DEBUG_agent.invoke(DEBUG_input)
                # Save previous input
                PRE_DEBUG_output.append(DEBUG_output)
                update_execute_agent_status_and_attempt(self.id, 2, retry_count+1)
                # Normalize format
                DEBUG_output = Json_Format_Agent(DEBUG_output, self.api_key, self.base_url)

                try:
                    print("***************************************************************")
                    print(DEBUG_output)
                    print("***************************************************************")
                    DEBUG_output_dict = json.loads(DEBUG_output)
                    self.save_progress(DEBUG_output_dict, self.output_dir, f"DEBUG_Output_{i}.json")
                    update_execute_agent_status(self.id)

                    if DEBUG_output_dict.get("stats", False):
                        # Add file verification using CheckAgent
                        debug_output_path = os.path.join(self.output_dir, f"{self.id}_DEBUG_Output_{i}.json")
                        check_results = self.check_agent.check_output_files(debug_output_path)
                        
                        # Reload the DEBUG output file as CheckAgent may have updated it
                        with open(debug_output_path, 'r', encoding='utf-8') as f:
                            DEBUG_output_dict = json.load(f)
                        
                        # If file verification passed
                        if check_results.get("stats", True):
                            # If we have new output filenames, update them
                            if check_results.get("output_filename"):
                                # Update the output_filename in DEBUG_output_dict
                                DEBUG_output_dict["output_filename"] = check_results.get("output_filename")
                                self.save_progress(DEBUG_output_dict, self.output_dir, f"DEBUG_Output_{i}.json")
                            
                            # Success - move to next step
                            previous_output_filenames = step['output_filename']
                            break
                        else:
                            # File verification failed, give DebugAgent another chance
                            DEBUG_input = {
                                "input": json.dumps({
                                    "task": step,
                                    "pre debug": [json.dumps(DEBUG_output_dict)],
                                    "result": f"File verification failed: {check_results.get('analysis', '')}"+result_stderr,
                                    "related_docs": related_docs_content,
                                    "id": ids,
                                    "shell": TASK_results,
                                })
                            }
                            
                            # Run DebugAgent again and parse result
                            DEBUG_output = DEBUG_agent.invoke(DEBUG_input)
                            DEBUG_output = Json_Format_Agent(DEBUG_output, self.api_key, self.base_url)
                            
                            try:
                                new_DEBUG_output_dict = json.loads(DEBUG_output)
                                # Update the DEBUG output file
                                DEBUG_output_dict = new_DEBUG_output_dict
                                self.save_progress(DEBUG_output_dict, self.output_dir, f"DEBUG_Output_{i}.json")
                            except json.JSONDecodeError:
                                logging.error(f"Error parsing DEBUG agent retry output for step {i}")
                            
                            # Check if DebugAgent fixed the issue
                            if DEBUG_output_dict.get("stats", False):
                                previous_output_filenames = step['output_filename']
                                update_execute_agent_status_and_attempt(self.id, 0, retry_count+1)
                                break  # Success
                            else:
                                print(f"Step {i} failed: {DEBUG_output_dict.get('analyze', '')}")
                                print(f"File check analysis: {check_results.get('analysis', '')}")
                                print(f"Attempt {retry_count + 1}")
                                retry_count += 1
                    else:
                        print(f"Step {i} failed. Attempt {retry_count + 1}")
                        retry_count += 1
                except json.JSONDecodeError:
                    print(f"JSON Decode Error, retrying... Attempt {retry_count + 1}")
                    DEBUG_output_dict = {}
                    retry_count += 1
                    Json_Error = True

            if retry_count >= self.repeat:
                if context_reset_count < max_context_resets:
                    # Clear context and retry debug
                    print(f"Step {i} failed after {self.repeat} retries. Clearing context and retrying...")
                    context_reset_count += 1
                    retry_count = 0
                    Json_Error = False
                    PRE_DEBUG_output = []  # Clear previous debug output
                    # Regenerate TASK results
                    TASK_input = {
                        "input": json.dumps({
                            "task": step,
                            "id": ids,
                            "related_docs": related_docs_content,
                        })
                    }
                    TASK_results = TASK_agent.invoke(TASK_input)
                    TASK_results = Json_Format_Agent(TASK_results, self.api_key, self.base_url)
                    try:
                        TASK_results = json.loads(TASK_results)
                        TASK_results = TASK_results.get("shell", "")
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to parse TASK_results after context reset: {e}")
                        TASK_results = ""
                    continue
                else:
                    update_execute_agent_status_and_attempt(self.id, 4, self.repeat)
                    print(f"Step {i} failed after {self.repeat} retries and context reset. Moving to next step.")
                    break
                

        # Update execution history, mode=1 indicates updating execution steps
        self.save_execution_history(None, mode=1)
        
        return PLAN_results_dict
