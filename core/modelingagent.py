"""
Integrated Population Genetics Analysis Agent
Handles complete analysis workflow from data processing to demographic modeling and interpretation.
"""
import os
import json
import yaml
import glob
import re
import subprocess
import logging
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any, TypedDict, Callable

# Third-party libraries
import demes
import demesdraw
import matplotlib.pyplot as plt
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Import our specialized agents
from .modeling.obs_agent import run_obs_agent
from .modeling.single_pop_agent import run_single_pop_agent
from .modeling.pca_agent import run_pca_agent
from .modeling.treemix_agent import run_treemix_agent
from .modeling.admixture_agent import run_admixture_agent
from .modeling.other_analysis_agent import run_other_analysis_agent
from .modeling.modeling_agent import run_modeling_agent

# Import prompts
from .prompts import (
    DEMOGRAPHIC_MODEL_ANALYSIS_PROMPT,
    GENERAL_IMAGE_ANALYSIS_PROMPT,
    UNIFIED_FASTSIMCOAL_PROMPT,
    fastsimcoal_PROMPT  # Restored for the missing method
)


# MODIFICATION: Added TypedDict for cleaner parameter passing
class FscParams(TypedDict):
    """Parameters for generating FastSimCoal assets."""
    goal: str
    report: str
    mode: str
    output_dir: str
    file_prefix: str
    obs_files: Optional[List[str]]
    sfs_type: Optional[str]
    debug_context: Optional[Dict[str, Any]]


class AnalysisState(TypedDict):
    """Defines the state for the LangGraph analysis workflow."""
    goal: str
    output_id: str
    ana_dir: str
    datalist: List[str]

    # Agent execution results
    obs_agent_result: Optional[Dict[str, Any]]
    single_pop_agent_result: Optional[Dict[str, Any]]
    pca_agent_result: Optional[Dict[str, Any]]
    treemix_agent_result: Optional[Dict[str, Any]]
    admixture_agent_result: Optional[Dict[str, Any]]
    other_analysis_agent_result: Optional[Dict[str, Any]]
    modeling_agent_result: Optional[Dict[str, Any]]
    final_modeling_result: Optional[Dict[str, Any]]

    # Analysis status tracking
    completed_agents: List[str]
    failed_agents: List[str]
    status: str

    # Final outputs
    analysis_reports: Dict[str, str]  # agent_name -> report_content
    final_analysis: str


