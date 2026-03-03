import os
import json
import uuid
import logging
from datetime import datetime
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain import hub
from langchain_community.tools import ShellTool

from langchain_community.document_loaders.text import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# PubMed-related imports
from langchain_community.retrievers import PubMedRetriever
from langchain_community.vectorstores.utils import filter_complex_metadata

from mem0 import Memory

from .prompts import CHAT_EXAMPLES, CHAT_PROMPT
import string

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ChatAgent:
    def __init__(self, api_key: str, base_url: str, Model: str = "claude-opus-4-1-20250805-thinking", chroma_db_dir: str = './chroma_db'):
        self.model_name = Model
        self.base_url = base_url
        self.chat_examples = CHAT_EXAMPLES
        self.api_key = api_key
        self.chroma_db_dir = chroma_db_dir
        self.similarity_threshold = 0.6  # Similarity threshold (lowered to reduce online search triggers)
        
        os.environ['OPENAI_API_KEY'] = api_key
        self.prompt_template = CHAT_PROMPT
        self.agent = self._create_agent(self.prompt_template, self.chat_examples)
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large", base_url=self.base_url)
        
        # Initialize PubMed knowledge base
        self.pubmed_collection_name = "pubmed_collection"
        self.pubmed_vectorstore = Chroma(
            collection_name=self.pubmed_collection_name,
            embedding_function=self.embeddings,
            persist_directory=os.path.join(chroma_db_dir, "pubmed")
        )
        
        # Initialize PubMed retriever for online searches with API configuration
        import sys as _sys
        _sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from config_loader import get_pubmed_config
        _pubmed_cfg = get_pubmed_config()
        self.pubmed_retriever = PubMedRetriever(
            api_key=_pubmed_cfg.get("api_key", ""),
            email=_pubmed_cfg.get("email", "user@example.com"),
            top_k_results=5,  # Increased for better results
            doc_content_chars_max=3000  # Increased for more detailed abstracts
        )
        
        # Load existing PubMed knowledge base
        self.load_pubmed_knowledge_from_file()
        
        # self.memory = ConversationBufferMemory(memory_key="history")
        # self.mem0 = Memory()
    
    def add_documents_if_not_exists(self, documents, collection, collection_name):
        """
        Add documents to vector database if document ID does not exist.
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
                # Filter complex metadata (convert lists to strings, etc.)
                filtered_metadata = self._process_metadata_for_storage(doc['metadata'])
                
                # For add_texts, use conservative truncation for stability
                truncated_text = self._truncate_for_embedding(doc['page_content'], max_tokens=30000, enable_truncation=True)
                new_texts.append(truncated_text)
                new_metadatas.append(filtered_metadata)
                new_ids.append(doc_id)

        if new_texts:
            collection.add_texts(texts=new_texts, metadatas=new_metadatas, ids=new_ids)
            logging.info(f"Added {len(new_texts)} new documents to {collection_name}")
    
    def _extract_key_terms(self, query):
        """
        Extract key scientific terms from a complex query to create simpler search terms
        """
        import re
        
        # Define important population genetics and genomics terms
        key_terms = [
            # Population genetics terms
            "population genetics", "genomics", "population structure", "PCA", "ADMIXTURE", 
            "FST", "F-statistics", "ancestry", "admixture", "migration", "drift", "selection",
            "GWAS", "SNP", "variant", "allele", "haplotype", "genome", "genotype",
            
            # Analysis methods
            "principal component", "structure analysis", "diversity", "differentiation",
            "phylogeny", "clustering", "association", "heritability",
            
            # Dataset references
            "1000 genomes", "1KGP", "human genome", "population samples",
            
            # Software/tools
            "PLINK", "VCFtools", "EIGENSOFT", "STRUCTURE"
        ]
        
        # Convert to lowercase for matching
        query_lower = query.lower()
        found_terms = []
        
        # Find all key terms present in the query
        for term in key_terms:
            if term.lower() in query_lower:
                found_terms.append(term)
        
        # If we found specific terms, use them
        if found_terms:
            # Prioritize more specific terms
            if len(found_terms) > 3:
                found_terms = found_terms[:3]  # Limit to top 3 terms
            return " ".join(found_terms)
        
        # Fallback: extract nouns and important words
        # Remove common words and keep potential scientific terms
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'are', 'is', 'what', 'how', 'where', 'when', 'why', 'which'}
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())
        filtered_words = [word for word in words if word not in stop_words and len(word) >= 3]
        
        # Return first few important words
        return " ".join(filtered_words[:4]) if filtered_words else "population genetics"
    
    def _truncate_for_embedding(self, text, max_tokens=30000, enable_truncation=True):
        """
        Truncate text to stay within embedding model token limit.
        text-embedding-3-large supports 32K context, use 30K as safe limit.
        Set enable_truncation=False to disable truncation.
        """
        if not text:
            return text
            
        # If truncation disabled, return original text
        if not enable_truncation:
            return text
            
        # For 32K model, use looser estimation
        # Assume ~0.75 tokens per character on average (considering larger context window)
        estimated_tokens = len(text) * 0.75
        
        if estimated_tokens <= max_tokens:
            return text
            
        # Only truncate when text is extremely long
        print(f"Warning: Text is very long ({estimated_tokens:.0f} estimated tokens), truncating to {max_tokens} tokens")
        
        # Calculate characters to retain
        max_chars = int(max_tokens / 0.75)
        truncated = text[:max_chars]
        
        # Try to truncate at sentence boundaries (period or newline) to avoid mid-sentence cuts
        for delimiter in ['\n\n', '\n', '。', '.', '！', '!', '？', '?']:
            last_delimiter = truncated.rfind(delimiter)
            if last_delimiter > max_chars * 0.7:  # Keep at least 70% of content
                return truncated[:last_delimiter + len(delimiter)]
        
        return truncated + '...'
    
    def _process_metadata_for_storage(self, metadata):
        """
        Process metadata to ensure compatibility with vector database storage.
        Convert lists to comma-separated strings and handle other complex types.
        """
        processed_metadata = {}
        
        for key, value in metadata.items():
            if isinstance(value, list):
                # Convert lists to comma-separated strings
                processed_metadata[key] = ", ".join(str(item) for item in value)
            elif isinstance(value, dict):
                # Convert dictionaries to string representation
                processed_metadata[key] = str(value)
            elif value is None:
                # Keep None values as they are supported
                processed_metadata[key] = value
            elif isinstance(value, (str, int, float, bool)):
                # Keep simple types as they are
                processed_metadata[key] = value
            else:
                # Convert other types to string
                processed_metadata[key] = str(value)
                
        return processed_metadata
    
    def search_local_pubmed_knowledge(self, query, k=3):
        """
        Search local PubMed knowledge base
        """
        try:
            # Use original query text for search (32K model supports long text)
            results = self.pubmed_vectorstore.similarity_search_with_score(query, k=k)
            return results
        except Exception as e:
            logging.error(f"Error searching local PubMed knowledge: {e}")
            return []
    
    def search_online_pubmed(self, query, max_docs=5):
        """
        Search PubMed literature online, focusing on population genetics related content
        """
        try:
            # Create multiple query variations to improve search success
            query_variations = [
                query,  # Original query
                self._extract_key_terms(query),  # Simplified key terms
                f"{self._extract_key_terms(query)} population genetics",  # Key terms + population genetics
                f"{query} genomics",  # Original + genomics
            ]
            
            search_results = []
            successful_query = query  # Default to original query
            
            # Try each query variation until we get results
            for i, search_query in enumerate(query_variations):
                if len(search_query.strip()) == 0:
                    continue
                    
                logging.info(f"Attempting PubMed search {i+1}/4 with query: '{search_query}'")
                
                try:
                    results = self.pubmed_retriever.invoke(search_query)
                    logging.info(f"Query {i+1} returned {len(results)} results")
                    
                    if results:
                        search_results = results
                        successful_query = search_query
                        logging.info(f"✅ Successful search with query variation {i+1}")
                        break
                        
                except Exception as e:
                    logging.warning(f"Query {i+1} failed: {e}")
                    continue
            
            if not search_results:
                logging.warning("All query variations failed to return results")
            
            logging.info(f"PubMed search returned {len(search_results)} raw results")
            
            # Debug: print first few results
            for i, result in enumerate(search_results[:2]):
                logging.info(f"Result {i+1}: {result.page_content[:100]}...")
                logging.info(f"Metadata: {result.metadata}")
            
            # Limit number of results
            search_results = search_results[:max_docs]
            logging.info(f"Limited to {len(search_results)} results")
            
            # Prepare documents to save to knowledge base
            documents_to_save = []
            for result in search_results:
                doc_content = result.page_content
                metadata = result.metadata.copy()
                metadata['id'] = str(uuid.uuid4())
                metadata['source'] = 'pubmed_online'
                metadata['original_query'] = query
                metadata['successful_query'] = successful_query
                
                documents_to_save.append({
                    'page_content': doc_content,
                    'metadata': metadata
                })
            
            # Save newly searched documents to local knowledge base
            if documents_to_save:
                logging.info(f"Attempting to save {len(documents_to_save)} documents to local knowledge base")
                self.add_documents_if_not_exists(documents_to_save, self.pubmed_vectorstore, self.pubmed_collection_name)
                
                # Also save to JSON file for user visibility
                self.save_documents_to_json_file(documents_to_save)
                
                logging.info(f"Successfully saved {len(documents_to_save)} new PubMed documents to local knowledge base and JSON file")
            else:
                logging.warning("No documents to save - PubMed search returned empty results")
            
            return search_results
            
        except Exception as e:
            logging.error(f"Error searching online PubMed: {e}")
            import traceback
            logging.error(f"Full traceback: {traceback.format_exc()}")
            return []
    
    def get_pubmed_knowledge(self, query, k=3):
        """
        Get PubMed knowledge: first search locally, if similarity is insufficient then search online
        """
        # First search local knowledge base
        local_results = self.search_local_pubmed_knowledge(query, k=k)
        
        highest_score = 0.0  # Initialize highest score
        
        if local_results:
            # Check highest similarity score
            highest_score = max([score for _, score in local_results])
            
            if highest_score >= self.similarity_threshold:
                logging.info(f"Using local PubMed knowledge (highest score: {highest_score:.3f})")
                return [doc for doc, score in local_results]
        
        # If local results are insufficient or similarity too low, perform online search
        logging.info(f"Local similarity too low ({highest_score:.3f} < {self.similarity_threshold}), searching online PubMed")
        online_results = self.search_online_pubmed(query)
        
        # Combine local and online results
        combined_results = []
        if local_results:
            combined_results.extend([doc for doc, score in local_results])
        combined_results.extend(online_results)
        
        return combined_results[:k]  # Return top k results
    
    def is_scientific_query(self, asking):
        """
        Determine if a query is related to population genetics research and requires PubMed knowledge support
        """
        population_genetics_keywords = [
            # Core population genetics terms
            "population", "genetics", "genomics", "evolution", "evolutionary", 
            "ancestry", "admixture", "migration", "demographic", "coalescent",
            "drift", "selection", "mutation", "variant", "allele", "haplotype",
            "lineage", "phylogeny", "tree", "structure", "stratification",
            
            # Analytical methods
            "pca", "principal component", "admixture", "structure", "fst", "f3", "f4",
            "fstatistics", "f-statistics", "diversity", "differentiation", "distance",
            "clustering", "tree", "network", "mds", "multidimensional scaling",
            
            # Software and tools
            "plink", "vcftools", "admixture", "structure", "eigensoft", "smartpca",
            "treemix", "mixmapper", "abacus", "msmc", "psmc", "dadi", "sfs",
            
            # Data types and formats
            "vcf", "snp", "indel", "genotype", "sequencing", "array", "chip",
            "whole genome", "exome", "targeted", "imputation", "phasing",
            
            # Research applications
            "gwas", "association", "heritability", "polygenic", "risk score",
            "biobank", "ethnicity", "race", "continental", "global", "local",
            "ancient", "archaic", "neanderthal", "denisovan",
            
            # Statistical concepts
            "effective size", "bottleneck", "expansion", "split", "divergence",
            "gene flow", "introgression", "hybridization", "inbreeding", "hardy weinberg"
        ]
        
        return any(keyword in asking.lower() for keyword in population_genetics_keywords)

    def _create_agent(self, prompt_template, examples):
        model = ChatOpenAI(model=self.model_name, base_url=self.base_url)

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
        # final_prompt = final_prompt | self.memory

        agent = final_prompt | model | parser
        return agent
    
    def read_plan(self, id):
        filepath=f'./output/{id}_PLAN.json'
        with open(filepath, 'r') as file:
            plan = json.load(file)
        return plan
    
    def read_latest_step(self, directory='./output/'):
        # List all step_*.sh files in the directory
        step_files = [f for f in os.listdir(directory) if f.startswith('step_') and f.endswith('.sh')]
        if not step_files:
            return None
        
        # Sort files to get the one with the highest step number
        step_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
        latest_step_file = step_files[-1]
        
        # Read the content of the latest step file
        with open(os.path.join(directory, latest_step_file), 'r') as file:
            step_content = file.readlines()
        
        # Filter out comments and categorize the commands
        commands = [line.strip() for line in step_content if line.strip() and not line.startswith('#')]
        
        return commands
    
    def save_chat_history(self, id, asking, response):
        import threading
        import fcntl  # File lock
        
        # Define directory for saving chat history
        formatted_id = str(id).zfill(3)
        history_dir = os.path.join('./history', formatted_id)
        os.makedirs(history_dir, exist_ok=True)

        # Define path for chat.json
        chat_file_path = os.path.join(history_dir, 'chat.json')
        
        # Use file lock for thread safety
        try:
            # If file exists, load existing records; otherwise create empty list
            chat_history = []
            if os.path.exists(chat_file_path):
                with open(chat_file_path, 'r', encoding='utf-8') as file:
                    try:
                        fcntl.flock(file.fileno(), fcntl.LOCK_SH)  # Shared lock for read
                        chat_history = json.load(file)
                    finally:
                        fcntl.flock(file.fileno(), fcntl.LOCK_UN)  # Release lock

            # Check for incomplete placeholder record
            placeholder_updated = False
            for entry in reversed(chat_history):
                if (entry.get('asking') == asking and 
                    entry.get('status') == 'processing' and 
                    entry.get('response') == ''):
                    # Update placeholder record
                    entry['response'] = response
                    entry['timestamp'] = datetime.now().isoformat()
                    entry['status'] = 'completed'
                    placeholder_updated = True
                    break
            
            # If no placeholder found, add new record (backward compatibility)
            if not placeholder_updated:
                new_entry = {
                    "asking": asking,
                    "response": response,
                    "timestamp": datetime.now().isoformat(),
                    "session_id": formatted_id
                }
                chat_history.append(new_entry)

            # Save records back to file
            with open(chat_file_path, 'w', encoding='utf-8') as file:
                try:
                    fcntl.flock(file.fileno(), fcntl.LOCK_EX)  # Exclusive lock for write
                    json.dump(chat_history, file, ensure_ascii=False, indent=4)
                finally:
                    fcntl.flock(file.fileno(), fcntl.LOCK_UN)  # Release lock
                    
            logging.info(f"Successfully saved chat history for session {formatted_id}")
            
        except Exception as e:
            logging.error(f"Error saving chat history for session {formatted_id}: {str(e)}")
            # Do not raise exception to avoid affecting main flow
    def get_recent_history(self, id, max_items=10):
        """
        Get recent history records for the specified ID
        """
        formatted_id = str(id).zfill(3)  # Or use formatted_id = f"{int(id):03}"
        history_dir = os.path.join('./history', formatted_id)
        chat_file_path = os.path.join(history_dir, 'chat.json')

        # If history file does not exist, return empty list
        if not os.path.exists(chat_file_path):
            return []

        # Read history and return latest max_items records
        with open(chat_file_path, 'r', encoding='utf-8') as file:
            chat_history = json.load(file)

        return chat_history[-max_items:]  # Return most recent records

    def should_load_plan_or_step(self, asking):
        """
        Determine whether to load analysis plan or execution steps for population genetics workflows
        """
        keywords_for_plan = [
            "plan", "strategy", "planning", "roadmap", "blueprint", "goal", "workflow",
            "pipeline", "analysis plan", "experimental design", "approach", "methodology",
            "overall", "complete", "full", "entire", "whole"
        ]
        keywords_for_step = [
            "step", "command", "task", "action", "process", "procedure", "execution",
            "current", "latest", "recent", "last", "running", "execute", "run",
            "output", "result", "file", "generated", "created"
        ]

        # Check if asking contains any relevant keywords
        needs_plan = any(keyword in asking.lower() for keyword in keywords_for_plan)
        needs_step = any(keyword in asking.lower() for keyword in keywords_for_step)

        return needs_plan, needs_step


    
    def _truncate_text(self, text, max_length):
        return text if len(text) <= max_length else text[:max_length] + '...'
    
    def interpret_plan(self, asking, id):
        needs_plan, needs_step = self.should_load_plan_or_step(asking)

        plan = self.read_plan(id) if needs_plan else None  # Load plan on demand
        latest_step = self.read_latest_step() if needs_step else None  # Load step on demand

        # Get recent 10 history records
        recent_history = self.get_recent_history(id, max_items=10)
        
        # Check if it's a scientific query, if so search PubMed knowledge base
        pubmed_docs = []
        if self.is_scientific_query(asking):
            logging.info("Detected scientific query, searching PubMed knowledge base...")
            pubmed_results = self.get_pubmed_knowledge(asking, k=3)
            
            # Extract document content for prompt
            pubmed_docs = []
            for doc in pubmed_results:
                doc_summary = {
                    "title": doc.metadata.get("title", ""),
                    "abstract": doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content,
                    "source": doc.metadata.get("source", "")
                }
                pubmed_docs.append(doc_summary)
            
            logging.info(f"Retrieved {len(pubmed_docs)} PubMed documents for the query")

        # Build input data
        CHAT_input = {
            "input": json.dumps({
                "history": recent_history,  # Use recent history
                "plan": plan if plan else "",
                "latest_step": latest_step if latest_step else "",
                "asking": asking,
                "pubmed_knowledge": pubmed_docs,  # Add PubMed knowledge
                "related_docs": ""  # Can be extended to load related documents if needed
            })
        }

        CHAT_output = self.agent.invoke(CHAT_input)
        

        # Extract output content
        response = CHAT_output  # Assume invoke method returns string directly
        self.save_chat_history(id, asking, response)  # Only save input and output

        return CHAT_output

    def generate_report(self, id):
        """
        Generate a concise Markdown report based on output files for a given ID.
        
        Args:
            id (str): The project ID in format like "001", "002", etc.
        
        Returns:
            str: The generated markdown report
        """
        formatted_id = str(id).zfill(3)
        output_dir = './output'
        
        # Collect all relevant files
        data = {
            "plan": None,
            "debug_outputs": [],
            "result_files": {},
            "result_images": []
        }
        
        # Read the plan
        plan_path = f'{output_dir}/{formatted_id}_PLAN.json'
        if os.path.exists(plan_path):
            with open(plan_path, 'r') as file:
                data["plan"] = json.load(file)
        
        # Collect all DEBUG output files
        debug_files = [f for f in os.listdir(output_dir) if f.startswith(f'{formatted_id}_DEBUG_Output_') and f.endswith('.json')]
        for debug_file in debug_files:
            file_path = os.path.join(output_dir, debug_file)
            try:
                with open(file_path, 'r') as file:
                    debug_data = json.load(file)
                    data["debug_outputs"].append({
                        "file": debug_file,
                        "content": debug_data
                    })
            except Exception as e:
                data["debug_outputs"].append({
                    "file": debug_file,
                    "error": f"Error reading file: {str(e)}"
                })
        
        # Read result.json if it exists
        result_path = f'{output_dir}/{formatted_id}_result.json'
        result_data = {}
        if os.path.exists(result_path):
            try:
                with open(result_path, 'r') as file:
                    result_data = json.load(file)
                    
                    # Process image paths from 'photo' field
                    if "photo" in result_data and result_data["photo"]:
                        data["result_images"] = result_data["photo"]
                    
                    # Get file contents from 'doc' field
                    if "doc" in result_data and result_data["doc"]:
                        data["result_files"] = result_data["doc"]
            except Exception as e:
                data["result_error"] = f"Error reading result file: {str(e)}"
        
        # Extract expected output filenames from plan and create a mapping of files to their plan steps
        expected_files = []
        file_to_step_map = {}
        plan_steps_summary = []
        
        if data["plan"] and "plan" in data["plan"]:
            for step in data["plan"]["plan"]:
                step_num = step.get("step_number", "")
                step_desc = step.get("description", "")
                tools = step.get("tools", "")
                plan_steps_summary.append(f"Step {step_num}: {step_desc} (Tools: {tools})")
                
                if "output_filename" in step:
                    for output_file in step["output_filename"]:
                        expected_files.append(output_file)
                        # Map each file to its corresponding plan step for reference
                        file_to_step_map[output_file.split(":")[0].strip()] = {
                            "step_number": step_num,
                            "description": step_desc,
                            "tools": tools
                        }
        
        # Create a simple plan summary
        plan_summary = "\n".join(plan_steps_summary)
        print(plan_summary)
        # Actual files and images from result_data
        actual_files = list(data["result_files"].keys()) if data["result_files"] else []
        actual_images = data["result_images"] if data["result_images"] else []
        
        # Create clean file content previews for display
        file_previews = {}
        file_contents = {}
        for filename, content in data["result_files"].items():
            # Check if content appears to be binary
            try:
                if isinstance(content, str):
                    # If there are many non-printable characters, consider it binary
                    if sum(c not in string.printable for c in content[:20]) > 5:
                        file_previews[filename] = "[Binary file content]"
                        file_contents[filename] = "[Binary file content]"
                    else:
                        # For JSON display (truncated)
                        file_previews[filename] = content[:100] + "..." if len(content) > 100 else content
                        
                        # For content display (full with newlines preserved)
                        # Replace escape sequences with actual newlines for display
                        cleaned_content = content.replace('\\n', '\n')
                        file_contents[filename] = cleaned_content
                else:
                    file_previews[filename] = str(content)
                    file_contents[filename] = str(content)
            except:
                file_previews[filename] = "[Error displaying content]"
                file_contents[filename] = "[Error displaying content]"
        
        # Construct the input for the chat agent with specific Markdown format
        report_prompt = f"""
