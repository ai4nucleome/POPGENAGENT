import os
import json
import glob
import yaml
import demes
import demesdraw
import matplotlib.pyplot as plt
import uuid
import logging
import subprocess
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import math

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
import base64
from langchain.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain import hub
from langchain_community.tools import ShellTool
from langchain_community.document_loaders.text import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from mem0 import Memory

from .prompts import ANA_PROMPT, fastsimcoal_examples, fastsimcoal_PROMPT
from .modelingagent import IntegratedPopGenWorkflow, ModelingAgent



class AnaAgent:
    def __init__(self, api_key: str, base_url: str, Model: str = "claude-opus-4-1-20250805-thinking", chroma_db_dir: str = './chroma_db'):
        self.model_name = Model
        self.base_url = base_url
        self.chroma_db_dir = chroma_db_dir
        os.environ['OPENAI_API_KEY'] = api_key
        self.prompt_template = ANA_PROMPT
        # self.agent = self._create_agent(self.prompt_template)
        
        self.fastsimcoal_examples = fastsimcoal_examples
        self.prompt_template = fastsimcoal_PROMPT

        
        # Initialize modeling agent for all specialized agents
        self.modeling_agent = ModelingAgent(api_key, base_url, Model)
        self.param_agent = self.modeling_agent.create_comprehensive_param_agent()
        self.script_agent = self.modeling_agent.create_comprehensive_script_agent()
        self.demes_agent = self.modeling_agent.create_comprehensive_demes_agent()

        # Initialize LangGraph workflow
        self.langgraph_workflow = IntegratedPopGenWorkflow(api_key, base_url, Model)

        self.doc_dir = "knowledge"
        
        # self.mem0 = Memory()

        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large", base_url=self.base_url)

        # Collection names for vector stores
        self.demes_collection_name = "demes_collection"
        self.fastsimcoal_collection_name = "fastsimcoal_collection"

        
        # Initialize demes-specific vector store
        self.demes_vectorstore = Chroma(
            collection_name=self.demes_collection_name,
            embedding_function=self.embeddings,
            persist_directory=os.path.join(self.chroma_db_dir, "collection_demes")
        )
        
        # Initialize fastsimcoal-specific vector store
        self.fastsimcoal_vectorstore = Chroma(
            collection_name=self.fastsimcoal_collection_name,
            embedding_function=self.embeddings,
            persist_directory=os.path.join(self.chroma_db_dir, "collection_fastsimcoal")
        )


    
    def interpret_plan(self, goal, datalist, id, reference_images=None):
        """
        Interpret and execute analysis plan with optional reference images from previous analyses
        
        Args:
            goal (str): Analysis goal/objective
            datalist (list): List of data files
            id (str/int): Output ID
            reference_images (dict, optional): Dict of previous analysis images with metadata
                e.g. {
                    'admixtools': {'path': 'path/to/image.png', 'type': 'admixtools'},
                    'admixture': {'path': 'path/to/image.png', 'type': 'admixture'}
                }
        """
        logging.info(f"Starting analysis workflow for ID: {id}")
        
        # Detect input type
        input_type = self._detect_input_type(datalist)
        logging.info(f"Detected input type: {input_type}")

        try:
            if input_type == "obs_files":
                # Direct OBS file input - use enhanced workflow without obs_agent and single_pop_agent
                result = self.Run_Obs_Workflow(goal, datalist, str(id))
            else:
                # PLINK/VCF file input - use full integrated workflow
                result = self.Run_Fully_Workflow(goal, datalist, str(id))
            
            # Add image links to result
            image_dir = f"./output/{id}/ana"
            local_images = glob.glob(os.path.join(image_dir, "*.png")) + glob.glob(os.path.join(image_dir, "*.jpg"))
            if local_images:
                result += "\n\n## Generated Analysis Results\n"
                
                # Detect environment and adjust path configuration
                dev_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
                
                # 1. Show demographic model image first
                demographic_model_path = f"./output/{id}/ana/demographic_model.png"
                if os.path.exists(demographic_model_path):
                    if os.path.exists(dev_env_path):
                        demographic_model_web_path = f"/output/{id}/ana/demographic_model.png"
                    else:
                        demographic_model_web_path = f"../{demographic_model_path.lstrip('./')}"
                    result += f"\n### Demographic Model\n"
                    result += f"![Demographic Model]({demographic_model_web_path})\n\n"
            # Save analysis history (maintain compatibility)
            self.save_analysis_history(id, goal, result)
            
            logging.info(f"Enhanced analysis completed for ID: {id}")
            return result
            
        except Exception as e:
            error_msg = f"Enhanced analysis failed: {e}"
            logging.error(error_msg)
            import traceback
            traceback.print_exc()
            
            # Fallback to legacy method
            logging.info("Falling back to legacy analysis method")
            return self._legacy_interpret_plan(goal, datalist, id, reference_images)
    
    def _detect_input_type(self, datalist):
        """Detect the type of input files"""
        obs_files = [f for f in datalist if f.lower().endswith('.obs')]
        plink_files = [f for f in datalist if f.lower().endswith(('.bed', '.bim', '.fam'))]
        vcf_files = [f for f in datalist if f.lower().endswith('.vcf')]
        
        if obs_files:
            return "obs_files"
        elif plink_files or vcf_files:
            return "plink_vcf_files"
        else:
            return "unknown"
    
    def Run_Fully_Workflow(self, goal, datalist, output_id):
        """Run the full integrated workflow with obs_agent and single_pop_agent"""
        from .modelingagent import IntegratedPopGenWorkflow
        
        # Create the integrated workflow
        workflow = IntegratedPopGenWorkflow(
            api_key=os.environ.get('OPENAI_API_KEY', ''),
            base_url=self.base_url,
            model=self.model_name
        )
        
        # Run the full workflow
        result = workflow.run_analysis(goal, output_id, datalist)
        return result
    
    def Run_Obs_Workflow(self, goal, datalist, output_id):
        """Run enhanced workflow with direct OBS files, skipping obs_agent and single_pop_agent"""
        from .modeling.pca_agent import run_pca_agent
        from .modeling.treemix_agent import run_treemix_agent
        from .modeling.admixture_agent import run_admixture_agent
        from .modeling.other_analysis_agent import run_other_analysis_agent
        from .modeling.modeling_agent import run_modeling_agent
        
        # Create ana directory
        ana_dir = f"./output/{output_id}/ana"
        os.makedirs(ana_dir, exist_ok=True)
        
        # Copy OBS files to ana/data directory
        data_dir = os.path.join(ana_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        obs_files = [f for f in datalist if f.lower().endswith('.obs')]
        plink_files = [f for f in datalist if f.lower().endswith(('.bed', '.bim', '.fam'))]
        copied_obs_files = []
        
        for obs_file in obs_files:
            if os.path.exists(obs_file):
                # Copy to data directory
                dest_path = os.path.join(data_dir, os.path.basename(obs_file))
                import shutil
                shutil.copy2(obs_file, dest_path)
                copied_obs_files.append(dest_path)
                print(f"Copied OBS file: {obs_file} -> {dest_path}")
        
        if not copied_obs_files:
            return "Error: No valid OBS files found in input"
        
        # Run image analysis agents in sequence
        analysis_results = {}
        
        # PCA Agent
        try:
            print("Running PCA Agent...")
            pca_result = run_pca_agent(
                goal=goal,
                output_id=output_id,
                api_key=os.environ.get('OPENAI_API_KEY', ''),
                base_url=self.base_url,
                model="gpt-4-vision-preview"
            )
            if pca_result.get("success", False):
                analysis_results["pca"] = pca_result.get("analysis_text", "")
                print("✅ PCA Agent completed successfully")
            else:
                print("⚠️ PCA Agent completed with issues")
        except Exception as e:
            print(f"❌ PCA Agent failed: {e}")
        
        # TreeMix Agent
        try:
            print("Running TreeMix Agent...")
            treemix_result = run_treemix_agent(
                goal=goal,
                output_id=output_id,
                api_key=os.environ.get('OPENAI_API_KEY', ''),
                base_url=self.base_url,
                model="gpt-4-vision-preview"
            )
            if treemix_result.get("success", False):
                analysis_results["treemix"] = treemix_result.get("analysis_text", "")
                print("✅ TreeMix Agent completed successfully")
            else:
                print("⚠️ TreeMix Agent completed with issues")
        except Exception as e:
            print(f"❌ TreeMix Agent failed: {e}")
        
        # Admixture Agent
        try:
            print("Running Admixture Agent...")
            admixture_result = run_admixture_agent(
                goal=goal,
                output_id=output_id,
                api_key=os.environ.get('OPENAI_API_KEY', ''),
                base_url=self.base_url,
                model="gpt-4-vision-preview"
            )
            if admixture_result.get("success", False):
                analysis_results["admixture"] = admixture_result.get("analysis_text", "")
                print("✅ Admixture Agent completed successfully")
            else:
                print("⚠️ Admixture Agent completed with issues")
        except Exception as e:
            print(f"❌ Admixture Agent failed: {e}")
        
        # Other Analysis Agent
        try:
            print("Running Other Analysis Agent...")
            other_result = run_other_analysis_agent(
                goal=goal,
                output_id=output_id,
                api_key=os.environ.get('OPENAI_API_KEY', ''),
                base_url=self.base_url,
                model="gpt-4-vision-preview"
            )
            if other_result.get("success", False):
                analysis_results["other_analysis"] = other_result.get("analysis_text", "")
                print("✅ Other Analysis Agent completed successfully")
            else:
                print("⚠️ Other Analysis Agent completed with issues")
        except Exception as e:
            print(f"❌ Other Analysis Agent failed: {e}")
        
        # Run modeling agent with available analysis results
        try:
            print("Running Modeling Agent...")
            modeling_result = run_modeling_agent(
                goal=goal,
                output_id=output_id,
                ana_dir=ana_dir,
                api_key=os.environ.get('OPENAI_API_KEY', ''),
                base_url=self.base_url,
                model=self.model_name
            )
            if modeling_result.get("success", False):
                print("✅ Modeling Agent completed successfully")
            else:
                print("⚠️ Modeling Agent completed with issues")
        except Exception as e:
            print(f"❌ Modeling Agent failed: {e}")
        
        # Generate final modeling using the OBS files
        try:
            print("Generating final demographic modeling...")
            self._generate_final_modeling_with_obs(goal, copied_obs_files, output_id, analysis_results)
        except Exception as e:
            print(f"❌ Final modeling failed: {e}")
        
        # Generate comprehensive report
        report = self._generate_enhanced_report(goal, output_id, analysis_results, copied_obs_files)
        return report
    
    def _generate_final_modeling_with_obs(self, goal, obs_files, output_id, analysis_results):
        """Generate final demographic modeling using provided OBS files - enhanced version"""
        ana_dir = f"./output/{output_id}/ana"
        
        # Find the main OBS file (prefer _MSFS.obs files)
        main_obs_file = None
        for obs_file in obs_files:
            if '_MSFS.obs' in os.path.basename(obs_file):
                main_obs_file = obs_file
                break
        
        if not main_obs_file:
            main_obs_file = obs_files[0]  # Use first available OBS file
        
        print(f"Using main OBS file for modeling: {main_obs_file}")
        
        # Extract file prefix from OBS filename
        obs_basename = os.path.basename(main_obs_file)
        if '_MSFS.obs' in obs_basename:
            file_prefix = obs_basename.replace('_MSFS.obs', '')
            sfs_type = 'MAF'
        elif '_DSFS.obs' in obs_basename:
            file_prefix = obs_basename.replace('_DSFS.obs', '')
            sfs_type = 'DAF'
        elif '_jointMAFpop1_0.obs' in obs_basename:
            file_prefix = obs_basename.replace('_jointMAFpop1_0.obs', '')
            sfs_type = 'MAF'
        elif '_jointDAFpop1_0.obs' in obs_basename:
            file_prefix = obs_basename.replace('_jointDAFpop1_0.obs', '')
            sfs_type = 'DAF'
        else:
            file_prefix = obs_basename.replace('.obs', '')
            sfs_type = 'MAF'  # Default to MAF
        
        print(f"File prefix: {file_prefix}, SFS type: {sfs_type}")
        
        # Use integrated workflow for final modeling
        try:
            from .modelingagent import IntegratedPopGenWorkflow
            
            # Create the integrated workflow
            workflow = IntegratedPopGenWorkflow(
                api_key=os.environ.get('OPENAI_API_KEY', ''),
                base_url=self.base_url,
                model=self.model_name
            )
            
            # Call the final modeling method from integrated workflow
            modeling_result = workflow._perform_final_modeling({
                "goal": goal,
                "output_id": output_id,
                "ana_dir": ana_dir,
                "analysis_reports": analysis_results,
                "status": "modeling"
            })
            
            if modeling_result and modeling_result.get("success", False):
                print("✅ Final demographic modeling completed successfully")
            else:
                print(f"⚠️ Final modeling completed with issues: {modeling_result}")
                # Fallback to legacy method
                print("Falling back to legacy modeling method...")
                self._legacy_final_modeling_with_obs(goal, obs_files, output_id, file_prefix, sfs_type)
            
        except Exception as e:
            print(f"❌ Error in final modeling: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to legacy method
            print("Falling back to legacy modeling method...")
            try:
                self._legacy_final_modeling_with_obs(goal, obs_files, output_id, file_prefix, sfs_type)
            except Exception as e2:
                print(f"❌ Legacy modeling also failed: {e2}")
    
    
    def _generate_enhanced_report(self, goal, output_id, analysis_results, obs_files):
        """Generate comprehensive analysis report"""
        report_lines = []
        report_lines.append("# Enhanced Population Genetics Analysis Report")
        report_lines.append(f"**Goal:** {goal}")
        report_lines.append(f"**Output ID:** {output_id}")
        report_lines.append(f"**Input Files:** {', '.join([os.path.basename(f) for f in obs_files])}")
        report_lines.append("")
        
        # Analysis results
        if analysis_results:
            report_lines.append("## Analysis Results")
            report_lines.append("")
            
            for analysis_type, result_text in analysis_results.items():
                if result_text:
                    report_lines.append(f"### {analysis_type.replace('_', ' ').title()} Analysis")
                    report_lines.append(result_text)
                    report_lines.append("")
        
        # Modeling recommendations
        modeling_report_path = f"./output/{output_id}/ana/modeling_report.txt"
        if os.path.exists(modeling_report_path):
            report_lines.append("## FastSimCoal Modeling Recommendations")
            report_lines.append("")
            try:
                with open(modeling_report_path, 'r', encoding='utf-8') as f:
                    modeling_content = f.read()
                report_lines.append(modeling_content)
            except Exception as e:
                report_lines.append(f"Error reading modeling report: {e}")
            report_lines.append("")
        
        # Single population analysis (if available)
        single_pop_report_path = f"./output/{output_id}/ana/single_pop_report.txt"
        if os.path.exists(single_pop_report_path):
            report_lines.append("## Single Population Analysis")
            report_lines.append("")
            try:
                with open(single_pop_report_path, 'r', encoding='utf-8') as f:
                    single_pop_content = f.read()
                report_lines.append(single_pop_content)
            except Exception as e:
                report_lines.append(f"Error reading single population report: {e}")
            report_lines.append("")
        
        return "\n".join(report_lines)
    

    
    def save_analysis_history(self, id, asking, response):
        import fcntl  # File lock
        
        # Format id as 3-digit with leading zeros
        formatted_id = str(id).zfill(3)  # Or use formatted_id = f"{int(id):03}"
        
        history_dir = os.path.join('./history', formatted_id)
        os.makedirs(history_dir, exist_ok=True)

        analysis_file_path = os.path.join(history_dir, 'analysis.json')

        # Use file lock for thread safety
        try:
            # If file exists, load existing records; otherwise create empty list
            analysis_history = []
            if os.path.exists(analysis_file_path):
                with open(analysis_file_path, 'r', encoding='utf-8') as file:
                    try:
                        fcntl.flock(file.fileno(), fcntl.LOCK_SH)  # Shared lock for read
                        analysis_history = json.load(file)
                    finally:
                        fcntl.flock(file.fileno(), fcntl.LOCK_UN)  # Release lock

            # Check for incomplete placeholder record
            placeholder_updated = False
            for entry in reversed(analysis_history):
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
                    "session_id": formatted_id,
                    "status": "completed"
                }
                analysis_history.append(new_entry)

            # Save records back to file
            with open(analysis_file_path, 'w', encoding='utf-8') as file:
                try:
                    fcntl.flock(file.fileno(), fcntl.LOCK_EX)  # Exclusive lock for write
                    json.dump(analysis_history, file, ensure_ascii=False, indent=4)
                finally:
                    fcntl.flock(file.fileno(), fcntl.LOCK_UN)  # Release lock
                    
            logging.info(f"Successfully saved analysis history for session {formatted_id}")
            
        except Exception as e:
            logging.error(f"Error saving analysis history for session {formatted_id}: {str(e)}")
            # Do not raise exception to avoid affecting main flow