class ModelingAgent:
    """Handles interactions with LLMs for configuration generation and image analysis."""

    def __init__(self, api_key: str, base_url: str, model: str = "claude-opus-4-1-20250805-thinking"):
        self.model_name = model
        self.base_url = base_url
        os.environ['OPENAI_API_KEY'] = api_key
        
        from langchain_openai import OpenAIEmbeddings
        from langchain_community.vectorstores import Chroma

        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large", base_url=self.base_url)
        self.fastsimcoal_vectorstore = Chroma(
            collection_name="fastsimcoal_collection",
            embedding_function=self.embeddings,
            persist_directory="./chroma_db/collection_fastsimcoal"
        )
        self.demes_vectorstore = Chroma(
            collection_name="demes_collection",
            embedding_function=self.embeddings,
            persist_directory="./chroma_db/collection_demes"
        )
        
        self.demes_agent_chain = self._create_agent_chain(
            """
You are a demes library expert. Generate VALID demographic model configurations.

## CRITICAL RULES FOR EPOCHS

### R1: Epoch Structure (PREVENTS "invalid epoch" ERROR)
Each epoch MUST have:
- end_time: When epoch ends (REQUIRED for all except final epoch)
- start_size: Population size at epoch start (REQUIRED)
- end_size: Population size at epoch end (OPTIONAL, defaults to start_size)
- size_function: constant, exponential, linear (OPTIONAL, default=exponential if sizes differ)

**CRITICAL**: Final epoch (present day) has NO end_time field!

### R2: Time Flow (PREVENTS temporal inconsistency)
Time flows BACKWARD from present (0) to past:
- Ancestral deme: end_time = divergence time (e.g., 2395)
- Child deme: starts at parent's end_time, grows to present (0)
- Child epochs: end_time must be GREATER than next epoch's end_time

### R3: Ancestor-Child Relationship
CORRECT example:
- Ancestral deme exists from 5000+ generations ago, ends at 5000
- Child deme starts at 5000, has epoch ending at 1000, then final epoch to present
- Final epoch has NO end_time field (represents present day)

WRONG example:
- Child deme ends at same time as parent (causes invalid epoch error)

### R4: Required Fields
Your JSON must have:
- time_units: generations
- generation_time: 1
- demes: list of deme objects
- Each deme: name, epochs list, optional ancestors
- Each epoch: start_size required, end_time required except for final epoch
- migrations: list of migration objects with source, dest, rate

### R5: Size Functions
- Constant size: start_size equals end_size OR only provide start_size
- Exponential growth: start_size differs from end_size (default)
- Linear growth: Add size_function field set to linear

## OUTPUT FORMAT
Pure JSON only, NO markdown blocks, NO explanations outside JSON.
            """
        )
        self.fastsimcoal_agent_chain = self._create_agent_chain(UNIFIED_FASTSIMCOAL_PROMPT)

    def _create_agent_chain(self, system_prompt: str):
        """Creates a reusable LangChain agent chain."""
        model = ChatOpenAI(model=self.model_name, base_url=self.base_url)
        parser = StrOutputParser()
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])
        return prompt_template | model | parser

    # --- Restored Methods to Fix AttributeError ---
    def create_comprehensive_param_agent(self):
        """Create comprehensive parameter generation agent for backward compatibility."""
        model = ChatOpenAI(model=self.model_name, base_url=self.base_url)
        parser = StrOutputParser()
        
        final_prompt = ChatPromptTemplate.from_messages([
            ("system", fastsimcoal_PROMPT),
            ("human", "{input}")
        ])
        
        return final_prompt | model | parser

    def create_comprehensive_script_agent(self):
        """Create comprehensive script generation agent for backward compatibility."""
        model = ChatOpenAI(model=self.model_name, base_url=self.base_url)
        parser = StrOutputParser()
        
        script_prompt = """
        You are a FastSimCoal2 script generation expert. Generate shell scripts for running FastSimCoal2 simulations and inference.
        
        Key requirements:
        1. Generate proper shell scripts with error handling
        2. Include file copying and cleanup operations
        3. Handle both simulation and inference modes
        4. Use appropriate FastSimCoal2 command line options
        
        Output format: Complete shell script ready for execution
        """
        
        final_prompt = ChatPromptTemplate.from_messages([
            ("system", script_prompt),
            ("human", "{input}")
        ])
        
        return final_prompt | model | parser
        
    def create_comprehensive_demes_agent(self):
        """Create comprehensive Demes configuration agent for backward compatibility."""
        return self.demes_agent_chain
    # -----------------------------------------

    @staticmethod
    def _write_file(file_path: str, content: str):
        """Writes content to a file, handling potential escape characters."""
        content = content.replace("```bash", "").replace("```", "").strip()
        content = content.replace("\\n", "\n")
        logging.info(f"Writing to {file_path}, content length: {len(content)}")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logging.info(f"Successfully wrote {len(content)} characters to {file_path}")
        except Exception as e:
            logging.error(f"Error writing to {file_path}: {e}")
            raise

    # MODIFICATION: The method now accepts the FscParams TypedDict for consolidated arguments and handles debugging.
    def generate_fastsimcoal_assets(self, params: FscParams) -> Dict[str, Any]:
        """Generates FastSimCoal2 config files (.tpl, .est) and the execution script."""
        try:
            # Retrieve related configuration examples from knowledge base
            goal = params["goal"]
            related_docs = self.fastsimcoal_vectorstore.max_marginal_relevance_search(goal, k=2, fetch_k=10)
            reference_examples = ""
            if related_docs:
                reference_examples = "\n--- Reference Examples from Knowledge Base ---\n"
                for i, doc in enumerate(related_docs):
                    config_name = doc.metadata.get('config_name', 'unknown')
                    reference_examples += f"\nExample {i+1} ({config_name}):\n{doc.page_content}\n\n"
            
            input_data = {
                "goal": params["goal"], 
                "report": params["report"], 
                "mode": params["mode"],
                "output_dir": params["output_dir"], 
                "file_prefix": params["file_prefix"],
                "reference_examples": reference_examples
            }
            if params["mode"] == "inference" and params.get("obs_files"):
                obs_files = params["obs_files"]
                obs_file_path = obs_files[0]  # Full obs file path
                input_data.update({
                    "obs_files": obs_files, 
                    "obs_file_path": obs_file_path,  # Add full path
                    "sfs_type": params["sfs_type"]
                })
                obs_basename = os.path.basename(obs_file_path)
                if "_MSFS.obs" in obs_basename:
                    input_data["expected_obs_name"] = f"{params['file_prefix']}_jointMAFpop1_0.obs"
                elif "_jointDAFpop1_0.obs" in obs_basename:
                    input_data["expected_obs_name"] = f"{params['file_prefix']}_DSFS.obs"
                else:
                    input_data["expected_obs_name"] = f"{params['file_prefix']}_jointMAFpop1_0.obs"

            # Add debug context to the input if it exists
            if params.get("debug_context"):
                input_data["debug_context"] = params["debug_context"]
                logging.info("Debugging context provided. Requesting corrected assets from LLM.")
            print("--------------------------------------------------------------------------------------")
            print(f"Input data keys: {list(input_data.keys())}")
            response = self.fastsimcoal_agent_chain.invoke({"input": json.dumps(input_data, indent=2, ensure_ascii=False)})
            print("--------------------------------------------------------------------------------------")
            print(response)
            result = json.loads(response)
            # result = json.loads(self._clean_json_response(response))
            
            # print(f"FastSimCoal agent response: {result}")
            # Use the robust cleaner to handle potentially malformed JSON from the LLM
            # cleaned_response = self._clean_json_response(response)
            # result = json.loads(cleaned_response)

            if not all(key in result for key in ["tpl", "est", "script"]):
                raise ValueError("Missing required keys ('tpl', 'est', 'script') in LLM response.")
            
            output_dir = params["output_dir"]
            file_prefix = params["file_prefix"]
            os.makedirs(output_dir, exist_ok=True)
            tpl_path = os.path.join(output_dir, f"{file_prefix}.tpl")
            est_path = os.path.join(output_dir, f"{file_prefix}.est")
            script_path = os.path.join(output_dir, "run_fastsimcoal.sh")

            self._write_file(tpl_path, result["tpl"])
            self._write_file(est_path, result["est"])
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(result["script"])
            os.chmod(script_path, 0o755)

            logging.info(f"Generated FastSimCoal2 assets: {tpl_path}, {est_path}, {script_path}")
            
            # Return generated content for potential use in debugging and the LLM's analysis
            return {
                "success": True, "tpl_path": tpl_path, "est_path": est_path,
                "script_path": script_path, "script_content": result["script"],
                "tpl_content": result["tpl"], "est_content": result["est"],
                "analysis": result.get("analysis", "Assets generated successfully on the first attempt.")
            }
        except Exception as e:
            logging.error(f"Failed to generate FastSimCoal2 assets: {e}")
            return {"success": False, "error": str(e), "analysis": f"Asset generation failed with error: {e}"}

    def generate_and_visualize_demes_model(self, goal: str, output_dir: str, analysis_results: Dict[str, str],
                                            fastsimcoal_results: Optional[Dict] = None,
                                            is_inference_mode: bool = False, file_prefix: Optional[str] = None) -> Optional[str]:
        """Generates a Demes demographic model configuration and visualizes it."""
        try:
            # RAG: Find similar demes configurations
            related_docs = self.demes_vectorstore.max_marginal_relevance_search(goal, k=3, fetch_k=20)
            reference_examples = "\n\n--- No reference examples found in knowledge base ---\n"
            if related_docs:
                reference_examples = "\n\n--- Reference Examples from Knowledge Base ---\n"
                for i, doc in enumerate(related_docs):
                    filename = doc.metadata.get('filename', 'unknown')
                    reference_examples += f"\nExample {i+1} (from {filename}):\n{doc.page_content}\n--- End of Example {i+1} ---\n"
            
            input_data = {
                "goal": goal,
                "analysis_results": analysis_results,
                "reference_examples": reference_examples,
                "fastsimcoal_results": fastsimcoal_results,
                "is_inference_mode": is_inference_mode,
                "file_prefix": file_prefix
            }
            
            response = self.demes_agent_chain.invoke({"input": json.dumps(input_data)})
            demes_config = json.loads(self._clean_json_response(response))
            self._validate_demes_config(demes_config)
            
            # Fix time_units and generation_time compatibility
            if demes_config.get('time_units') == 'generations':
                # If time_units is generations, generation_time must be 1
                demes_config['generation_time'] = 1
                logging.info("Fixed demes config: set generation_time=1 for time_units='generations'")
            elif demes_config.get('generation_time') and demes_config.get('generation_time') != 1:
                # If generation_time is not 1, time_units must be years
                demes_config['time_units'] = 'years'
                if 'generation_time' not in demes_config:
                    demes_config['generation_time'] = 25  # Default for humans
                logging.info(f"Fixed demes config: set time_units='years' for generation_time={demes_config.get('generation_time')}")

            yaml_filename = f"{file_prefix}.yaml" if is_inference_mode and file_prefix else "demographic_model.yaml"
            yaml_path = os.path.join(output_dir, yaml_filename)
            with open(yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(demes_config, f)

            # Generate visualization
            graph = demes.load(yaml_path)
            fig, ax = plt.subplots(figsize=(10, 8))
            demesdraw.tubes(graph, ax=ax)
            plot_path = os.path.join(output_dir, "demographic_model.png")
            fig.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            
            logging.info(f"Demes model and plot generated: {plot_path}")
            return plot_path
        except Exception as e:
            logging.error(f"Demes model generation and visualization failed: {e}")
            return None

    @staticmethod
    def _validate_demes_config(demes_config: Dict[str, Any]):
        """Validates that demes configuration uses only allowed fields in epochs."""
        allowed_fields = {'end_time', 'start_size', 'end_size', 'size_function', 'cloning_rate', 'selfing_rate'}
        forbidden_fields = {'start_time'}
        if 'demes' in demes_config:
            for i, deme in enumerate(demes_config.get('demes', [])):
                for j, epoch in enumerate(deme.get('epochs', [])):
                    for field in epoch:
                        if field in forbidden_fields:
                            raise ValueError(f"Demes[{i}].epochs[{j}]: forbidden field '{field}' found.")
                        if field not in allowed_fields:
                            logging.warning(f"Demes[{i}].epochs[{j}]: unknown field '{field}' found.")

    @staticmethod
    def _clean_json_response(response: str) -> str:
        """Cleans and extracts a JSON object from a string, with robust fallback."""
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]
        
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            json_part = response[start_idx:end_idx + 1]
            try:
                json.loads(json_part)
                return json_part
            except json.JSONDecodeError:
                logging.warning("Initial JSON parsing failed, attempting to fix format.")
                try:
                    fixed_json = ModelingAgent._fix_json_format(json_part)
                    json.loads(fixed_json)
                    return fixed_json
                except (json.JSONDecodeError, Exception) as e:
                    logging.error(f"JSON fixing failed: {e}. Returning original response part.")
                    return json_part
        logging.error("Could not find a valid JSON object in the response.")
        return response

    @staticmethod
    def _fix_json_format(json_str: str) -> str:
        """Fixes common JSON formatting issues using regex."""
        json_str = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', json_str)
        json_str = re.sub(r":\s*'([^']*)'", r': "\1"', json_str)
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        return json_str

    def analyze_image(self, image_path: str, goal: str, image_type: str = "general") -> str:
        """Analyzes an image using a multimodal model."""
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            if image_type == "demographic_model":
                text_prompt = DEMOGRAPHIC_MODEL_ANALYSIS_PROMPT.format(goal=goal)
                model_name = self.model_name
                max_tokens = 2000
            else:
                text_prompt = GENERAL_IMAGE_ANALYSIS_PROMPT.format(goal=goal)
                model_name = 'claude-sonnet-4-20250514'
                max_tokens = 3000

            vision_model = ChatOpenAI(model=model_name, base_url=self.base_url, max_tokens=max_tokens)
            message = HumanMessage(content=[
                {"type": "text", "text": text_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}", "detail": "high"}}
            ])
            response = vision_model.invoke([message])
            return response.content
        except Exception as e:
            logging.error(f"Image analysis failed for {image_path}: {e}")
            return f"Unable to analyze image due to an error: {e}"

    def analyze_demographic_model_image(self, image_path: str, goal: str) -> str:
        """Wrapper for analyzing a demographic model image."""
        return self.analyze_image(image_path, goal, "demographic_model")


