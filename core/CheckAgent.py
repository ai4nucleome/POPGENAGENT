import os
import json
import logging
import re
from typing import Dict, List, Tuple, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

class CheckAgent:
    """
    CheckAgent core functionality:
    - Verify expected output files exist and are non-empty (not 0 bytes)
    - When files don't exist, scan directory and let LLM determine possible output files
    - Update status in DEBUG_Output file
    """
    
    def __init__(self, api_key: str, base_url: str, model: str = "claude-opus-4-1-20250805-thinking", **kwargs):
        # Configure logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        self.model = ChatOpenAI(model=model, base_url=base_url)
        
        # Create prompt template - fixed JSON format escaping
        self.file_prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are a bioinformatics file analyzer. Based on the step information and file list, 
            determine which files are likely outputs. Return JSON with:
            {{
                "analysis": "Detailed analysis of why files are valid or invalid",
                "output_filename": ["file1: description", "file2: description", ...],
                "stats": true/false (whether the files are valid outputs)
            }}
            """),
            ("human", """
            Step details:
            - Step number: {step_number}
            - Tool: {tool_name}
            - Description: {step_description}
            
            Available files: {file_list}
            
            Expected output files: {expected_files}
            """)
        ])
    
    def check_file_size(self, file_path: str) -> Tuple[bool, str]:
        """Check if file exists and is non-empty (not 0 bytes)"""
        if not os.path.exists(file_path):
            return False, f"File doesn't exist: {file_path}"
        
        if os.path.getsize(file_path) == 0:
            return False, f"File is empty (0 bytes): {file_path}"
            
        return True, f"File exists and has content"
    
    def scan_directory(self, directory: str) -> List[Dict[str, Any]]:
        """Scan all non-empty files in directory"""
        if not os.path.exists(directory):
            return []
        
        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                path = os.path.join(root, filename)
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    files.append({
                        "path": path,
                        "size": os.path.getsize(path)
                    })
        return files
    
    def get_step_details(self, task_id: str, step_number: str) -> Dict[str, Any]:
        """Get step details from PLAN.json"""
        plan_path = f"./output/{task_id}_PLAN.json"
        if not os.path.exists(plan_path):
            return {}
        
        plan_file = open(plan_path, 'r', encoding='utf-8')
        plan_data = plan_file.read()
        plan_file.close()
        
        if not plan_data:
            return {}
            
        plan = json.loads(plan_data)
        
        for step in plan.get("plan", []):
            if str(step.get("step_number", "")) == step_number:
                return step
        
        return {}
    
    def is_valid_json(self, json_str: str) -> bool:
        """Check if string is valid JSON"""
        if not json_str:
            return False
            
        # Simple check: starts with { and ends with }
        json_str = json_str.strip()
        if not (json_str.startswith('{') and json_str.endswith('}')):
            return False
            
        # More checks can be added here
        return True
    
    def safe_parse_json(self, json_str: str) -> Dict[str, Any]:
        """Safely parse JSON string, avoid using try-except"""
        if not self.is_valid_json(json_str):
            self.logger.error(f"Invalid JSON format: {json_str[:100]}...")
            return {
                "analysis": f"Failed to parse response: invalid JSON format",
                "output_filename": [],
                "stats": False
            }
            
        return json.loads(json_str)
    
    def check_output_files(self, debug_output_path: str) -> Dict[str, Any]:
        """
        Main check function: verify files exist and are non-empty; if not, scan directory for analysis
        """
        # Check and load DEBUG_Output file
        if not os.path.exists(debug_output_path):
            self.logger.error(f"DEBUG_Output file not found: {debug_output_path}")
            return {"overall_check": False}
            
        debug_file = open(debug_output_path, 'r', encoding='utf-8')
        debug_content = debug_file.read()
        debug_file.close()
        
        if not debug_content:
            self.logger.error(f"DEBUG_Output file is empty")
            return {"overall_check": False}
            
        debug_output = json.loads(debug_content)
        
        # If stats is already False, return directly
        if not debug_output.get("stats", False):
            return {"overall_check": False}
        
        # Extract task ID and step number from path
        path_match = re.search(r'(\d+)_DEBUG_Output_(\d+)\.json', debug_output_path)
        if not path_match:
            return {"overall_check": False}
        
        task_id = path_match.group(1)
        step_number = path_match.group(2)
        output_dir = f"./output/{task_id}"
        
        # Get expected output file list
        output_files = debug_output.get("output_filename", [])
        expected_files = []
        for file_entry in output_files:
            if ':' in file_entry:
                path = file_entry.split(':', 1)[0].strip()
            else:
                path = file_entry.strip()
            expected_files.append(path)
        
        # Check all expected files
        all_valid = True
        
        # If expected files exist, check they exist and are non-empty
        if expected_files:
            for file_path in expected_files:
                valid, _ = self.check_file_size(file_path)
                if not valid:
                    all_valid = False
                    break
            
            # If all files valid, return success directly
            if all_valid:
                return {
                    "overall_check": True,
                    "stats": True
                }
        
        # Scan all non-empty files in directory
        all_files = self.scan_directory(output_dir)
        if not all_files:
            # No files found, mark as failed directly
            debug_output["stats"] = False
            debug_output["analyze"] = debug_output.get("analyze", "") + f"\n\nNo valid files found in {output_dir}"
            
            out_file = open(debug_output_path, 'w', encoding='utf-8')
            out_file.write(json.dumps(debug_output, indent=4))
            out_file.close()
            
            return {"overall_check": False, "stats": False}
        
        # Get step details and format file list
        step_details = self.get_step_details(task_id, step_number)
        file_list_text = "\n".join([f"- {f['path']} ({f['size']} bytes)" for f in all_files])
        
        # Call LLM for analysis
        response = self.file_prompt.invoke({
            "step_number": step_details.get("step_number", "unknown"),
            "tool_name": step_details.get("tools", "unknown"),
            "step_description": step_details.get("description", "unknown"),
            "file_list": file_list_text,
            "expected_files": ", ".join(expected_files) if expected_files else "None specified"
        })
        
        result = self.model.invoke(response)
        
        # Parse model response, avoid using try-except
        model_response = self.safe_parse_json(result.content)
        analysis = model_response.get("analysis", "")
        new_output_files = model_response.get("output_filename", [])
        stats = model_response.get("stats", False)
        print("--------------------------------")
        print(model_response)
        print("--------------------------------")
        # Update DEBUG_Output file
        debug_output["stats"] = stats
        debug_output["analyze"] = debug_output.get("analyze", "") + f"\n\n{analysis}"
        if new_output_files:
            debug_output["output_filename"] = new_output_files
        
        out_file = open(debug_output_path, 'w', encoding='utf-8')
        out_file.write(json.dumps(debug_output, indent=4))
        out_file.close()
        
        return {
            "overall_check": stats,
            "analysis": analysis,
            "output_filename": new_output_files,
            "stats": stats
        }