You are a population genetics researcher writing an academic-style analysis report. Generate a comprehensive, scientifically rigorous Markdown report based on the analysis outputs. Do NOT put the output in a code block. Use EXACTLY the following structure:

# Population Genetics Analysis Report — Session {formatted_id}

## 1. Executive Summary

[Write a concise paragraph (150–200 words) summarizing the analysis goal, datasets analyzed (number of populations, individuals, variants), the analytical pipeline, and the most important findings. State the completion status of the workflow. Cite specific quantitative values from the debug outputs wherever possible (e.g., "170,158 SNPs across 3,202 individuals from 26 populations").]

## 2. Data Characterization & Quality Control

[Based on the debug outputs from filtering and QC steps, report:]
- **Initial dataset**: Number of variants, individuals, populations
- **Post-QC dataset**: Variants and individuals retained after MAF, genotyping rate, and biallelic filtering
- **Related individuals**: Number of related pairs identified by KING and individuals removed
- **Final analytical dataset**: Variants and individuals used for downstream analyses
- **LD pruning**: Number of independent SNPs retained for structure analyses

[Present these as a structured summary table where possible.]

## 3. Genetic Diversity & Population Differentiation

### 3.1 Heterozygosity & Inbreeding Coefficients
[Report observed heterozygosity (Ho), expected heterozygosity (He), and inbreeding coefficient (F) per population if available. Identify populations with notably high or low diversity. Interpret in the context of effective population size and demographic history.]