class IntegratedPopGenWorkflow:
    """Manages the integrated population genetics analysis workflow using LangGraph."""

    def __init__(self, api_key: str, base_url: str, model: str = "claude-opus-4-1-20250805"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        
        self.modeling_agent = ModelingAgent(api_key, base_url, model)
        
        self._load_demes_knowledge_base()
        self._load_fastsimcoal_knowledge_base()
        
        self.workflow = self._build_workflow()
        self.checkpointer = MemorySaver()
        self.app = self.workflow.compile(checkpointer=self.checkpointer)

    def _add_documents_to_vectorstore(self, documents: List[Dict], collection: Any, collection_name: str):
        """Adds documents to a Chroma vectorstore collection if they don't already exist."""
        import uuid
        new_texts, new_metadatas, new_ids = [], [], []
        existing_ids = set(collection.get(include=[])['ids'])

        for doc in documents:
            content_hash = hash(doc['page_content'])
            doc_id = doc['metadata'].get("id", f"{collection_name}_{doc['metadata'].get('filename', 'doc')}_{content_hash}")
            
            if doc_id not in existing_ids:
                new_texts.append(doc['page_content'])
                new_metadatas.append(doc['metadata'])
                new_ids.append(doc_id)

        if new_texts:
            collection.add_texts(texts=new_texts, metadatas=new_metadatas, ids=new_ids)
            logging.info(f"Added {len(new_texts)} new documents to the '{collection_name}' collection.")
        else:
            logging.info(f"All documents already exist in the '{collection_name}' collection.")

    def _load_demes_knowledge_base(self):
        """Loads demes YAML files from the knowledge base directory into the vectorstore."""
        self._load_knowledge_base(
            doc_dir="./knowledge/demes",
            file_pattern="**/*.y*ml",
            collection=self.modeling_agent.demes_vectorstore,
            collection_name="demes",
            content_processor=lambda content, path: content,
            metadata_builder=lambda path: {'type': 'demes_yaml', 'filename': os.path.basename(path)}
        )

    def _load_fastsimcoal_knowledge_base(self):
        """Loads FastSimCoal configuration sets from the knowledge base directory."""
        doc_dir = "./knowledge/fastsimcoal"
        if not os.path.exists(doc_dir):
            logging.warning(f"FastSimCoal knowledge base directory not found: {doc_dir}")
            return

        documents = []
        for txt_file in glob.glob(os.path.join(doc_dir, "*.txt")):
            base_name = os.path.splitext(os.path.basename(txt_file))[0]
            tpl_path = os.path.join(doc_dir, f"{base_name}.tpl")
            est_path = os.path.join(doc_dir, f"{base_name}.est")
            
            if all(os.path.exists(p) for p in [tpl_path, est_path]):
                with open(txt_file, 'r', encoding='utf-8') as f_txt, \
                     open(tpl_path, 'r', encoding='utf-8') as f_tpl, \
                     open(est_path, 'r', encoding='utf-8') as f_est:
                    
                    goal_desc = f_txt.read()
                    tpl_content = f_tpl.read()
                    est_content = f_est.read()
                    
                    combined_content = (
                        f"Configuration Set: {base_name}\n\n"
                        f"Goal/Description:\n{goal_desc}\n\n"
                        f"Template File (.tpl):\n{tpl_content}\n\n"
                        f"Estimation File (.est):\n{est_content}"
                    )
                    documents.append({
                        'page_content': combined_content,
                        'metadata': {
                            'config_name': base_name,
                            'type': 'fastsimcoal_config',
                            'goal': goal_desc.strip()
                        }
                    })
            else:
                logging.warning(f"Incomplete FastSimCoal config set for '{base_name}', skipping.")
        
        if documents:
            self._add_documents_to_vectorstore(documents, self.modeling_agent.fastsimcoal_vectorstore, "fastsimcoal")

    def _load_knowledge_base(self, doc_dir: str, file_pattern: str, collection: Any, collection_name: str, content_processor, metadata_builder):
        """Generic helper to load documents from a directory into a vectorstore."""
        if not os.path.exists(doc_dir):
            logging.warning(f"Knowledge base directory not found: {doc_dir}")
            return
        
        documents = []
        for file_path in glob.glob(os.path.join(doc_dir, file_pattern), recursive=True):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                documents.append({
                    'page_content': content_processor(content, file_path),
                    'metadata': metadata_builder(file_path)
                })
            except Exception as e:
                logging.error(f"Error loading knowledge base file {file_path}: {e}")
        
        if documents:
            self._add_documents_to_vectorstore(documents, collection, collection_name)

    def _build_workflow(self) -> StateGraph:
        """Builds the LangGraph workflow with sequential analysis nodes."""
        workflow = StateGraph(AnalysisState)
        
        workflow.add_node("obs_agent", self.obs_agent_node)
        workflow.add_node("single_pop_agent", self.single_pop_agent_node)
        
        workflow.add_node("pca_agent", self._create_analysis_node(run_pca_agent, "pca_agent_result", "pca"))
        workflow.add_node("treemix_agent", self._create_analysis_node(run_treemix_agent, "treemix_agent_result", "treemix"))
        workflow.add_node("admixture_agent", self._create_analysis_node(run_admixture_agent, "admixture_agent_result", "admixture"))
        workflow.add_node("other_analysis_agent", self._create_analysis_node(run_other_analysis_agent, "other_analysis_agent_result", "other_analysis"))
        
        workflow.add_node("final_integration", self.final_integration_node)
        
        workflow.set_entry_point("final_integration")
        # Define the workflow graph
        # workflow.set_entry_point("obs_agent")
        # workflow.add_edge("obs_agent", "single_pop_agent")
        # workflow.add_edge("single_pop_agent", "pca_agent")
        # workflow.add_edge("pca_agent", "treemix_agent")
        # workflow.add_edge("treemix_agent", "admixture_agent")
        # workflow.add_edge("admixture_agent", "other_analysis_agent")
        # workflow.add_edge("other_analysis_agent", "final_integration")
        # workflow.add_edge("final_integration", END)
        
        return workflow

    def _create_analysis_node(self, agent_func: Callable, result_key: str, report_key: str) -> Callable[[AnalysisState], AnalysisState]:
        """Factory function to create a standard analysis node for the graph."""
        def node_runner(state: AnalysisState) -> AnalysisState:
            agent_name = result_key.replace("_result", "")
            logging.info(f"Executing {agent_name}...")
            try:
                result = agent_func(
                    goal=state["goal"],
                    output_id=state["output_id"],
                    api_key=self.api_key,
                    base_url=self.base_url,
                    model="gpt-4-vision-preview" 
                )
                state[result_key] = result
                state["completed_agents"] = state.get("completed_agents", []) + [agent_name]
                if result.get("success"):
                    logging.info(f"{agent_name} completed successfully.")
                    analysis_text = result.get("analysis_text")
                    if analysis_text:
                        reports = state.get("analysis_reports", {})
                        reports[report_key] = analysis_text
                        state["analysis_reports"] = reports
                else:
                    logging.error(f"{agent_name} failed: {result.get('analysis', 'Unknown error')}")
                    state["failed_agents"] = state.get("failed_agents", []) + [agent_name]
            except Exception as e:
                logging.error(f"{agent_name} execution crashed: {e}", exc_info=True)
                state[result_key] = {"success": False, "error": str(e)}
                state["failed_agents"] = state.get("failed_agents", []) + [agent_name]
            return state
        return node_runner

    def obs_agent_node(self, state: AnalysisState) -> AnalysisState:
        """Executes the obs_agent to convert data to .obs files."""
        logging.info("Executing obs_agent...")
        try:
            result = run_obs_agent(
                goal=state["goal"], datalist=state["datalist"], output_id=state["output_id"],
                api_key=self.api_key, base_url=self.base_url, model=self.model, max_retries=3
            )
            state["obs_agent_result"] = result
            state["completed_agents"] = state.get("completed_agents", []) + ["obs_agent"]
            if not result.get("success"):
                logging.error(f"obs_agent failed: {result.get('analysis', 'Unknown error')}")
                state["failed_agents"] = state.get("failed_agents", []) + ["obs_agent"]
        except Exception as e:
            logging.error(f"obs_agent execution crashed: {e}", exc_info=True)
            state["obs_agent_result"] = {"success": False, "error": str(e)}
            state["failed_agents"] = state.get("failed_agents", []) + ["obs_agent"]
        return state

    def single_pop_agent_node(self, state: AnalysisState) -> AnalysisState:
        """Executes the single_pop_agent for single population analysis."""
        logging.info("Executing single_pop_agent...")
        try:
            result = run_single_pop_agent(
                goal=state["goal"], output_id=state["output_id"], api_key=self.api_key,
                base_url=self.base_url, model=self.model, max_retries=3
            )
            state["single_pop_agent_result"] = result
            state["completed_agents"] = state.get("completed_agents", []) + ["single_pop_agent"]
            if not result.get("success"):
                logging.error(f"single_pop_agent failed: {result.get('analysis', 'Unknown error')}")
                state["failed_agents"] = state.get("failed_agents", []) + ["single_pop_agent"]
        except Exception as e:
            logging.error(f"single_pop_agent execution crashed: {e}", exc_info=True)
            state["single_pop_agent_result"] = {"success": False, "error": str(e)}
            state["failed_agents"] = state.get("failed_agents", []) + ["single_pop_agent"]
        return state

    def final_integration_node(self, state: AnalysisState) -> AnalysisState:
        """Integrates all results, performs final modeling, and generates the final report."""
        logging.info("Executing final integration node...")
        
        # 1. Run the modeling agent to get high-level recommendations
        try:
            modeling_result = run_modeling_agent(
                goal=state["goal"], output_id=state["output_id"], ana_dir=state["ana_dir"],
                api_key=self.api_key, base_url=self.base_url, model=self.model
            )
            state["modeling_agent_result"] = modeling_result
            state["completed_agents"].append("modeling_agent")
        except Exception as e:
            logging.error(f"Modeling agent crashed: {e}", exc_info=True)
            state["modeling_agent_result"] = {"success": False, "error": str(e)}
            state["failed_agents"].append("modeling_agent")
        # 2. Perform final detailed modeling (FastSimCoal2 + Demes) based on recommendations
        if state["modeling_agent_result"].get("success"):
            logging.info("Proceeding with final detailed modeling...")
            try:
                final_modeling_result = self._perform_final_modeling(state)
                state["final_modeling_result"] = final_modeling_result
                logging.info(f"Final modeling complete. Success: {final_modeling_result.get('success', False)}")
            except Exception as e:
                logging.error(f"Final modeling step crashed: {e}", exc_info=True)
                state["final_modeling_result"] = {"success": False, "error": str(e)}
        else:
            logging.warning("Skipping final detailed modeling due to modeling_agent failure.")
            state["final_modeling_result"] = {"success": False, "error": "Prerequisite modeling_agent failed."}

        # final_modeling_result = self._perform_final_modeling(state)
        # state["final_modeling_result"] = final_modeling_result
        # 3. Generate the comprehensive final report
        state["final_analysis"] = self._generate_comprehensive_report(state)
        state["status"] = "completed"
        logging.info("Analysis workflow officially completed.")
        return state


    def run_analysis(self, goal: str, output_id: str, datalist: List[str]) -> str:
        """Entry point to run the complete integrated analysis workflow."""
        ana_dir = os.path.join("./output", output_id, "ana")
        os.makedirs(ana_dir, exist_ok=True)
        
        initial_state = AnalysisState(
            goal=goal,
            output_id=output_id,
            ana_dir=ana_dir,
            datalist=datalist,
            completed_agents=[],
            failed_agents=[],
            analysis_reports={},
            status="running",
            obs_agent_result=None, single_pop_agent_result=None, pca_agent_result=None,
            treemix_agent_result=None, admixture_agent_result=None, other_analysis_agent_result=None,
            modeling_agent_result=None, final_modeling_result=None, final_analysis=""
        )
        
        try:
            config = {"configurable": {"thread_id": f"analysis_{output_id}"}}
            final_state = self.app.invoke(initial_state, config=config)
            return final_state.get("final_analysis", "Workflow finished but no final report was generated.")
        except Exception as e:
            logging.error(f"Workflow execution failed with an unhandled exception: {e}", exc_info=True)
            return f"Error: The analysis workflow failed unexpectedly. Details: {e}"

    def _generate_comprehensive_report(self, state: AnalysisState) -> str:
        """Generates the final, comprehensive analysis report in Markdown format."""
        report_parts = [
            f"# Integrated Population Genetics Analysis Report",
            f"**Analysis Goal**: {state['goal']}",
            f"**Analysis ID**: {state['output_id']}",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## Execution Summary",
            f"- **Completed Agents**: {', '.join(state.get('completed_agents', [])) or 'None'}",
            f"- **Failed Agents**: {', '.join(state.get('failed_agents', [])) or 'None'}",
        ]

        # ... (code for appending other reports remains unchanged)

        # Append modeling recommendations
        modeling_result = state.get("modeling_agent_result", {})
        if modeling_result: # Only add this section if the agent was run
            report_parts.append("\n## Demographic Modeling Recommendations")
            if modeling_result.get("success"):
                report_parts.append(modeling_result.get("modeling_recommendations", "Modeling recommendations were generated successfully."))
            else:
                report_parts.append(f"❌ Failed to generate modeling recommendations. Error: {modeling_result.get('error', 'Unknown error')}")

        # Append final demographic model analysis and visualization
        final_modeling_result = state.get("final_modeling_result", {})
        report_parts.append("\n## Final Demographic Modeling")
        
        status = final_modeling_result.get("status", "false")
        analysis_text = final_modeling_result.get("analysis", "No analysis was performed.")
        
        report_parts.append(f"**Modeling Status**: {'✅ Success' if status == 'true' else '❌ Failed'}")
        report_parts.append(f"**Debugging Analysis**:\n\n> {analysis_text.replace(chr(10), ' ' + chr(10) + '> ')}\n")
        
        if status == 'true':
            demes_plot_path = final_modeling_result.get("demes_plot_path")
            if demes_plot_path and os.path.exists(demes_plot_path):
                report_parts.append("\n### Final Demographic Model")
                model_analysis = self.modeling_agent.analyze_demographic_model_image(demes_plot_path, state['goal'])
                report_parts.append(model_analysis)
                web_path = self._get_web_path(demes_plot_path)
                report_parts.append(f"\n![Demographic Model]({web_path})")

        return "\n".join(report_parts)
    
    @staticmethod
    def _get_web_path(local_path: str) -> str:
        """Converts a local file path to a web-accessible path."""
        dev_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
        relative_path = os.path.relpath(local_path, '.').replace('\\', '/')
        if os.path.exists(dev_env_path):
            return f"/{relative_path}"
        return f"../{relative_path}"

    # MODIFICATION: This entire method is refactored to include likelihood-based optimization.
    def _perform_final_modeling(self, state: AnalysisState) -> Dict[str, Any]:
        """Orchestrates FastSimCoal2 config, execution (with likelihood-based optimization), and Demes generation."""
        output_id = state["output_id"]
        goal = state["goal"]
        ana_dir = state["ana_dir"]
        max_retries = 10
        attempt = 0
        
        # Track only essential information - memory efficient for 100 iterations
        recent_attempts = []  # Keep only last 2 attempts with full content
        best_likelihood = float('inf')
        best_result = None
        best_timestamp = None  # Timestamp of best result directory
        
        # Lightweight tracking: only timestamps and likelihoods
        all_attempt_summary = []  # List of {attempt, likelihood, timestamp, success}
        
        debug_context = None
        config_result = {}
        execution_result = {}
        analysis_log = "Modeling process initiated with likelihood-based optimization."

        obs_files = self._detect_obs_files(ana_dir)
        is_inference_mode = bool(obs_files)
        mode = "inference" if is_inference_mode else "simulation"
        
        if is_inference_mode:
            file_prefix = self._extract_file_prefix_from_obs(obs_files[0])
            sfs_type = self._detect_sfs_type(obs_files[0])
            logging.info(f"Inference mode detected: prefix={file_prefix}, sfs_type={sfs_type}")
        else:
            file_prefix = f"simulation_{output_id}"
            sfs_type = None
            logging.info(f"Simulation mode detected: prefix={file_prefix}")

        modeling_report_path = os.path.join(ana_dir, "modeling_report.txt")
        modeling_report = ""
        if os.path.exists(modeling_report_path):
            with open(modeling_report_path, 'r', encoding='utf-8') as f:
                modeling_report = f.read()

        while attempt < max_retries:
            attempt += 1
            logging.info(f"--- Starting Modeling Attempt #{attempt} (Best likelihood so far: {best_likelihood:.2f}) ---")

            # 1. Generate FastSimCoal2 assets (with model search context)
            fsc_params: FscParams = {
                "goal": goal, "report": modeling_report, "mode": mode, "output_dir": ana_dir,
                "file_prefix": file_prefix, "obs_files": obs_files, "sfs_type": sfs_type,
                "debug_context": debug_context
            }
            config_result = self.modeling_agent.generate_fastsimcoal_assets(fsc_params)
            
            if not config_result.get("success"):
                analysis_log = config_result.get("analysis", "Failed to generate FSC assets.")
                logging.error(f"Attempt {attempt}: Asset generation failed. Error: {config_result.get('error')}")
                debug_context = None 
                continue

            analysis_log = config_result.get("analysis", "Assets generated.")
            script_path = config_result.get("script_path", "")
            
            # 2. Execute FastSimCoal2 script
            execution_result = self._execute_fastsimcoal_script(script_path)
            
            # 3. Analyze execution result
            stdout = execution_result.get('stdout', '')
            stderr = execution_result.get('stderr', '')
            has_convergence_issue = "MRCA not found" in stderr or "did not converge" in stderr
            current_likelihood = self._extract_likelihood(execution_result)
            
            # Extract timestamp from execution result directory
            current_timestamp = self._extract_timestamp_from_result(execution_result, ana_dir, file_prefix)
            
            # Record lightweight summary for all attempts
            attempt_summary = {
                "attempt": attempt,
                "likelihood": current_likelihood if current_likelihood else float('inf'),
                "success": execution_result.get("success") and not has_convergence_issue,
                "timestamp": current_timestamp,
                "convergence_issue": has_convergence_issue
            }
            all_attempt_summary.append(attempt_summary)
            
            # Record full attempt data (only keep last 2)
            attempt_record = {
                "attempt": attempt,
                "likelihood": current_likelihood if current_likelihood else float('inf'),
                "success": execution_result.get("success") and not has_convergence_issue,
                "params": execution_result.get("bestlhoods_params"),
                "tpl": config_result.get("tpl_content"),
                "est": config_result.get("est_content"),
                "timestamp": current_timestamp
            }
            recent_attempts.append(attempt_record)
            # Keep only last 2 attempts
            if len(recent_attempts) > 2:
                recent_attempts.pop(0)
            
            # Update best result if this is better
            if attempt_summary["success"] and current_likelihood and current_likelihood < best_likelihood:
                best_likelihood = current_likelihood
                best_result = execution_result
                best_timestamp = current_timestamp
                logging.info(f"🎯 New best likelihood found: {best_likelihood:.2f} (timestamp: {best_timestamp})")
            
            if execution_result.get("success") and not has_convergence_issue:
                # Execution succeeded with no convergence issues
                if attempt < max_retries:
                    # Perform model search optimization based on attempt history
                    logging.info(f"Attempt {attempt}: Success! Performing model search optimization...")
                    debug_context = self._prepare_model_search_context(
                        recent_attempts, all_attempt_summary, goal, modeling_report
                    )
                else:
                    # Last attempt, use best result
                    if best_result:
                        execution_result = best_result
                        logging.info(f"Using best result from attempt history (likelihood: {best_likelihood:.2f}, timestamp: {best_timestamp})")
                    break
            elif execution_result.get("success") and has_convergence_issue:
                # Execution succeeded but has convergence issues
                logging.warning(f"Attempt {attempt}: Convergence issues detected.")
                debug_context = {
                    "error_log": f"CONVERGENCE ISSUES:\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}",
                    "convergence_issue": True,
                    "previous_tpl": config_result.get("tpl_content"),
                    "previous_est": config_result.get("est_content"),
                    "recent_attempts": recent_attempts  # Only last 2 attempts
                }
            else:
                # Execution failed
                logging.warning(f"Attempt {attempt}: Execution FAILED.")
                debug_context = {
                    "error_log": f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}",
                    "previous_tpl": config_result.get("tpl_content"),
                    "previous_est": config_result.get("est_content"),
                    "recent_attempts": recent_attempts  # Only last 2 attempts
                }
        
        # 4. Use best result for final analysis
        if best_result:
            execution_result = best_result
            successful_attempts = [s for s in all_attempt_summary if s["success"]]
            analysis_log += (
                f"\n\nModel search completed over {len(all_attempt_summary)} attempts "
                f"({len(successful_attempts)} successful).\n"
                f"Best likelihood: {best_likelihood:.2f} (from run_{best_timestamp})"
            )
            logging.info(f"Final: Using best result from run_{best_timestamp}")
        
        # 5. Process final results
        if not execution_result.get("success") or best_likelihood == float('inf'):
            logging.error(f"Modeling failed after {attempt} attempts.")
            return {
                "status": "false",
                "analysis": analysis_log + f"\n\nNo successful models found after {attempt} attempts.",
                "execution_result": execution_result,
                "demes_plot_path": None
            }

        # 6. Generate and visualize Demes model using BEST result
        demes_plot_path = self.modeling_agent.generate_and_visualize_demes_model(
            goal=goal, output_dir=ana_dir, analysis_results=state.get("analysis_reports", {}),
            fastsimcoal_results=execution_result.get("bestlhoods_params"),
            is_inference_mode=is_inference_mode, file_prefix=file_prefix
        )
        
        return {
            "status": "true",
            "analysis": analysis_log,
            "execution_result": execution_result,
            "demes_plot_path": demes_plot_path,
            "best_likelihood": best_likelihood,
            "best_timestamp": best_timestamp,
            "total_attempts": len(all_attempt_summary),
            "successful_attempts": len([s for s in all_attempt_summary if s["success"]])
        }

    def _extract_timestamp_from_result(self, execution_result: Dict[str, Any], ana_dir: str, file_prefix: str) -> Optional[str]:
        """Extract timestamp from the result directory path."""
        if not execution_result.get("success"):
            return None
        
        # Look for run_TIMESTAMP directories in ana_dir
        run_dirs = glob.glob(os.path.join(ana_dir, "run_*"))
        if not run_dirs:
            return None
        
        # Get the most recent one (latest created)
        latest_run_dir = max(run_dirs, key=os.path.getmtime)
        dir_name = os.path.basename(latest_run_dir)
        
        # Extract timestamp from "run_20251010_160321" format
        if dir_name.startswith("run_"):
            return dir_name[4:]  # Remove "run_" prefix
        
        return None
    
    def _prepare_model_search_context(self, recent_attempts: List[Dict], all_attempt_summary: List[Dict], 
                                     goal: str, modeling_report: str) -> Dict[str, Any]:
        """Prepare context for model search optimization based on attempt history (memory efficient)."""
        # Get successful attempts from summary (lightweight)
        successful_summaries = [a for a in all_attempt_summary if a["success"]]
        successful_summaries.sort(key=lambda x: x["likelihood"])
        
        # Get recent successful attempts with full content
        recent_successful = [a for a in recent_attempts if a["success"]]
        recent_successful.sort(key=lambda x: x["likelihood"])
        
        # Analyze parameter trends from recent successful attempts only
        param_analysis = self._analyze_parameter_trends(recent_successful)
        
        context = {
            "model_search_mode": True,
            "attempt_count": len(all_attempt_summary),
            "successful_count": len(successful_summaries),
            "best_likelihood": successful_summaries[0]["likelihood"] if successful_summaries else float('inf'),
            "parameter_trends": param_analysis,
            "previous_models": [],
            "recent_timestamps": [a.get("timestamp") for a in recent_attempts[-2:] if a.get("timestamp")]
        }
        
        # Include up to 2 recent successful models with full content
        for i, attempt in enumerate(recent_successful[:2]):
            model_info = {
                "rank": i + 1,
                "likelihood": attempt["likelihood"],
                "params": attempt["params"],
                "tpl_snippet": attempt["tpl"][:500] if attempt["tpl"] else "",
                "est_snippet": attempt["est"][:500] if attempt["est"] else "",
                "timestamp": attempt.get("timestamp")
            }
            context["previous_models"].append(model_info)
        
        # Add optimization strategy
        if len(successful_summaries) >= 2:
            # Compare top 2 models (from summary)
            best = successful_summaries[0]
            second = successful_summaries[1]
            likelihood_diff = second["likelihood"] - best["likelihood"]
            
            context["optimization_strategy"] = (
                f"Model search iteration {len(all_attempt_summary)}. "
                f"Best overall likelihood: {best['likelihood']:.2f} (from attempt #{best['attempt']}), "
                f"second best: {second['likelihood']:.2f} (diff: {likelihood_diff:.2f}). "
                "Analyze parameter differences from recent models and explore variations that might improve likelihood further. "
                "Consider: 1) Adjusting time parameter ranges based on best estimates, "
                "2) Testing alternative migration patterns, "
                "3) Exploring different population size change scenarios. "
                "DO NOT simply copy previous models - innovate based on trends. "
                "🚨 CRITICAL: Ensure TEXP < all TDIV values to prevent hang!"
            )
        else:
            best_lhood_str = f"{successful_summaries[0]['likelihood']:.2f}" if successful_summaries else "none"
            context["optimization_strategy"] = (
                f"Attempt {len(all_attempt_summary)}. "
                f"Best likelihood so far: {best_lhood_str}. "
                "Try alternative model structures: 1) Different migration matrices, "
                "2) Additional bottleneck events, 3) Adjusted divergence time ordering. "
                "Explore parameter space systematically. "
                "🚨 CRITICAL: Ensure TEXP < all TDIV values to prevent hang!"
            )
        
        return context
    
    @staticmethod
    def _analyze_parameter_trends(successful_attempts: List[Dict]) -> Dict[str, Any]:
        """Analyze parameter trends from successful model attempts."""
        if not successful_attempts:
            return {}
        
        # Extract parameter values from attempts
        all_params = {}
        for attempt in successful_attempts:
            if attempt["params"]:
                for key, value in attempt["params"].items():
                    if key not in ['MaxEstLhood', 'MaxObsLhood'] and isinstance(value, (int, float)):
                        if key not in all_params:
                            all_params[key] = []
                        all_params[key].append(value)
        
        # Calculate statistics for each parameter
        trends = {}
        for param_name, values in all_params.items():
            if len(values) > 0:
                trends[param_name] = {
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / len(values),
                    "best_value": values[0] if values else None  # Value from best model
                }
        
        return trends
    
    @staticmethod
    def _detect_obs_files(ana_dir: str) -> List[str]:
        """Detects .obs files in the data directory, prioritizing multi-SFS files."""
        data_dir = os.path.join(ana_dir, "data")
        if not os.path.exists(data_dir): return []
        
        obs_files = glob.glob(os.path.join(data_dir, "*.obs"))
        msfs_files = [f for f in obs_files if '_MSFS.obs' in os.path.basename(f)]
        return msfs_files if msfs_files else obs_files

    @staticmethod
    def _extract_file_prefix_from_obs(obs_file: str) -> str:
        """Extracts the file prefix from an .obs filename."""
        basename = os.path.basename(obs_file)
        for suffix in ["_MSFS.obs", "_DSFS.obs", "_jointMAFpop1_0.obs", "_jointDAFpop1_0.obs", ".obs"]:
            if basename.endswith(suffix):
                return basename[:-len(suffix)]
        return os.path.splitext(basename)[0]

    @staticmethod
    def _detect_sfs_type(obs_file: str) -> str:
        """Detects SFS type (MAF or DAF) from the filename."""
        basename = os.path.basename(obs_file).upper()
        if "DAF" in basename or "_DSFS" in basename:
            return "DAF"
        return "MAF"

    def _execute_fastsimcoal_script(self, script_path: str) -> Dict[str, Any]:
        """Executes the FastSimCoal2 script and captures the results."""
        if not script_path or not os.path.exists(script_path):
            return {"success": False, "error": "Script file not found", "stderr": "Script file not found"}
        
        try:
            logging.info(f"Executing FastSimCoal2 script: {script_path}")
            # Ensure script is executable
            os.chmod(script_path, 0o755)
            result = subprocess.run(["bash", script_path], capture_output=True, text=True, check=False)
            
            logging.info(f"FastSimCoal2 exited with code {result.returncode}")
            # MODIFICATION: Log stdout and stderr regardless of exit code for better debugging
            if result.stdout: logging.info(f"FSC2 STDOUT:\n{result.stdout}")
            if result.stderr: logging.warning(f"FSC2 STDERR:\n{result.stderr}")
            
            output = {"success": result.returncode == 0, "returncode": result.returncode,
                      "stdout": result.stdout, "stderr": result.stderr}
            
            if output["success"]:
                run_dir = os.path.dirname(script_path)
                bestlhoods_files = glob.glob(os.path.join(run_dir, "*", "*.bestlhoods"))
                if bestlhoods_files:
                    latest_bestlhoods = max(bestlhoods_files, key=os.path.getmtime)
                    output["bestlhoods_params"] = self._parse_bestlhoods_file(latest_bestlhoods)
            
            return output
        except Exception as e:
            logging.error(f"Failed to execute FastSimCoal2 script: {e}", exc_info=True)
            return {"success": False, "error": str(e), "stderr": str(e)}

    @staticmethod
    def _extract_likelihood(execution_result: Dict[str, Any]) -> Optional[float]:
        """Extract likelihood value from execution result"""
        bestlhoods = execution_result.get("bestlhoods_params")
        if bestlhoods and isinstance(bestlhoods, dict):
            return bestlhoods.get("MaxEstLhood") or bestlhoods.get("MaxObsLhood")
        return None

    @staticmethod
    def _parse_bestlhoods_file(file_path: str) -> Optional[Dict[str, Any]]:
        """Parses a .bestlhoods file to extract parameter estimates."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if len(lines) < 2: return None
            
            headers = lines[0].strip().split('\t')
            values = lines[1].strip().split('\t')
            if len(headers) != len(values): return None
            
            params = {}
            for header, value in zip(headers, values):
                try:
                    params[header] = float(value) if '.' in value or 'e' in value.lower() else int(value)
                except ValueError:
                    params[header] = value
            return params
        except Exception as e:
            logging.error(f"Error parsing .bestlhoods file {file_path}: {e}")
            return None


def run_integrated_analysis(goal: str, output_id: str, datalist: List[str],
                            api_key: str, base_url: str,
                            model: str = "claude-opus-4-1-20250805") -> str:
    """
    Convenience function to initialize and run the integrated population genetics workflow.
    
    Args:
        goal: The main objective of the analysis.
        output_id: A unique identifier for the analysis run.
        datalist: A list of input data file paths (e.g., BED/BIM/FAM).
        api_key: The API key for LLM services.
        base_url: The base URL for the LLM API endpoint.
        model: The name of the language model to use.
    
    Returns:
        A string containing the comprehensive analysis report in Markdown format.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    workflow = IntegratedPopGenWorkflow(api_key, base_url, model)
    return workflow.run_analysis(goal, output_id, datalist)


# Example usage for testing
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from config_loader import get_llm_config
    cfg = get_llm_config()

    print("Testing Integrated Population Genetics Analysis Workflow...")

    test_datalist = [
        "./data/1000GP_pruned.bed",
        "./data/1000GP_pruned.bim",
        "./data/1000GP_pruned.fam",
    ]

    final_report = run_integrated_analysis(
        goal="I have data for YRI, CEU, and CHB populations. Please infer a migration and separation model for these three populations based on the provided data.",
        output_id=f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        datalist=test_datalist,
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        model=cfg.get("default_model", "claude-opus-4-1-20250805"),
    )

    print("\n" + "=" * 80)
    print("Analysis Completed!")
    print("=" * 80)
    print(final_report)
    print("=" * 80)