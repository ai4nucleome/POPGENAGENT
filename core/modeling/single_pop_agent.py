#!/usr/bin/env python3
"""
SinglePopAgent - Single Population Demographic Analysis Agent

Based on obs_agent.py framework, specialized for single population SFS analysis and FastSimCoal2 modeling
Auto-discovers _MAFpop0.obs files, generates independent FastSimCoal2 configs and scripts per population
Includes full LangGraph error handling and retry mechanism
"""

import os
import json
import glob
import subprocess
import shutil
from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, END

# LLM
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import Chroma

# =========================
#         State definition
# =========================
class SinglePopAgentState(TypedDict, total=False):
    goal: str
    data_dir: str
    populations: List[str]
    obs_files: Dict[str, str]  # Population name -> obs file path
    id: str
    max_retries: int
    
    # LLM related
    api_key: str
    base_url: str
    model: str
    
    # Run intermediate results
    ok: bool
    analysis: str
    outputs: Dict[str, str]

# =========================
#       Utility functions
# =========================
MAX_STD_CHARS = 8000

def write_text(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def write_json(path: str, obj: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def file_nonempty(p: str) -> bool:
    return os.path.exists(p) and os.path.getsize(p) > 0

def dir_nonempty(p: str) -> bool:
    if not os.path.isdir(p):
        return False
    for _, _, files in os.walk(p):
        if files:
            return True
    return False

# JSON formatter
def Json_Format_Agent(text: str) -> str:
    if not text or not text.strip():
        return '{"shell": [], "analyze": "empty response", "output_filename": [], "stats": false}'
    try:
        json.loads(text)
        return text
    except Exception:
        pass
    import re, ast
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        s = m.group(0)
        try:
            json.loads(s); return s
        except Exception:
            try:
                d = ast.literal_eval(s)
                return json.dumps(d)
            except Exception:
                pass
    return '{"shell": [], "analyze": "failed to parse json", "output_filename": [], "stats": false}'

# =========================
#       PROMPT definition
# =========================
TASK_PROMPT = """You are a senior bioinformatics engineer and FastSimCoal2 expert specialized in single population demographic analysis.
Return VALID JSON ONLY with keys: "shell", "analyze", "output_filename", "stats".
- "shell": array of shell strings, each string is one full command line.
- "analyze": short paragraph using only periods and commas, no quotes.
- "output_filename": array of expected output paths.
- "stats": boolean.

CRITICAL: You MUST prioritize and use the provided data-driven parameter settings:

1. **Data-Driven Parameters Priority**: The input will include a "data_driven_params" section containing parameter ranges automatically calculated from the SFS data analysis. This is your PRIMARY source for parameter values.

2. **Parameter Usage Guidelines**:
   - ALWAYS use the npop_range, texp_range, and resize_range from data_driven_params
   - The sample_size should match the analyzed SFS dimensions
   - These parameters are scientifically derived from the actual genetic diversity in the data
   - Do NOT use arbitrary or default parameter values when data-driven parameters are available

3. **Reference Configurations (Secondary)**: The input may also include a "reference_configs" section containing proven successful FastSimCoal2 configuration files.
   - Use these for file structure and syntax patterns
   - Adapt the file formats but replace parameter ranges with data-driven values
   - Maintain proven file structures while using scientifically-informed parameter ranges

4. **Data-Informed Adaptation**:
   - Use the demographic_inference from data_driven_params to guide model complexity
   - If inference suggests "rapid expansion", prioritize recent time ranges and larger size changes
   - If inference suggests "stable population", use moderate parameter ranges
   - The estimated_ne provides guidance for realistic effective population size ranges

5. **Single Population Specific Requirements**:
   - Generate .tpl (template) file with single deme configuration
   - Generate .est (estimation) file with proper PARAMETERS section format
   - Use FREQ data type for SFS computation with observed data
   - Include population size changes and demographic events as appropriate
   - Follow FastSimCoal2 .est file format: [PARAMETERS] section with proper column structure

You must complete single population demographic analysis using FastSimCoal2:
1) Generate .tpl (template) file for single population demographic model
2) Generate .est (estimation) file for parameter estimation  
3) Generate .par (parameter) file with specific parameter values
4) Create shell script to run FastSimCoal2 analysis
5) Execute FastSimCoal2 with appropriate parameters for single population analysis

SINGLE POPULATION MODEL REQUIREMENTS:
- Use single deme with potential size changes over time
- Include population expansion/contraction events if relevant
- Set appropriate mutation rate and generation time
- Use folded SFS (-m parameter for MAF data)
- Generate both simulation and parameter estimation runs

CRITICAL FASTSIMCOAL2 FORMAT REQUIREMENTS:

**Template File (.tpl) Structure**:
- Single deme configuration (1 population)
- Population effective size parameters (use parameter names from knowledge base)
- Historical events section for demographic changes
- FREQ data type for SFS computation: "FREQ 1 0 2.5e-8 OUTEXP"

**Estimation File (.est) Structure** (CRITICAL - Follow exact format):
```
[PARAMETERS]
//#isInt? #name   #dist.#min  #max     #output
1  NPOP     logunif    1000    50000    output
1  TEXP     logunif    100     10000    output
0  RESIZE   logunif    0.1     10.0     output

[RULES]

[COMPLEX PARAMETERS]
```

**File Naming Convention**:
- For population POP: POP_single.tpl, POP_single.est, POP_single.par
- Configuration files go to ./output/{{id}}/ana/single_pop/POP/
- Copy obs files: cp ./output/{{id}}/ana/data/POP_MAFpop0.obs ./POP_single_MAFpop0.obs

**FastSimCoal2 Execution Pattern**:
- Copy obs file to project root for execution
- Run: ./fsc28 -t ./output/{{id}}/ana/single_pop/POP/POP_single.tpl -e ./output/{{id}}/ana/single_pop/POP/POP_single.est
- Use -m for folded SFS (MAF data), -M for maximum likelihood estimation
- CRITICAL: Always use ./fsc28 as the executable command

**Post-execution File Management**:
- Create results directory: mkdir -p ./output/{{id}}/ana/single_pop/POP/results
- Move FastSimCoal2 output files to results directory
- Clean up temporary obs files from project root
- Ensure .bestlhoods file is moved to ./output/{{id}}/ana/single_pop/POP/results/

ACCEPTANCE CRITERIA for stats=true:
- All .tpl, .est, .par files created and non-empty
- FastSimCoal2 execution completed successfully
- Output files (.bestlhoods, .log) exist and contain results

Return JSON only.
"""

DEBUG_PROMPT = """You are a senior bioinformatics engineer and FastSimCoal2 debugging expert.
Given the previous execution result, return VALID JSON ONLY with: "shell", "analyze", "output_filename", "stats".
- "shell": array of corrected shell commands to fix the failure.
- "analyze": brief paragraph with only periods and commas.
- "output_filename": expected output paths after fix.
- "stats": false unless you are certain all acceptance criteria are met.

COMMON FASTSIMCOAL2 FIXES:
- Fix file permission issues with chmod
- Correct parameter file formats and syntax
- Adjust memory and CPU parameters for the system
- Fix file path issues and working directory problems
- Correct SFS type parameters (-m vs -d)
- Handle missing input files by checking paths
- Do NOT attempt to install FastSimCoal2, assume it is available

PATH AND EXECUTION FIXES:
- Assume FastSimCoal2 executable (fsc28) is available in system PATH
- Check input file existence and format before execution
- Create necessary output directories
- Fix file naming and path issues
- Handle parameter value ranges and constraints
- CRITICAL: Always use ./fsc28 as the executable command, not fsc28 or full paths
- Do NOT attempt to download or install FastSimCoal2
- CRITICAL: Follow successful script pattern: copy obs file to project root, run with full config paths
- Copy obs files: cp ./output/{{id}}/ana/data/POP_MAFpop0.obs ./POP_single_MAFpop0.obs
- Execute: ./fsc28 -t ./output/{{id}}/ana/single_pop/POP/POP_single.tpl -e ./output/{{id}}/ana/single_pop/POP/POP_single.est

Return JSON only.
"""

# Example configuration
TASK_EXAMPLES = [
    {
        "input": {
            "task": {"phase": "single_pop_analysis", "population": "YRI", "obs_file": "./data/YRI_MAFpop0.obs", "output_dir": "./output/061/ana/single_pop/YRI", "mutation_rate": 2.5e-8, "generation_time": 25}, 
            "id": "061",
            "data_driven_params": {
                "sample_size": 71,
                "npop_range": "8000 80000",
                "texp_range": "100 10000",
                "resize_range": "1.5 20.0",
                "demographic_inference": "Moderate population expansion",
                "estimated_ne": 24000,
                "parameter_rationale": "Based on pi=0.000600, Tajima_D≈-0.85, rare_alleles=0.280"
            }
        },
        "output": {"shell": [
            "mkdir -p ./output/061/ana/single_pop/YRI",
            "cat > ./output/061/ana/single_pop/YRI/YRI_single.tpl << 'EOF'\n//Number of population samples (demes)\n1\n//Population effective sizes (number of genes)\nNPOP\n//Sample sizes\n71\n//Growth rates: negative growth implies population expansion\n0\n//Number of migration matrices : 0 implies no migration between demes\n0\n//historical event: time, source, sink, migrants, new size, new growth rate, migr matrix\n1 historical event\nTEXP 0 0 0 RESIZE 0 0\n//Number of independent loci [chromosome]\n1 0\n//Per chromosome: Number of contiguous linkage Block: a block is a set of contiguous loci\n1\n//per Block:data type, number of loci, per generation recombination and mutation rates and optional parameters\nFREQ 1 0 2.5e-8 OUTEXP\nEOF",
            "cat > ./output/061/ana/single_pop/YRI/YRI_single.est << 'EOF'\n[PARAMETERS]\n//#isInt? #name   #dist.#min  #max     #output\n1  NPOP     logunif    8000    80000    output\n1  TEXP     logunif    100     10000    output\n0  RESIZE   logunif    1.5     20.0     output\n\n[RULES]\n\n[COMPLEX PARAMETERS]\nEOF",
            "cp ./output/061/ana/data/YRI_MAFpop0.obs ./YRI_single_MAFpop0.obs",
            "./fsc28 -t ./output/061/ana/single_pop/YRI/YRI_single.tpl -e ./output/061/ana/single_pop/YRI/YRI_single.est -m -M -n 50000 -L 20 -c 8 -q --seed 12345",
            "mkdir -p ./output/061/ana/single_pop/YRI/results",
            "if [ -d \"YRI_single\" ]; then mv YRI_single/* ./output/061/ana/single_pop/YRI/results/ 2>/dev/null || true; rmdir YRI_single 2>/dev/null || true; fi",
            "if [ -f \"YRI_single.bestlhoods\" ]; then mv YRI_single.bestlhoods ./output/061/ana/single_pop/YRI/results/; fi",
            "if [ -f \"YRI_single_MAFpop0.obs\" ]; then rm YRI_single_MAFpop0.obs; fi"
        ], "analyze": "Generate FastSimCoal2 configuration files using data-driven parameters from SFS analysis with Ne range 8000-80000 based on nucleotide diversity, expansion time 100-10000 generations from Tajima's D analysis, and size change factor 1.5-20.0 indicating moderate population expansion for YRI population.", "output_filename": ["./output/061/ana/single_pop/YRI/YRI_single.tpl", "./output/061/ana/single_pop/YRI/YRI_single.est", "./output/061/ana/single_pop/YRI/YRI_single.par"], "stats": False}
    }
]

DEBUG_EXAMPLES = [
    {
        "input": {"task": {"phase": "single_pop_analysis", "population": "YRI"}, "result": "RC=127\\nSTDOUT:\\n\\nSTDERR:\\nfsc28: command not found", "shell": ["fsc28 -t YRI_single.tpl -e YRI_single.est -m -M -n 50000 -L 20"]},
        "output": {"shell": [
            "cat > ./output/061/ana/single_pop/YRI/YRI_single.est << 'EOF'\n[PARAMETERS]\n//#isInt? #name   #dist.#min  #max     #output\n1  NPOP     logunif    1000    50000    output\n1  TEXP     logunif    100     10000    output\n0  RESIZE   logunif    0.1     10.0     output\n\n[RULES]\n\n[COMPLEX PARAMETERS]\nEOF",
            "cp ./output/061/ana/data/YRI_MAFpop0.obs ./YRI_single_MAFpop0.obs",
            "which fsc28 > /dev/null && cp $(which fsc28) ./fsc28 || echo 'FastSimCoal2 not found in PATH'",
            "./fsc28 -t ./output/061/ana/single_pop/YRI/YRI_single.tpl -e ./output/061/ana/single_pop/YRI/YRI_single.est -m -M -n 50000 -L 20 -c 8 -q --seed 12345",
            "mkdir -p ./output/061/ana/single_pop/YRI/results",
            "if [ -d \"YRI_single\" ]; then mv YRI_single/* ./output/061/ana/single_pop/YRI/results/ 2>/dev/null || true; rmdir YRI_single 2>/dev/null || true; fi",
            "if [ -f \"YRI_single.bestlhoods\" ]; then mv YRI_single.bestlhoods ./output/061/ana/single_pop/YRI/results/; fi",
            "if [ -f \"YRI_single_MAFpop0.obs\" ]; then rm YRI_single_MAFpop0.obs; fi"
        ], "analyze": "Fix estimation file format with proper PARAMETERS section then copy obs file and run FastSimCoal2 with correct configuration file format", "output_filename": ["./output/061/ana/single_pop/YRI/YRI_single.tpl", "./output/061/ana/single_pop/YRI/YRI_single.est"], "stats": False}
    }
]

# =========================
#       LLM construction
# =========================
def create_llm_agent(api_key: str, base_url: str, model: str, prompt_template: str, examples: List[Dict]):
    print(f"[DEBUG] Creating LLM agent for SinglePopAgent with model: {model}")
    llm = ChatOpenAI(
        model=model,
        base_url=base_url,
        openai_api_key=api_key,
        temperature=0.1,
        max_tokens=4000
    )
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
    agent = final_prompt | llm | parser
    print(f"[DEBUG] SinglePopAgent LLM agent created successfully")
    return agent

def load_fastsimcoal_knowledge_base(api_key: str, base_url: str):
    """Load FastSimCoal2 knowledge base, reference AnaAgent implementation"""
    print("[DEBUG] Loading FastSimCoal2 knowledge base for SinglePopAgent...")
    
    # Initialize embeddings
    embeddings = OpenAIEmbeddings(
        model="qwen3-embedding-8b",
        base_url=base_url,
        openai_api_key=api_key
    )
    
    # Initialize vector store
    fastsimcoal_vectorstore = Chroma(
        collection_name="fastsimcoal_collection",
        embedding_function=embeddings,
        persist_directory="./chroma_db/fastsimcoal"
    )
    
    # Check knowledge base directory
    fastsimcoal_doc_dir = "./knowledge/fastsimcoal"
    if not os.path.exists(fastsimcoal_doc_dir):
        print(f"[WARNING] FastSimCoal2 knowledge base directory not found: {fastsimcoal_doc_dir}")
        return fastsimcoal_vectorstore
    
    print(f"[DEBUG] FastSimCoal2 knowledge base loaded from: {fastsimcoal_doc_dir}")
    return fastsimcoal_vectorstore

def search_fastsimcoal_knowledge(vectorstore, query: str, k: int = 3) -> str:
    """Search FastSimCoal2 knowledge base, reference AnaAgent implementation"""
    try:
        related_docs = vectorstore.max_marginal_relevance_search(query, k=k, fetch_k=20)
        if related_docs:
            reference_content = ""
            for i, doc in enumerate(related_docs):
                reference_content += f"\n--- Reference Example {i+1} ---\n"
                reference_content += f"Source: {doc.metadata.get('source', 'Unknown')}\n"
                reference_content += doc.page_content
                reference_content += "\n"
            return reference_content
        else:
            return "\n--- No reference examples found in knowledge base ---\n"
    except Exception as e:
        print(f"[WARNING] Error searching knowledge base: {e}")
        return "\n--- Error accessing knowledge base ---\n"

# =========================
#        Execution and verification
# =========================
def execute_shell_array(shell_cmds: List[str], script_path: str, timeout: int = 1800) -> Dict[str, str]:
    content = "#!/bin/bash\nset -euo pipefail\n" + "\n".join(shell_cmds) + "\n"
    write_text(script_path, content)
    os.chmod(script_path, 0o755)
    print(f"[EXEC] Running {script_path}")
    try:
        p = subprocess.run(["bash", script_path], capture_output=True, text=True, timeout=timeout)
        return {
            "rc": str(p.returncode),
            "stdout": (p.stdout or "")[:MAX_STD_CHARS],
            "stderr": (p.stderr or "")[:MAX_STD_CHARS],
            "script": script_path,
            "shell": shell_cmds
        }
    except subprocess.TimeoutExpired:
        return {"rc": "124", "stdout": "", "stderr": "TimeoutExpired", "script": script_path, "shell": shell_cmds}
    except Exception as e:
        error_msg = f"Unexpected error during script execution: {type(e).__name__}: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return {"rc": "1", "stdout": "", "stderr": error_msg, "script": script_path, "shell": shell_cmds}

def verify_single_pop_analysis(output_dir: str, population: str) -> bool:
    """Verify whether single population analysis is complete"""
    required_files = [
        os.path.join(output_dir, f"{population}_single.tpl"),
        os.path.join(output_dir, f"{population}_single.est")
    ]
    
    # Check basic config files
    basic_check = all(file_nonempty(f) for f in required_files)
    
    # Check FastSimCoal2 output files - prefer moved location, then original
    result_locations = [
        os.path.join(output_dir, "results", f"{population}_single.bestlhoods"),  # Moved location
        f"{population}_single/{population}_single.bestlhoods",  # Original subdirectory
        f"{population}_single.bestlhoods"  # Original root directory
    ]
    
    result_check = any(file_nonempty(f) for f in result_locations)
    
    print(f"[VERIFY] Basic files check: {basic_check}")
    print(f"[VERIFY] Result files check: {result_check}")
    print(f"[VERIFY] Checking result files: {result_locations}")
    for f in result_locations:
        if os.path.exists(f):
            print(f"[VERIFY] Found result file: {f}")
    
    return basic_check and result_check

def parse_bestlhoods_file(file_path: str) -> Dict[str, float]:
    """Parse .bestlhoods file to extract parameter estimates"""
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        if len(lines) < 2:
            return {}
            
        # Parse header and values
        headers = lines[0].strip().split('\t')
        values = lines[1].strip().split('\t')
        
        if len(headers) != len(values):
            return {}
            
        # Build parameter dictionary
        params = {}
        for header, value in zip(headers, values):
            try:
                if '.' in value or 'e' in value.lower():
                    params[header] = float(value)
                else:
                    params[header] = int(value)
            except ValueError:
                params[header] = value
                
        return params
    except Exception as e:
        print(f"[ERROR] Failed to parse bestlhoods file {file_path}: {e}")
        return {}

def generate_single_pop_report(output_id: str, ana_dir: str, single_pop_dir: str, results: Dict[str, Any]) -> str:
    """Generate single population analysis report"""
    from datetime import datetime
    
    report_lines = []
    report_lines.append(f"Single Population Demographic Analysis Report")
    report_lines.append(f"Project ID: {output_id}")
    report_lines.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    successful_populations = []
    failed_populations = []
    
    for population, result in results.items():
        if result["ok"]:
            successful_populations.append(population)
        else:
            failed_populations.append(population)
    
    report_lines.append(f"SUMMARY:")
    report_lines.append(f"- Total populations analyzed: {len(results)}")
    report_lines.append(f"- Successful analyses: {len(successful_populations)}")
    report_lines.append(f"- Failed analyses: {len(failed_populations)}")
    report_lines.append("")
    
    if successful_populations:
        report_lines.append("DEMOGRAPHIC PARAMETER ESTIMATES:")
        report_lines.append("")
        
        for population in successful_populations:
            report_lines.append(f"Population: {population}")
            report_lines.append("-" * 40)
            
            # Find .bestlhoods file
            pop_dir = os.path.join(single_pop_dir, population)
            bestlhoods_locations = [
                os.path.join(pop_dir, "results", f"{population}_single.bestlhoods"),
                f"{population}_single/{population}_single.bestlhoods",
                f"{population}_single.bestlhoods"
            ]
            
            bestlhoods_file = None
            for location in bestlhoods_locations:
                if file_nonempty(location):
                    bestlhoods_file = location
                    break
            
            if bestlhoods_file:
                params = parse_bestlhoods_file(bestlhoods_file)
                if params:
                    report_lines.append("Parameter Estimates:")
                    for param, value in params.items():
                        if param == "MaxEstLhood":
                            report_lines.append(f"  Maximum Likelihood: {value:.2f}")
                        elif param == "NPOP":
                            report_lines.append(f"  Effective Population Size (Ne): {value:,}")
                        elif param == "TEXP":
                            report_lines.append(f"  Expansion Time (generations): {value:,}")
                        elif param == "RESIZE":
                            report_lines.append(f"  Population Size Change Factor: {value:.4f}")
                        else:
                            report_lines.append(f"  {param}: {value}")
                    
                    # Biological interpretation
                    report_lines.append("")
                    report_lines.append("Biological Interpretation:")
                    
                    # Analyze effective population size
                    if "NPOP" in params:
                        ne = params["NPOP"]
                        if ne < 5000:
                            ne_interpretation = "relatively small effective population size, indicating potential bottleneck effects"
                        elif ne < 20000:
                            ne_interpretation = "moderate effective population size, typical for many human populations"
                        else:
                            ne_interpretation = "large effective population size, indicating good genetic diversity"
                        report_lines.append(f"  - Current effective population size of {ne:,} suggests {ne_interpretation}")
                    
                    # Analyze expansion time
                    if "TEXP" in params:
                        texp = params["TEXP"]
                        years_ago = texp * 25  # Assume 25 years per generation
                        if years_ago < 5000:
                            time_interpretation = "recent demographic changes (within historical times)"
                        elif years_ago < 50000:
                            time_interpretation = "demographic changes during the Late Pleistocene"
                        else:
                            time_interpretation = "ancient demographic changes"
                        report_lines.append(f"  - Expansion occurred ~{texp:,} generations (~{years_ago:,} years) ago, indicating {time_interpretation}")
                    
                    # Analyze population size change
                    if "RESIZE" in params:
                        resize = params["RESIZE"]
                        if resize > 1:
                            change_interpretation = f"population expansion (grew by factor of {resize:.2f})"
                        elif resize < 1:
                            change_interpretation = f"population contraction/bottleneck (reduced to {resize:.2f} of original size)"
                        else:
                            change_interpretation = "stable population size"
                        report_lines.append(f"  - Size change factor of {resize:.4f} indicates {change_interpretation}")
                    
                    # Population-specific interpretation
                    if population == "YRI":
                        report_lines.append(f"  - {population} represents African populations with typically high genetic diversity and large effective population sizes")
                    elif population == "CEU":
                        report_lines.append(f"  - {population} represents European populations that experienced out-of-Africa bottleneck and subsequent expansion")
                    elif population == "CHB":
                        report_lines.append(f"  - {population} represents East Asian populations with similar demographic history to Europeans but distinct expansion patterns")
                    elif population == "CHS":
                        report_lines.append(f"  - {population} represents another East Asian population with potentially similar demographic patterns to CHB")
                else:
                    report_lines.append("  No parameter estimates available")
            else:
                report_lines.append("  Results file not found")
            
            report_lines.append("")
    
    if failed_populations:
        report_lines.append("FAILED ANALYSES:")
        for population in failed_populations:
            report_lines.append(f"- {population}: Analysis failed to complete successfully")
        report_lines.append("")
    
    # Add comparative analysis (if multiple successful populations)
    if len(successful_populations) > 1:
        report_lines.append("COMPARATIVE ANALYSIS:")
        report_lines.append("")
        
        # Collect all parameters for comparison
        all_params = {}
        for population in successful_populations:
            pop_dir = os.path.join(single_pop_dir, population)
            bestlhoods_locations = [
                os.path.join(pop_dir, "results", f"{population}_single.bestlhoods"),
                f"{population}_single/{population}_single.bestlhoods",
                f"{population}_single.bestlhoods"
            ]
            
            for location in bestlhoods_locations:
                if file_nonempty(location):
                    params = parse_bestlhoods_file(location)
                    if params:
                        all_params[population] = params
                    break
        
        # Compare effective population sizes
        if all(p.get("NPOP") for p in all_params.values()):
            report_lines.append("Effective Population Size Comparison:")
            ne_values = {pop: params["NPOP"] for pop, params in all_params.items()}
            sorted_pops = sorted(ne_values.items(), key=lambda x: x[1], reverse=True)
            for pop, ne in sorted_pops:
                report_lines.append(f"  {pop}: {ne:,}")
            
            largest_pop = sorted_pops[0][0]
            smallest_pop = sorted_pops[-1][0]
            ratio = sorted_pops[0][1] / sorted_pops[-1][1]
            report_lines.append(f"  -> {largest_pop} has {ratio:.1f}x larger effective population size than {smallest_pop}")
            report_lines.append("")
        
        # Compare expansion times
        if all(p.get("TEXP") for p in all_params.values()):
            report_lines.append("Expansion Time Comparison:")
            texp_values = {pop: params["TEXP"] for pop, params in all_params.items()}
            sorted_pops = sorted(texp_values.items(), key=lambda x: x[1], reverse=True)
            for pop, texp in sorted_pops:
                years_ago = texp * 25
                report_lines.append(f"  {pop}: {texp:,} generations (~{years_ago:,} years ago)")
            report_lines.append("")
    
    report_lines.append("TECHNICAL DETAILS:")
    report_lines.append(f"- Analysis method: FastSimCoal2 maximum likelihood estimation")
    report_lines.append(f"- Model: Single population with size change event")
    report_lines.append(f"- Data type: Folded site frequency spectrum (MAF)")
    report_lines.append(f"- Mutation rate: 2.5e-8 per site per generation")
    report_lines.append(f"- Generation time: 25 years")
    report_lines.append("")
    
    report_lines.append("FILES GENERATED:")
    for population in successful_populations:
        pop_dir = os.path.join(single_pop_dir, population)
        report_lines.append(f"- {population}:")
        report_lines.append(f"  Configuration: {pop_dir}/{population}_single.tpl, {population}_single.est")
        
        results_dir = os.path.join(pop_dir, "results")
        if os.path.isdir(results_dir):
            report_lines.append(f"  Results: {results_dir}/")
    
        return "\n".join(report_lines)

def analyze_sfs_data(obs_file_path: str) -> Dict[str, Any]:
    """Analyze SFS data file, extract features for parameter setting"""
    try:
        with open(obs_file_path, 'r') as f:
            lines = f.readlines()
        
        if len(lines) < 3:
            print(f"[WARNING] Invalid obs file format: {obs_file_path}")
            return {}
            
        # Parse SFS data (line 3)
        sfs_data = [float(x) for x in lines[2].strip().split() if x]
        
        if not sfs_data:
            print(f"[WARNING] No SFS data found in: {obs_file_path}")
            return {}
        
        # Compute SFS features
        total_sites = sum(sfs_data)
        n_alleles = len(sfs_data)  # Number of allele frequency classes
        
        # Compute diversity metrics
        # Approximate π (nucleotide diversity)
        pi_estimate = 0
        for i, count in enumerate(sfs_data):
            if i > 0 and i < len(sfs_data) - 1:  # Exclude fixed sites
                frequency = i / (n_alleles - 1)
                pi_estimate += count * 2 * frequency * (1 - frequency)
        
        if total_sites > 0:
            pi_estimate = pi_estimate / total_sites
        
        # Watterson's theta estimate
        harmonic_number = sum(1/k for k in range(1, n_alleles))
        theta_w = sum(sfs_data[1:-1]) / harmonic_number if harmonic_number > 0 else 0
        
        # Simplified Tajima's D estimate
        tajima_d_approx = (pi_estimate - theta_w) / max(theta_w, 1e-10)
        
        # Compute SFS distribution shape features
        if len(sfs_data) > 1:
            # Approximate haplotype diversity - based on rare allele ratio
            rare_allele_ratio = sfs_data[1] / max(total_sites, 1)
            
            # Proportion of intermediate frequency alleles
            mid_freq_start = max(1, len(sfs_data) // 4)
            mid_freq_end = min(len(sfs_data) - 1, 3 * len(sfs_data) // 4)
            mid_freq_count = sum(sfs_data[mid_freq_start:mid_freq_end])
            mid_freq_ratio = mid_freq_count / max(total_sites, 1)
        else:
            rare_allele_ratio = 0
            mid_freq_ratio = 0
        
        return {
            "total_sites": total_sites,
            "n_alleles": n_alleles,
            "pi_estimate": pi_estimate,
            "theta_w": theta_w,
            "tajima_d_approx": tajima_d_approx,
            "rare_allele_ratio": rare_allele_ratio,
            "mid_freq_ratio": mid_freq_ratio,
            "sfs_shape": "skewed_rare" if rare_allele_ratio > 0.3 else "balanced" if mid_freq_ratio > 0.2 else "intermediate"
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to analyze SFS data in {obs_file_path}: {e}")
        return {}

def get_data_driven_parameters(obs_file_path: str, population: str) -> Dict[str, Any]:
    """Auto-set parameters based on observed data features"""
    
    # Analyze SFS data
    sfs_analysis = analyze_sfs_data(obs_file_path)
    
    if not sfs_analysis:
        print(f"[WARNING] Using default parameters for {population} due to SFS analysis failure")
        return get_default_parameters()
    
    print(f"[INFO] SFS analysis for {population}:")
    print(f"  - Total sites: {sfs_analysis.get('total_sites', 0):.0f}")
    print(f"  - Pi estimate: {sfs_analysis.get('pi_estimate', 0):.6f}")
    print(f"  - Theta_W: {sfs_analysis.get('theta_w', 0):.6f}")
    print(f"  - Tajima's D approx: {sfs_analysis.get('tajima_d_approx', 0):.3f}")
    print(f"  - Rare allele ratio: {sfs_analysis.get('rare_allele_ratio', 0):.3f}")
    print(f"  - SFS shape: {sfs_analysis.get('sfs_shape', 'unknown')}")
    
    # Set parameters based on data features
    pi_est = sfs_analysis.get('pi_estimate', 0)
    tajima_d = sfs_analysis.get('tajima_d_approx', 0)
    rare_ratio = sfs_analysis.get('rare_allele_ratio', 0)
    n_alleles = sfs_analysis.get('n_alleles', 70)
    
    # Estimate effective population size range (based on nucleotide diversity)
    # Ne ≈ π / (4μ), where μ = 2.5e-8
    if pi_est > 0:
        ne_estimate = pi_est / (4 * 2.5e-8)
        # Set range from 0.1x to 10x of estimate
        ne_min = max(1000, int(ne_estimate * 0.1))
        ne_max = min(100000, int(ne_estimate * 10))
    else:
        ne_min, ne_max = 5000, 50000
    
    # Infer demographic history from Tajima's D
    if tajima_d < -1.5:
        # Strongly negative: recent population expansion
        texp_min, texp_max = 50, 5000
        resize_min, resize_max = 2.0, 50.0
        demographic_inference = "Recent rapid population expansion"
    elif tajima_d < -0.5:
        # Moderately negative: moderate expansion
        texp_min, texp_max = 100, 10000
        resize_min, resize_max = 1.5, 20.0
        demographic_inference = "Moderate population expansion"
    elif tajima_d > 1.0:
        # Positive: population bottleneck or balancing selection
        texp_min, texp_max = 500, 20000
        resize_min, resize_max = 0.1, 2.0
        demographic_inference = "Population bottleneck or balancing selection"
    else:
        # Near zero: relatively stable population
        texp_min, texp_max = 200, 15000
        resize_min, resize_max = 0.5, 5.0
        demographic_inference = "Relatively stable population history"
    
    # Further adjust based on rare allele ratio
    if rare_ratio > 0.4:
        # High rare allele ratio: recent expansion
        texp_max = min(texp_max, 3000)
        resize_min = max(resize_min, 2.0)
    elif rare_ratio < 0.15:
        # Low rare allele ratio: ancient event or bottleneck
        texp_min = max(texp_min, 1000)
        resize_max = min(resize_max, 2.0)
    
    return {
        "sample_size": n_alleles,
        "npop_range": f"{ne_min} {ne_max}",
        "texp_range": f"{texp_min} {texp_max}",
        "resize_range": f"{resize_min:.1f} {resize_max:.1f}",
        "mutation_rate": "2.5e-8",
        "estimated_ne": ne_estimate if pi_est > 0 else "unknown",
        "demographic_inference": demographic_inference,
        "sfs_features": sfs_analysis,
        "parameter_rationale": f"Based on pi={pi_est:.6f}, Tajima_D≈{tajima_d:.2f}, rare_alleles={rare_ratio:.3f}"
    }

def get_default_parameters() -> Dict[str, Any]:
    """Default parameter settings"""
    return {
        "sample_size": 70,
        "npop_range": "1000 50000",
        "texp_range": "100 20000", 
        "resize_range": "0.1 10.0",
        "mutation_rate": "2.5e-8",
        "estimated_ne": "unknown",
        "demographic_inference": "Default parameter set",
        "parameter_rationale": "Using default parameters due to insufficient data"
    }

# =========================
#        Phase LangGraph (single population processing)
# =========================
class PopulationState(TypedDict, total=False):
    # constants
    id: str
    population: str
    obs_file: str
    task: Dict[str, Any]
    max_retries: int
    output_dir: str

    # dynamic
    attempt: int
    plan_json: Dict[str, Any]
    shell: List[str]
    outputs: List[str]
    exec_result: Dict[str, Any]
    verified: bool
    ok: bool
    events: List[Dict[str, Any]]

def pop_plan_node(state: PopulationState, task_agent, vectorstore=None) -> PopulationState:
    # Search knowledge base for related configs
    reference_configs = ""
    if vectorstore:
        search_query = f"single population {state['population']} FastSimCoal2 configuration template estimation file"
        reference_configs = search_fastsimcoal_knowledge(vectorstore, search_query, k=3)
        print(f"[KNOWLEDGE BASE] Found reference configurations for {state['population']}")
    
    # Auto-set parameters from SFS data
    obs_file = state["obs_file"]
    population = state["population"]
    data_params = get_data_driven_parameters(obs_file, population)
    
    print(f"[DATA ANALYSIS] Parameters for {population}:")
    print(f"  - Ne range: {data_params.get('npop_range', 'unknown')}")
    print(f"  - Time range: {data_params.get('texp_range', 'unknown')}")
    print(f"  - Size change range: {data_params.get('resize_range', 'unknown')}")
    print(f"  - Demographic inference: {data_params.get('demographic_inference', 'unknown')}")
    print(f"  - Rationale: {data_params.get('parameter_rationale', 'unknown')}")
    
    # Build payload with knowledge base and data analysis
    payload = {
        "task": state["task"], 
        "id": state["id"],
        "reference_configs": reference_configs,
        "data_driven_params": data_params
    }
    
    print(f"[AGENT INPUT] {state['population']} single population analysis planning:")
    print(f"[AGENT INPUT] {json.dumps({k: v for k, v in payload.items() if k not in ['reference_configs', 'data_driven_params']}, indent=2)}")
    if reference_configs:
        print(f"[KNOWLEDGE BASE] Reference configurations loaded")
    print(f"[DATA DRIVEN] Using parameters based on SFS analysis")
    
    resp = task_agent.invoke({"input": json.dumps(payload)})
    print(f"[AGENT OUTPUT] Raw response:")
    print(f"[AGENT OUTPUT] {resp}")
    
    formatted_resp = Json_Format_Agent(resp)
    print(f"[AGENT OUTPUT] Formatted response:")
    print(f"[AGENT OUTPUT] {formatted_resp}")
    
    try:
        plan = json.loads(formatted_resp)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse JSON: {e}")
        plan = {"shell": [], "analyze": f"JSON parsing failed: {e}", "output_filename": [], "stats": False}
    
    state["plan_json"] = plan
    state["shell"] = plan.get("shell", [])
    state["outputs"] = plan.get("output_filename", [])
    state["attempt"] = 0
    state.setdefault("events", []).append({
        "event": "plan",
        "population": state["population"],
        "payload": payload,
        "plan": plan
    })
    return state

def pop_exec_node(state: PopulationState) -> PopulationState:
    state["attempt"] = int(state.get("attempt", 0)) + 1
    script_path = os.path.join(state["output_dir"], f"{state['population']}_single_{state['attempt']}.sh")
    result = execute_shell_array(state.get("shell", []), script_path)
    state["exec_result"] = result
    state.setdefault("events", []).append({
        "event": "exec",
        "attempt": state["attempt"],
        "population": state["population"],
        "script": result.get("script"),
        "shell": result.get("shell"),
        "rc": result.get("rc"),
        "stdout": result.get("stdout"),
        "stderr": result.get("stderr")
    })
    return state

def pop_verify_node(state: PopulationState) -> PopulationState:
    exec_result = state.get("exec_result", {})
    exec_rc = exec_result.get("rc", "1")
    
    if exec_rc != "0":
        print(f"[VERIFY] Execution failed with RC={exec_rc}, skipping file verification")
        ok = False
    else:
        ok = verify_single_pop_analysis(state["output_dir"], state["population"])
    
    state["verified"] = ok
    state.setdefault("events", []).append({
        "event": "verify",
        "attempt": state["attempt"],
        "population": state["population"],
        "verified": ok,
        "expected_outputs": state.get("outputs", []),
        "exec_rc": exec_rc
    })
    return state

def pop_decider(state: PopulationState) -> str:
    if state.get("verified"):
        return "end_success"
    if int(state.get("attempt", 0)) >= int(state.get("max_retries", 3)):
        return "end_fail"
    return "debug"

def pop_debug_node(state: PopulationState, debug_agent) -> PopulationState:
    debug_input = {
        "task": state["task"],
        "id": state["id"],
        "shell": state.get("shell", []),
        "result": f"RC={state.get('exec_result', {}).get('rc')}\\nSTDOUT:\\n{state.get('exec_result', {}).get('stdout','')}\\nSTDERR:\\n{state.get('exec_result', {}).get('stderr','')}\\n"
    }
    
    print(f"[DEBUG INPUT] {state['population']} debugging:")
    print(f"[DEBUG INPUT] {json.dumps(debug_input, indent=2)}")
    
    dbg_resp = debug_agent.invoke({"input": json.dumps(debug_input)})
    print(f"[DEBUG OUTPUT] Raw response:")
    print(f"[DEBUG OUTPUT] {dbg_resp}")
    
    formatted_resp = Json_Format_Agent(dbg_resp)
    print(f"[DEBUG OUTPUT] Formatted response:")
    print(f"[DEBUG OUTPUT] {formatted_resp}")
    
    try:
        dbg_plan = json.loads(formatted_resp)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse debug JSON: {e}")
        dbg_plan = {"shell": [], "analyze": f"Debug JSON parsing failed: {e}", "output_filename": [], "stats": False}
    
    new_shell = dbg_plan.get("shell", [])
    new_outputs = dbg_plan.get("output_filename", []) or state.get("outputs", [])

    state["shell"] = new_shell
    state["outputs"] = new_outputs
    state.setdefault("events", []).append({
        "event": "debug",
        "attempt": state["attempt"],
        "population": state["population"],
        "debug_input": debug_input,
        "debug_plan": dbg_plan
    })
    return state

def pop_end_success(state: PopulationState) -> PopulationState:
    state["ok"] = True
    state.setdefault("events", []).append({
        "event": "end_success",
        "attempt": state["attempt"],
        "population": state["population"]
    })
    return state

def pop_end_fail(state: PopulationState) -> PopulationState:
    state["ok"] = False
    state.setdefault("events", []).append({
        "event": "end_fail",
        "attempt": state["attempt"],
        "population": state["population"]
    })
    return state

def run_population_graph(task_agent, debug_agent, population: str, obs_file: str, task_payload: Dict[str, Any], out_id: str, max_retries: int, output_dir: str, vectorstore=None) -> Dict[str, Any]:
    """Run LangGraph analysis for a single population"""
    print(f"[INFO] Starting single population analysis for {population}")
    
    # Build graph
    g = StateGraph(PopulationState)
    g.add_node("plan", lambda s: pop_plan_node(s, task_agent, vectorstore))
    g.add_node("exec", pop_exec_node)
    g.add_node("verify", pop_verify_node)
    g.add_node("debug", lambda s: pop_debug_node(s, debug_agent))
    g.add_node("end_success", pop_end_success)
    g.add_node("end_fail", pop_end_fail)

    # edges
    g.set_entry_point("plan")
    g.add_edge("plan", "exec")
    g.add_edge("exec", "verify")

    # conditional from verify
    try:
        g.add_conditional_edges("verify", pop_decider, {
            "end_success": "end_success",
            "debug": "debug",
            "end_fail": "end_fail"
        })
    except Exception:
        g.add_edge("verify", "debug")

    g.add_edge("debug", "exec")
    graph = g.compile()

    init_state: PopulationState = {
        "id": out_id,
        "population": population,
        "obs_file": obs_file,
        "task": task_payload,
        "max_retries": max_retries,
        "output_dir": output_dir,
        "attempt": 0,
        "ok": False,
        "events": []
    }

    # run
    final_state = graph.invoke(init_state)

    # write logs
    trace_path = os.path.join(output_dir, f"{population}_single_trace.json")
    write_json(trace_path, {
        "id": out_id,
        "population": population,
        "obs_file": obs_file,
        "task": task_payload,
        "attempts": final_state.get("attempt", 0),
        "ok": final_state.get("ok", False),
        "events": final_state.get("events", [])
    })

    return {
        "ok": final_state.get("ok", False),
        "attempt": final_state.get("attempt", 0),
        "outputs": final_state.get("outputs", []),
        "exec_result": final_state.get("exec_result", {}),
        "trace_path": trace_path
    }

# =========================
#        Main processing nodes
# =========================
def single_pop_agent_node(state: SinglePopAgentState) -> SinglePopAgentState:
    """Main single population analysis node"""
    if "max_retries" not in state:
        state["max_retries"] = 3

    output_id = state.get("id", "001")
    data_dir = state.get("data_dir", f"./output/{output_id}/ana/data")
    ana_dir = os.path.join(".", "output", output_id, "ana")
    single_pop_dir = os.path.join(ana_dir, "single_pop")
    os.makedirs(single_pop_dir, exist_ok=True)

    # LLM agents
    api_key = state.get("api_key", "")
    base_url = state.get("base_url", "")
    model = state.get("model", "claude-opus-4-1-20250805")
    task_agent = create_llm_agent(api_key, base_url, model, TASK_PROMPT, TASK_EXAMPLES)
    debug_agent = create_llm_agent(api_key, base_url, model, DEBUG_PROMPT, DEBUG_EXAMPLES)
    
    # Initialize knowledge base
    vectorstore = None
    if api_key and base_url:
        try:
            vectorstore = load_fastsimcoal_knowledge_base(api_key, base_url)
        except Exception as e:
            print(f"[WARNING] Failed to load knowledge base: {e}")
            vectorstore = None

    # Auto-discover _MAFpop0.obs files
    # **CRITICAL**: ONLY search in the current analysis data_dir, NOT in ./data/
    # This ensures we use obs files generated for THIS specific analysis
    print(f"[INFO] Discovering _MAFpop0.obs files in {data_dir}")
    obs_pattern = os.path.join(data_dir, "*_MAFpop0.obs")
    obs_files = glob.glob(obs_pattern)
    
    # DO NOT fall back to ./data/ directory - this would use wrong populations
    # If no files found, it means obs_agent failed and we should report this
    if not obs_files:
        state["ok"] = False
        state["analysis"] = f"No _MAFpop0.obs files found in {data_dir}"
        state["outputs"] = {}
        return state

    print(f"[INFO] Found {len(obs_files)} single population obs files: {[os.path.basename(f) for f in obs_files]}")

    # Process each population
    results = {}
    all_success = True
    
    for obs_file in obs_files:
        # Extract population name from filename
        basename = os.path.basename(obs_file)
        population = basename.replace("_MAFpop0.obs", "")
        
        print(f"[INFO] Processing population: {population}")
        
        # Create output directory for this population
        pop_output_dir = os.path.join(single_pop_dir, population)
        os.makedirs(pop_output_dir, exist_ok=True)
        
        # Build task payload
        task_payload = {
            "phase": "single_pop_analysis",
            "population": population,
            "obs_file": obs_file,
            "output_dir": pop_output_dir,
            "mutation_rate": 2.5e-8,
            "generation_time": 25,
            "goal": state.get("goal", f"Single population demographic analysis for {population}"),
            "description": f"FastSimCoal2 demographic modeling for {population} using {basename}",
            "obs_file_source": obs_file  # Save original obs path for copying
        }
        
        # Run analysis for this population
        pop_result = run_population_graph(
            task_agent, debug_agent, population, obs_file, 
            task_payload, output_id, state["max_retries"], 
            pop_output_dir, vectorstore
        )
        
        results[population] = pop_result
        if not pop_result["ok"]:
            all_success = False
            print(f"[WARNING] Analysis failed for population {population}")
        else:
            print(f"[SUCCESS] Analysis completed for population {population}")

    # Aggregate results
    successful_pops = [pop for pop, result in results.items() if result["ok"]]
    failed_pops = [pop for pop, result in results.items() if not result["ok"]]
    
    state["ok"] = all_success
    if all_success:
        state["analysis"] = f"Successfully completed single population analysis for {len(successful_pops)} populations: {', '.join(successful_pops)}"
    else:
        state["analysis"] = f"Completed analysis for {len(successful_pops)} populations, failed for {len(failed_pops)} populations. Successful: {', '.join(successful_pops) if successful_pops else 'none'}. Failed: {', '.join(failed_pops) if failed_pops else 'none'}"
    
    # Collect output files
    outputs = {}
    for population, result in results.items():
        if result["ok"]:
            pop_dir = os.path.join(single_pop_dir, population)
            outputs[f"{population}_config_files"] = [
                os.path.join(pop_dir, f"{population}_single.tpl"),
                os.path.join(pop_dir, f"{population}_single.est")
            ]
            outputs[f"{population}_trace"] = result.get("trace_path", "")
            
            # Find FastSimCoal2 output files - prefer moved location
            results_dir = os.path.join(pop_dir, "results")
            bestlhoods_file = os.path.join(results_dir, f"{population}_single.bestlhoods")
            
            if file_nonempty(bestlhoods_file):
                outputs[f"{population}_results_dir"] = results_dir
                outputs[f"{population}_bestlhoods"] = bestlhoods_file
            else:
                # Check original location
                fsc_output_dir = os.path.join(pop_dir, f"{population}_single")
                root_bestlhoods = f"{population}_single.bestlhoods"
                if os.path.isdir(fsc_output_dir):
                    outputs[f"{population}_results_dir"] = fsc_output_dir
                elif file_nonempty(root_bestlhoods):
                    outputs[f"{population}_bestlhoods"] = root_bestlhoods
    
    state["outputs"] = outputs
    
    # ---------- Phase 4: Generate analysis report
    print("[INFO] Phase 4: Generating single population analysis report")
    try:
        report_content = generate_single_pop_report(output_id, ana_dir, single_pop_dir, results)
        
        # Save report to file
        report_path = os.path.join(ana_dir, "single_pop_report.txt")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # Print report
        print("\n" + "="*80)
        print("SINGLE POPULATION ANALYSIS REPORT")
        print("="*80)
        print(report_content)
        print("="*80)
        
        # Add report path to output
        outputs["analysis_report"] = report_path
        state["outputs"] = outputs
        
        print(f"[INFO] Report saved to: {report_path}")
        
    except Exception as e:
        print(f"[ERROR] Failed to generate report: {e}")
        import traceback
        traceback.print_exc()
    
    return state

# =========================
#        Graph construction and execution
# =========================
def build_single_pop_graph():
    g = StateGraph(SinglePopAgentState)
    g.add_node("single_pop_agent", single_pop_agent_node)
    g.set_entry_point("single_pop_agent")
    g.add_edge("single_pop_agent", END)
    return g.compile()

# =========================
#        Public interface
# =========================
def run_single_pop_agent(goal: str = "", data_dir: str = "", output_id: str = "001", 
                         max_retries: int = 3, api_key: str = "", base_url: str = "", 
                         model: str = "claude-opus-4-1-20250805") -> Dict[str, Any]:
    """Run SinglePopAgent for single population analysis"""
    
    # If data_dir not specified, use default path
    if not data_dir:
        data_dir = f"./output/{output_id}/ana/data"
    
    if not goal:
        goal = "Single population demographic analysis using FastSimCoal2 for all discovered populations"
    
    graph = build_single_pop_graph()
    init_state: SinglePopAgentState = {
        "goal": goal,
        "data_dir": data_dir,
        "populations": [],
        "obs_files": {},
        "id": output_id,
        "max_retries": max_retries,
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "ok": False,
        "analysis": "",
        "outputs": {}
    }
    
    final_state = graph.invoke(init_state)
    
    return {
        "success": final_state.get("ok", False),
        "analysis": final_state.get("analysis", ""),
        "outputs": final_state.get("outputs", {}),
        "populations": list(final_state.get("outputs", {}).keys())
    }

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from config_loader import get_llm_config
    cfg = get_llm_config()

    print("Testing SinglePopAgent...")
    result = run_single_pop_agent(
        goal="Single population demographic analysis for YRI, CEU, CHB populations using FastSimCoal2",
        output_id="061",
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        model=cfg.get("default_model", "claude-opus-4-1-20250805"),
        max_retries=3,
    )
    print("SinglePopAgent Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