### 3.2 Runs of Homozygosity (ROH)
[Report the total number of ROH segments detected, mean ROH length per population, and FROH (proportion of genome in ROH). Highlight populations with elevated FROH, which may indicate bottleneck history, founder effects, or consanguinity.]

### 3.3 Linkage Disequilibrium Decay
[Compare LD decay rates across populations. Populations with slower LD decay (higher background LD) likely experienced more recent bottlenecks or smaller effective population sizes. Report r² at key distance bins (e.g., 0–1 kb, 10 kb, 50 kb, 100 kb) per population if available.]
        
## 4. Population Structure Analysis

### 4.1 Principal Component Analysis (PCA)
[Report the variance explained by the top principal components (PC1, PC2, PC3). Describe the population clustering patterns observed. Identify which PCs separate continental groups vs. finer-scale structure. Note any outlier individuals or unexpected clustering.]

### 4.2 ADMIXTURE Analysis
[Report the K values tested and the optimal K based on cross-validation error (CV error). Describe the ancestry composition patterns at the optimal K and other informative K values. Identify populations showing admixed ancestry profiles. Present the CV error values for each K in a list.]

### 4.3 TreeMix Phylogenetic Analysis
[Report the population tree topology inferred by TreeMix. Describe migration edges detected (number and direction). Report the log-likelihood improvement with additional migration edges (m=0 through m=5). Identify the optimal number of migration edges based on the likelihood plateau.]

### 4.4 F-statistics & Formal Admixture Tests
[If F3 and D-statistics were computed, report:]
- **F3 statistics**: Which population triplets show significant negative F3 values (indicating admixture)? List the top results with Z-scores.
- **D-statistics (ABBA-BABA)**: Which quartet tests show significant gene flow? Report D-values and Z-scores for the most significant results.

## 5. Quantitative Parameter Estimates for Demographic Modeling

**CRITICAL**: This section extracts quantitative estimates from ALL analyses above to provide parameter priors for demographic model inference (e.g., FastSimCoal2, dadi, moments).

### 5.1 Effective Population Sizes (Ne)
[Estimate Ne for each population from heterozygosity (Ne ≈ θ / 4μ, where θ = 4Neμ), ROH-based estimates, or LD-based estimates. Report plausible ranges. Example format:]
- Population X: Ne ≈ XX,XXX (based on heterozygosity / LD / ROH)
- Population Y: Ne ≈ XX,XXX

### 5.2 Divergence Time Estimates
[From FST values, TreeMix branch lengths, or other available data, estimate approximate divergence times between population pairs. Convert to generations (assuming 25–30 years/generation). Report ranges rather than point estimates.]

### 5.3 Migration Rate Estimates
[From TreeMix migration edges and D-statistics, estimate plausible migration rate ranges between population pairs. Distinguish between ancient and recent gene flow.]

### 5.4 Population Size Change Events
[From ROH patterns, LD decay, Tajima's D (if available), or ADMIXTURE patterns, infer bottleneck or expansion events. Estimate timing and magnitude where possible.]

### 5.5 Recommended Model Architecture
[Based on all evidence, propose a demographic model topology:]
```
[Draw a simple ASCII tree showing population relationships, divergence events, and migration arrows]
```

**Recommended parameter ranges for demographic modeling:**

| Parameter | Description | Estimated Range | Source |
|-----------|-------------|-----------------|--------|
| Ne_PopX | Current Ne of Pop X | X,XXX – XX,XXX | Heterozygosity / LD |
| Ne_anc | Ancestral Ne | X,XXX – XX,XXX | TreeMix / FST |
| T_div1 | Deepest divergence time (gen) | X,XXX – X,XXX | TreeMix / FST |
| T_div2 | Recent divergence time (gen) | XXX – X,XXX | TreeMix |
| m_XY | Migration rate X→Y | Xe-X – Xe-X | D-statistics |
| ... | ... | ... | ... |

## 6. Generated Visualizations

[List all image files with their analytical category. Use the format:]
- **Filename**: Brief description of what the plot shows and its key finding.

## 7. Conclusions & Recommendations

[Write 2–3 paragraphs summarizing:]
1. The key evolutionary insights from this analysis (population relationships, demographic history, gene flow).
2. The consistency or inconsistency across different analytical methods.
3. Specific recommendations for downstream demographic modeling, including which model architectures to test and which parameters to prioritize.
4. Caveats and limitations of the current analysis.

## 8. Methods Summary

[Provide a brief methods section (suitable for a manuscript supplement) listing:]
- Software and versions used (PLINK, KING, smartPCA, ADMIXTURE, TreeMix, Admixtools)
- Key parameter settings for each tool
- Filtering criteria applied

---
*Report generated automatically by PopGenAgent. All quantitative estimates should be validated with formal statistical inference before publication.*
"""
        
        # Extract key quantitative data from output directory for modeling parameters
        quantitative_data = self._extract_quantitative_data(formatted_id)
        
        CHAT_input = {
            "input": json.dumps({
                "data": data,
                "asking": report_prompt,
                "expected_files": expected_files,
                "actual_files": actual_files,
                "actual_images": actual_images,
                "file_previews": file_previews,
                "file_contents": file_contents,
                "debug_outputs": data["debug_outputs"],
                "plan_summary": plan_summary,
                "file_to_step_map": file_to_step_map,
                "full_plan": data["plan"],
                "quantitative_data": quantitative_data
            })
        }
        
        # Generate the initial report
        generated_report = self.agent.invoke(CHAT_input)
        
        # Collect all images from the output directory automatically
        output_project_dir = f'./output/{formatted_id}'
        all_images = []
        
        # Scan for common image formats
        image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf']
        
        if os.path.exists(output_project_dir):
            for root, dirs, files in os.walk(output_project_dir):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in image_extensions):
                        image_path = os.path.join(root, file)
                        relative_image_path = os.path.relpath(image_path, '.')
                        all_images.append({
                            'filename': file,
                            'path': relative_image_path,
                            'web_path': self._get_image_web_path(relative_image_path)
                        })
        
        # Add images section to the report
        report_parts = [generated_report]
        
        if all_images:
            report_parts.append("\n## Generated Images\n")
            report_parts.append("The following images were generated during the analysis:\n")
            
            for img in all_images:
                # Determine image category based on path
                category = self._categorize_image(img['path'])
                report_parts.append(f"\n### {img['filename']}")
                if category:
                    report_parts.append(f"\n*Category: {category}*\n")
                else:
                    report_parts.append("")
                report_parts.append(f"![{img['filename']}]({img['web_path']})\n")
        
        # Combine all parts
        report = '\n'.join(report_parts)
        
        # Save the report to a file in ./output directory
        report_path = f'./output/{formatted_id}_report.md'
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w') as f:
            f.write(report)
        
        # Add report to ./history/{id}/execute.json file
        history_dir = os.path.join('./history', formatted_id)
        execute_json_path = os.path.join(history_dir, 'execute.json')
        
        # Ensure history directory exists
        os.makedirs(history_dir, exist_ok=True)
        
        # Read current execute.json file
        execute_data = []
        if os.path.exists(execute_json_path):
            try:
                with open(execute_json_path, 'r', encoding='utf-8') as f:
                    execute_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Invalid JSON format in {execute_json_path}")
                execute_data = []
        
        # If data is not empty, add report to last entry
        if execute_data:
            # Update report status and content
            execute_data[-1]["report"] = report
            execute_data[-1]["report_status"] = "completed"
        else:
            # If no existing data, create new entry
            execute_data.append({
                "asking": "Report generation",
                "plan": data["plan"] if data["plan"] else {"plan": []},
                "execute": {
                    "steps": [],
                    "status": "completed"
                },
                "report": report
            })
        
        # Save updated execute.json
        with open(execute_json_path, 'w', encoding='utf-8') as f:
            json.dump(execute_data, f, ensure_ascii=False, indent=4)
        
        return report

    def _extract_quantitative_data(self, formatted_id):
        """
        Extract key quantitative data files from the output directory to provide
        structured numerical data for the report generator. This enables extraction
        of population genetics parameters suitable for downstream demographic modeling.
        """
        output_dir = f'./output/{formatted_id}'
        quant_data = {}
        
        if not os.path.exists(output_dir):
            return quant_data
        
        # Key files to look for and read (with size limits)
        key_files = {
            'cv_errors': ['cv_errors.txt', 'admixture_cv_error.txt'],
            'het_stats': ['het.het', 'het_stats.het'],
            'roh_summary': ['roh.hom.indiv', 'roh_analysis.hom.indiv'],
            'roh_segments': ['roh.hom.summary', 'roh_segments.txt'],
            'pca_eigenvalues': ['pca_results.eval', 'pca_eigenvalues.txt'],
            'treemix_llik': ['treemix_llik.txt'],
            'f3_results': ['f3_results.txt', 'f3_statistics.txt', 'admixtools_f3_results.txt'],
            'd_statistics': ['d_statistics.txt', 'admixtools_d_statistics.txt'],
            'fst_results': ['fst_results.txt', 'fst_summary.txt'],
            'basic_stats': ['basic_stats_report.txt', 'diversity_summary.txt'],
            'admixtools_summary': ['admixtools_summary.txt', 'admixtools_summary_report.txt'],
            'kinship': ['kinship.kin0'],
            'ld_decay': ['ld_decay.txt', 'ld_decay.ld'],
        }
        
        for data_key, filenames in key_files.items():
            for filename in filenames:
                file_path = os.path.join(output_dir, filename)
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read(8000)  # Read up to 8KB
                        quant_data[data_key] = {
                            'filename': filename,
                            'content': content
                        }
                        break  # Found the file, skip alternatives
                    except Exception as e:
                        logging.warning(f"Error reading {file_path}: {e}")
        
        # Also scan for log files with key metrics
        for filename in os.listdir(output_dir):
            filepath = os.path.join(output_dir, filename)
            if os.path.isdir(filepath):
                continue
            
            # Read ADMIXTURE log files for CV errors
            if filename.startswith('admixture_k') and filename.endswith('.log'):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for line in f:
                            if 'CV error' in line:
                                k_val = filename.replace('admixture_k', '').replace('.log', '')
                                if 'admixture_cv_detail' not in quant_data:
                                    quant_data['admixture_cv_detail'] = {}
                                quant_data['admixture_cv_detail'][f'K={k_val}'] = line.strip()
                                break
                except Exception:
                    pass
            
            # Read smartPCA log for variance explained
            if filename == 'smartpca.log' or filename == 'smartpca_output.log':
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read(4000)
                    quant_data['smartpca_log'] = {
                        'filename': filename,
                        'content': content
                    }
                except Exception:
                    pass
        
        # Check for ana/ directory (modeling results)
        ana_dir = os.path.join(output_dir, 'ana')
        if os.path.exists(ana_dir):
            for fname in ['modeling_report.txt', 'modeling_report1.txt']:
                fpath = os.path.join(ana_dir, fname)
                if os.path.exists(fpath):
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            content = f.read(10000)
                        quant_data['modeling_report'] = {
                            'filename': fname,
                            'content': content
                        }
                        break
                    except Exception:
                        pass
        
        return quant_data

    def _get_image_web_path(self, relative_image_path):
        """Get image web path based on environment"""
        dev_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
        if os.path.exists(dev_env_path):
            # Dev environment: use /output path
            return f"/{relative_image_path}"
        else:
            # Production: use relative path
            return f"../{relative_image_path}"
    
    def _categorize_image(self, image_path):
        """Categorize image based on file path and name"""
        path_lower = image_path.lower()
        filename_lower = os.path.basename(image_path).lower()
        
        # Infer image type from path and filename
        if 'demographic_model' in filename_lower:
            return "Demographic Model"
        elif 'pca' in filename_lower or 'pca' in path_lower:
            return "Principal Component Analysis"
        elif 'admixture' in filename_lower or 'admixture' in path_lower:
            return "Admixture Analysis"
        elif 'admixtools' in filename_lower or 'admixtools' in path_lower:
            return "AdmixTools Analysis"
        elif 'treemix' in filename_lower or 'treemix' in path_lower:
            return "TreeMix Analysis"
        elif 'ld' in filename_lower and ('decay' in filename_lower or 'pruning' in filename_lower):
            return "Linkage Disequilibrium Analysis"
        elif 'roh' in filename_lower:
            return "Runs of Homozygosity"
        elif 'dendrogram' in filename_lower or 'population_dendrogram' in filename_lower:
            return "Population Dendrogram"
        elif 'tree' in filename_lower and filename_lower.endswith('.pdf'):
            return "Phylogenetic Tree (PDF)"
        elif 'graph' in filename_lower and filename_lower.endswith('.pdf'):
            return "Statistical Graph (PDF)"
        elif 'multiplot' in filename_lower:
            return "Multi-panel Plot"
        elif 'plot' in filename_lower or 'graph' in filename_lower:
            return "Statistical Plot"
        elif filename_lower.endswith('.pdf'):
            return "PDF Document"
        elif 'ana/' in path_lower:
            return "FastSimCoal2 Analysis"
        else:
            return "Analysis Result"

    def save_documents_to_json_file(self, documents, json_file_path="./knowledge/PubMed_Knowledge.json"):
        """
        Append new documents to the PubMed knowledge JSON file
        """
        try:
            # Load existing data or create empty list
            if os.path.exists(json_file_path):
                with open(json_file_path, "r", encoding="utf-8") as file:
                    existing_data = json.load(file)
            else:
                existing_data = []
            
            # Convert documents to JSON format
            new_entries = []
            for doc in documents:
                entry = {
                    "content": doc["page_content"],
                    "metadata": doc["metadata"]
                }
                new_entries.append(entry)
            
            # Append new entries to existing data
            existing_data.extend(new_entries)
            
            # Save back to file
            os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
            with open(json_file_path, "w", encoding="utf-8") as file:
                json.dump(existing_data, file, indent=2, ensure_ascii=False)
            
            logging.info(f"Added {len(new_entries)} documents to {json_file_path} (total: {len(existing_data)})")
            
        except Exception as e:
            logging.error(f"Error saving documents to JSON file: {e}")

    def load_pubmed_knowledge_from_file(self, json_file_path="./knowledge/PubMed_Knowledge.json"):
        """
        Load PubMed knowledge entries from JSON file and store them in Chroma vector database.
        """
        if not os.path.exists(json_file_path):
            logging.info(f"PubMed knowledge file not found: {json_file_path}. Starting with empty knowledge base.")
            return

        try:
            with open(json_file_path, "r", encoding="utf-8") as file:
                knowledge_data = json.load(file)

            if not isinstance(knowledge_data, list):
                logging.error("PubMed knowledge file format error: should contain a list of knowledge entries")
                return

            if len(knowledge_data) == 0:
                logging.info("PubMed knowledge file is empty. Starting with empty knowledge base - will be populated through online searches.")
                return

            documents = [
                {
                    "page_content": entry["content"],
                    "metadata": entry.get("metadata", {})
                }
                for entry in knowledge_data
            ]
            
            self.add_documents_if_not_exists(documents, self.pubmed_vectorstore, self.pubmed_collection_name)
            logging.info(f"Loaded {len(documents)} PubMed knowledge entries from file.")
            
        except Exception as e:
            logging.error(f"Error loading PubMed knowledge from file: {e}")
