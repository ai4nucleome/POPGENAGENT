#!/usr/bin/env python3
"""
ObsAgent - Observed Data Processing Agent
Agent-driven pipeline: bed/bim/fam -> VCF -> sample_pop.txt -> easySFS
All shell generation and debugging are performed by LLM agents via a LangGraph per phase.

Enhancements in this version:
1) Full JSON logging for every phase:
   - {ana_dir}/{phase}_trace.json: chronological event log with agent plans, shells, stdout, stderr, verification, and debug rounds
   - {ana_dir}/{phase}_final.json: phase summary and produced outputs
2) Debug flow is implemented with LangGraph nodes:
   plan -> exec -> verify -> (end_success | debug -> exec -> verify ... | end_fail)

"""

import os
import json
import subprocess
from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, END

# LLM
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser

# =========================
#         State definition
# =========================
class ObsAgentState(TypedDict, total=False):
    goal: str
    bfile_prefix: str
    pops: List[str]                 # optional, prefer agent to infer from goal
    id: str
    max_retries: int
    workdir: str

    # easySFS related
    easy_sfs_py: str
    proj_override: Optional[str]
    easy_out_name: Optional[str]

    # LLM related
    api_key: str
    base_url: str
    model: str

    # Run intermediate results
    ok: bool
    analysis: str
    outputs: Dict[str, str]

# =========================
#       Utility functions (minimal set)
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

# JSON formatter, ensures agent output is parseable
def Json_Format_Agent(text: str) -> str:
    if not text or not text.strip():
        return '{"shell": [], "analyze": "empty response", "output_filename": [], "stats": false}'
    try:
        json.loads(text)
        return text
    except Exception:
        pass
    # Fallback: extract outermost {...}
    import re, ast
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        s = m.group(0)
        try:
            json.loads(s); return s
        except Exception:
            try:
                d = ast.literal_eval(s)  # single quotes -> dict
                return json.dumps(d)
            except Exception:
                pass
    return '{"shell": [], "analyze": "failed to parse json", "output_filename": [], "stats": false}'

# =========================
#       PROMPT definition
# =========================
TASK_PROMPT = """You are a senior bioinformatics engineer and shell scripting expert.
Return VALID JSON ONLY with keys: "shell", "analyze", "output_filename", "stats".
- "shell": array of shell strings, each string is one full command line.
- "analyze": short paragraph using only periods and commas, no quotes.
- "output_filename": array of expected output paths.
- "stats": boolean.

You must complete the requested PHASE using ONLY shell commands, writing all outputs directly to data_dir.
Never include backticks or comments outside JSON. Do not include any extra text.

CRITICAL - POPULATION DETECTION:
- ALWAYS read populations from the goal text FIRST (e.g., "A, B, C" or "YRI, CEU, CHB")
- Extract population names from goal using pattern matching
- For generic names like "A", "B", "C", they are UPPERCASE single letters
- Match populations EXACTLY as specified in goal (case-sensitive)
- If goal mentions "A,B,C" or "A, B, C", use regex pattern ^[A-C]$ in awk
- If goal mentions "YRI,CEU,CHB", use pattern (YRI|CEU|CHB) in awk
- DO NOT use hardcoded population lists that don't match the goal

Scope:
1) VCF conversion: plink --recode vcf-iid, write {{id}}_obs.vcf to data_dir.
2) Sample-pop map: TSV two columns "sample_id<TAB>population", write {{id}}_sample_pop.txt to data_dir.
   **CRITICAL**: Extract populations from task.goal text first!
   - If goal says "A,B,C" → filter for populations matching ^[A-C]$ pattern
   - If goal says "YRI,CEU,CHB" → filter for populations matching (YRI|CEU|CHB) pattern
   - Parse the goal string to build the awk pattern dynamically
   Detect whether fam has population in col1 or col2, and output sample in col2 or col1 accordingly.
   Avoid grep with set -e, do filtering in awk to prevent exit code 1.
3) easySFS: Use VCF and sample-pop from previous phase outputs, run folded SFS with robust projections.
   For obs_generation phase: Use task.vcf_file and task.popmap_file as inputs (generated from phase 1).
   If proj_override provided use it, else compute per-pop projections automatically from sample_pop.txt:
     v = even(n-2), clip 2..70, ensure even number.
   Build output dir name if not provided: k{{K}}_{{POP1}}_{{POP2}}..., write directly under data_dir.

INPUT FILES HANDLING:
- For vcf_conversion phase: Use task.bfile_prefix for PLINK binary files.
- For obs_generation phase: Use task.vcf_file and task.popmap_file (outputs from phase 1).
- Always check if input files exist before using them.

Dependencies rule:
- If a tool is missing, install via conda or pip with non-interactive flags where applicable.
- easySFS may require dadi, fix "ModuleNotFoundError: Spectrum" by installing dadi and replacing import to "from dadi import Spectrum", or by exporting PYTHONPATH to include easySFS dir.

Acceptance criteria for stats=true:
- For VCF phase: {{id}}_obs.vcf exists and non-empty, {{id}}_sample_pop.txt exists and non-empty.
- For OBS phase: easySFS output directory exists and contains at least one file.

Return JSON only.
"""

DEBUG_PROMPT = """You are a senior bioinformatics engineer and shell debugging expert.
Given the previous execution result, return VALID JSON ONLY with: "shell", "analyze", "output_filename", "stats".
- "shell": array of corrected shell commands to fix the failure, then rerun the failed step(s).
- "analyze": brief paragraph with only periods and commas.
- "output_filename": expected output paths after fix.
- "stats": false unless you are certain all acceptance criteria are met, in which case provide empty shell and set true.

Common fixes you may use:
- Install missing binaries via conda -y, e.g., conda install -y -c conda-forge -c bioconda plink.
- easySFS "ModuleNotFoundError: Spectrum": python -m pip install -U dadi, and sed -i 's/from Spectrum import Spectrum/from dadi import Spectrum/' easySFS.py, or export PYTHONPATH to include the script directory, then rerun.
- Recompute sample-pop map with robust awk if empty.
- Compute projections from sample_pop.txt if invalid, ensure even numbers, 2..70.
- Ensure outputs are written directly to data_dir, use --out and proper redirections.

PATH AND DIRECTORY ERRORS FIXES:
- If "FileNotFoundError" or "No such file or directory" appears: Check if working directory exists, correct paths in commands, create missing directories with mkdir -p.
- If path contains typos (e.g. wrong project directory name), correct the path references.
- If relative paths fail, convert to absolute paths or adjust working directory with cd commands.
- If script execution fails due to wrong cwd, add cd commands to navigate to correct directory before running commands.
- Check if input files (.bed, .bim, .fam) exist at specified paths and correct paths if needed.

SYSTEMATIC DEBUGGING APPROACH:
- First identify the root cause: missing files, wrong paths, missing dependencies, or permission issues.
- For path errors: verify directory structure, correct typos, ensure working directory is set properly.
- For missing tools: install via conda with proper channels.
- For permission errors: check file permissions and working directory access.
- Test file existence before using files in commands.

Return JSON only.
"""

# —— Note: Examples use Python's True/False —— #
TASK_EXAMPLES = [
    {
        "input": {"task": {"phase": "vcf_conversion", "goal": "I have data about A,B,C three populations", "bfile_prefix": "./data/abc", "pops": [], "ana_dir": "./output/071/ana", "data_dir": "./output/071/ana/data", "easy_sfs_py": "./scripts/easySFS.py"}, "id": "071"},
        "output": {"shell": [
            "mkdir -p ./output/071/ana/data",
            "command -v plink >/dev/null 2>&1 || conda install -y -c conda-forge -c bioconda plink",
            "plink --bfile ./data/abc --recode vcf-iid --out ./output/071/ana/data/071_obs",
            "awk 'BEGIN{OFS=\"\\t\"} NF>=2 { if ($2 ~ /^[A-C]$/) {s=$1;p=$2} else if ($1 ~ /^[A-C]$/) {s=$2;p=$1} else {s=$2;p=$1} if (p==\"A\"||p==\"B\"||p==\"C\") print s,p }' ./data/abc.fam > ./output/071/ana/data/071_sample_pop.txt"
        ], "analyze": "convert plink binary to vcf and extract populations A B C from goal text then build sample population mapping using awk pattern matching for single letter populations", "output_filename": ["./output/071/ana/data/071_obs.vcf", "./output/071/ana/data/071_sample_pop.txt"], "stats": False}
    },
    {
        "input": {"task": {"phase": "vcf_conversion", "goal": "YRI CEU CHB three populations", "bfile_prefix": "./data/1000GP_pruned", "pops": [], "ana_dir": "./output/061/ana", "data_dir": "./output/061/ana/data", "easy_sfs_py": "./scripts/easySFS.py"}, "id": "061"},
        "output": {"shell": [
            "mkdir -p ./output/061/ana/data",
            "command -v plink >/dev/null 2>&1 || conda install -y -c conda-forge -c bioconda plink",
            "plink --bfile ./data/1000GP_pruned --recode vcf-iid --out ./output/061/ana/data/061_obs",
            "awk 'BEGIN{OFS=\"\\t\"} NF>=2 { if ($2 ~ /^[A-Z]{3}$/) {s=$1;p=$2} else if ($1 ~ /^[A-Z]{3}$/) {s=$2;p=$1} else {s=$2;p=$1} if (p==\"YRI\"||p==\"CEU\"||p==\"CHB\") print s,p }' ./data/1000GP_pruned.fam > ./output/061/ana/data/061_sample_pop.txt"
        ], "analyze": "convert plink binary to vcf and extract populations YRI CEU CHB from goal text then build sample population mapping using awk pattern matching for three letter population codes", "output_filename": ["./output/061/ana/data/061_obs.vcf", "./output/061/ana/data/061_sample_pop.txt"], "stats": False}
    },
    {
        "input": {"task": {"phase": "obs_generation", "goal": "YRI CEU CHB CHS four populations", "vcf_file": "./output/061/ana/data/061_obs.vcf", "popmap_file": "./output/061/ana/data/061_sample_pop.txt", "input_files": ["./output/061/ana/data/061_obs.vcf", "./output/061/ana/data/061_sample_pop.txt"], "pops": [], "ana_dir": "./output/061/ana", "data_dir": "./output/061/ana/data", "easy_sfs_py": "./scripts/easySFS.py", "easy_out_name": "k4_YRI_CEU_CHB_CHS"}, "id": "061"},
        "output": {"shell": [
            "test -f ./output/061/ana/data/061_obs.vcf || { echo VCF file missing 1>&2; exit 1; }",
            "test -f ./output/061/ana/data/061_sample_pop.txt || { echo sample_pop file missing 1>&2; exit 1; }",
            "mkdir -p ./output/061/ana/data/k4_YRI_CEU_CHB_CHS",
            "python - << 'PY'\nimport os\npp='./output/061/ana/data/061_sample_pop.txt'\nfrom collections import Counter\nc=Counter([l.strip().split()[1] for l in open(pp) if l.strip()])\npops=sorted(c.keys())\nvals=[]\nfor p in pops:\n    n=c.get(p,0)\n    v=max(2,min(70,n-2))\n    v=v if v%2==0 else v-1\n    v=max(2,v)\n    vals.append(str(v))\nopen('./output/061/ana/data/061_proj.txt','w').write(','.join(vals))\nPY",
            "test -f ./scripts/easySFS.py || { echo easySFS.py missing 1>&2; exit 1; }",
            "python ./scripts/easySFS.py -i ./output/061/ana/data/061_obs.vcf -p ./output/061/ana/data/061_sample_pop.txt -a --proj $(cat ./output/061/ana/data/061_proj.txt) -o ./output/061/ana/data/k4_YRI_CEU_CHB_CHS"
        ], "analyze": "verify input files exist then compute dynamic projections for all populations found in sample mapping file and run easySFS with folded spectra using phase 1 outputs", "output_filename": ["./output/061/ana/data/k4_YRI_CEU_CHB_CHS"], "stats": False}
    }
]

DEBUG_EXAMPLES = [
    {
        "input": {"task": {"phase": "obs_generation", "bfile_prefix": "./data/1000GP_pruned", "ana_dir": "./output/061/ana", "data_dir": "./output/061/ana/data", "easy_sfs_py": "./scripts/easySFS.py"}, "result": "ModuleNotFoundError: No module named 'Spectrum'", "id": "061", "shell": ["python ./scripts/easySFS.py -i ./output/061/ana/data/061_obs.vcf -p ./output/061/ana/data/061_sample_pop.txt -a --proj 50,50,50 -o ./output/061/ana/data/k3_YRI_CEU_CHB"]},
        "output": {"shell": [
            "python -m pip install -U dadi || pip install -U dadi",
            "sed -i \"s/from Spectrum import Spectrum/from dadi import Spectrum/\" ./scripts/easySFS.py || true",
            "export PYTHONPATH=$(dirname ./scripts/easySFS.py):$PYTHONPATH",
            "mkdir -p ./output/061/ana/data/k3_YRI_CEU_CHB",
            "python ./scripts/easySFS.py -i ./output/061/ana/data/061_obs.vcf -p ./output/061/ana/data/061_sample_pop.txt -a --proj 50,50,50 -o ./output/061/ana/data/k3_YRI_CEU_CHB"
        ], "analyze": "install dadi and fix import then rerun easySFS with the same parameters", "output_filename": ["./output/061/ana/data/k3_YRI_CEU_CHB"], "stats": False}
    },
    {
        "input": {"task": {"phase": "vcf_conversion", "bfile_prefix": "./data/1000GP_pruned", "ana_dir": "./output/061/ana", "data_dir": "./output/061/ana/data"}, "result": "RC=2\nSTDOUT:\n\nSTDERR:\nFileNotFoundError: [Errno 2] No such file or directory: './data1'. Working directory may not exist or script execution failed.", "id": "061", "shell": ["mkdir -p ./output/061/ana/data", "plink --bfile ./data/1000GP_pruned --recode vcf-iid --out ./output/061/ana/data/061_obs"]},
        "output": {"shell": [
            "mkdir -p ./output/061/ana/data",
            "command -v plink >/dev/null 2>&1 || conda install -y -c conda-forge -c bioconda plink",
            "plink --bfile ./data/1000GP_pruned --recode vcf-iid --out ./output/061/ana/data/061_obs",
            "awk 'BEGIN{OFS=\"\\t\"} NF>=2 { if ($2 ~ /^[A-Z]{3}$/) {s=$1;p=$2} else if ($1 ~ /^[A-Z]{3}$/) {s=$2;p=$1} else {s=$2;p=$1} if (p==\"YRI\"||p==\"CEU\"||p==\"CHB\") print s,p }' ./data/1000GP_pruned.fam > ./output/061/ana/data/061_sample_pop.txt"
        ], "analyze": "working directory does not exist so navigate to correct directory first then run plink conversion and create sample population mapping", "output_filename": ["./output/061/ana/data/061_obs.vcf", "./output/061/ana/data/061_sample_pop.txt"], "stats": False}
    }
]

# =========================
#       LLM construction
# =========================
def create_llm_agent(api_key: str, base_url: str, model: str, prompt_template: str, examples: List[Dict]):
    print(f"[DEBUG] Creating LLM agent with model: {model}, base_url: {base_url}")
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
    print(f"[DEBUG] LLM agent created successfully")
    return agent

# =========================
#        Execution and verification
# =========================
def execute_shell_array(shell_cmds: List[str], script_path: str, workdir: str, timeout: int = 1800) -> Dict[str, str]:
    content = "#!/bin/bash\nset -euo pipefail\n" + "\n".join(shell_cmds) + "\n"
    write_text(script_path, content)
    os.chmod(script_path, 0o755)
    print(f"[EXEC] Running {script_path}")
    try:
        p = subprocess.run(["bash", script_path], capture_output=True, text=True, timeout=timeout, cwd=workdir)
        return {
            "rc": str(p.returncode),
            "stdout": (p.stdout or "")[:MAX_STD_CHARS],
            "stderr": (p.stderr or "")[:MAX_STD_CHARS],
            "script": script_path,
            "shell": shell_cmds
        }
    except subprocess.TimeoutExpired:
        return {"rc": "124", "stdout": "", "stderr": "TimeoutExpired", "script": script_path, "shell": shell_cmds}
    except FileNotFoundError as e:
        error_msg = f"FileNotFoundError: {str(e)}. Working directory '{workdir}' may not exist or script execution failed."
        print(f"[ERROR] {error_msg}")
        return {"rc": "2", "stdout": "", "stderr": error_msg, "script": script_path, "shell": shell_cmds}
    except PermissionError as e:
        error_msg = f"PermissionError: {str(e)}. Check permissions for script or working directory."
        print(f"[ERROR] {error_msg}")
        return {"rc": "13", "stdout": "", "stderr": error_msg, "script": script_path, "shell": shell_cmds}
    except Exception as e:
        error_msg = f"Unexpected error during script execution: {type(e).__name__}: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return {"rc": "1", "stdout": "", "stderr": error_msg, "script": script_path, "shell": shell_cmds}

def verify_phase(phase: str, data_dir: str, out_id: str, agent_outputs: List[str]) -> bool:
    if phase == "vcf_conversion":
        vcf = os.path.join(data_dir, f"{out_id}_obs.vcf")
        pop = os.path.join(data_dir, f"{out_id}_sample_pop.txt")
        ok = file_nonempty(vcf) and file_nonempty(pop)
        if not ok:
            ok = all([(file_nonempty(p) or dir_nonempty(p)) for p in agent_outputs])
        return ok
    elif phase == "obs_generation":
        if agent_outputs:
            for p in agent_outputs:
                if dir_nonempty(p):
                    return True
        try:
            for name in os.listdir(data_dir):
                p = os.path.join(data_dir, name)
                if os.path.isdir(p) and dir_nonempty(p):
                    return True
        except Exception:
            pass
        return False
    return False

# =========================
#        Phase LangGraph
# =========================
class PhaseState(TypedDict, total=False):
    # constants
    id: str
    phase: str
    task: Dict[str, Any]
    workdir: str
    max_retries: int
    ana_dir: str
    data_dir: str

    # dynamic
    attempt: int
    plan_json: Dict[str, Any]
    shell: List[str]
    outputs: List[str]
    exec_result: Dict[str, Any]
    verified: bool
    ok: bool
    events: List[Dict[str, Any]]  # for trace logging

def phase_plan_node(state: PhaseState, task_agent) -> PhaseState:
    payload = {"task": state["task"], "id": state["id"]}
    print(f"[AGENT INPUT] {state['phase']} phase planning:")
    print(f"[AGENT INPUT] {json.dumps(payload, indent=2)}")
    
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
        "phase": state["phase"],
        "payload": payload,
        "plan": plan
    })
    return state

def phase_exec_node(state: PhaseState) -> PhaseState:
    state["attempt"] = int(state.get("attempt", 0)) + 1
    script_path = os.path.join(state["ana_dir"], f"{state['phase']}_{state['attempt']}.sh")
    result = execute_shell_array(state.get("shell", []), script_path, state["workdir"])
    state["exec_result"] = result
    state.setdefault("events", []).append({
        "event": "exec",
        "attempt": state["attempt"],
        "script": result.get("script"),
        "shell": result.get("shell"),
        "rc": result.get("rc"),
        "stdout": result.get("stdout"),
        "stderr": result.get("stderr")
    })
    return state

def phase_verify_node(state: PhaseState) -> PhaseState:
    # First check if execution was successful (return code 0)
    exec_result = state.get("exec_result", {})
    exec_rc = exec_result.get("rc", "1")
    
    # If execution failed, verification should fail regardless of file existence
    if exec_rc != "0":
        print(f"[VERIFY] Execution failed with RC={exec_rc}, skipping file verification")
        ok = False
    else:
        # Only do file verification if execution was successful
        ok = verify_phase(state["phase"], state["data_dir"], state["id"], state.get("outputs", []))
    
    state["verified"] = ok
    state.setdefault("events", []).append({
        "event": "verify",
        "attempt": state["attempt"],
        "verified": ok,
        "expected_outputs": state.get("outputs", []),
        "exec_rc": exec_rc
    })
    return state

def phase_decider(state: PhaseState) -> str:
    if state.get("verified"):
        return "end_success"
    if int(state.get("attempt", 0)) >= int(state.get("max_retries", 3)):
        return "end_fail"
    return "debug"

def phase_debug_node(state: PhaseState, debug_agent) -> PhaseState:
    debug_input = {
        "task": state["task"],
        "id": state["id"],
        "shell": state.get("shell", []),
        "result": f"RC={state.get('exec_result', {}).get('rc')}\nSTDOUT:\n{state.get('exec_result', {}).get('stdout','')}\nSTDERR:\n{state.get('exec_result', {}).get('stderr','')}\n"
    }
    
    print(f"[DEBUG INPUT] {state['phase']} phase debugging:")
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
        "debug_input": debug_input,
        "debug_plan": dbg_plan
    })
    return state

def phase_end_success(state: PhaseState) -> PhaseState:
    state["ok"] = True
    state.setdefault("events", []).append({
        "event": "end_success",
        "attempt": state["attempt"]
    })
    return state

def phase_end_fail(state: PhaseState) -> PhaseState:
    state["ok"] = False
    state.setdefault("events", []).append({
        "event": "end_fail",
        "attempt": state["attempt"]
    })
    return state

def run_phase_graph(task_agent, debug_agent, task_payload: Dict[str, Any], workdir: str, out_id: str, max_retries: int, ana_dir: str, data_dir: str) -> Dict[str, Any]:
    """Build and run a per-phase LangGraph with plan, exec, verify, debug loops, and JSON logging."""
    phase = task_payload["phase"]
    trace_path = os.path.join(ana_dir, f"{phase}_trace.json")
    final_path = os.path.join(ana_dir, f"{phase}_final.json")

    # Build graph
    g = StateGraph(PhaseState)
    # wrap to bind agents
    g.add_node("plan", lambda s: phase_plan_node(s, task_agent))
    g.add_node("exec", phase_exec_node)
    g.add_node("verify", phase_verify_node)
    g.add_node("debug", lambda s: phase_debug_node(s, debug_agent))
    g.add_node("end_success", phase_end_success)
    g.add_node("end_fail", phase_end_fail)

    # edges
    g.set_entry_point("plan")
    g.add_edge("plan", "exec")
    g.add_edge("exec", "verify")

    # conditional from verify
    try:
        # Modern LangGraph supports add_conditional_edges
        g.add_conditional_edges("verify", phase_decider, {
            "end_success": "end_success",
            "debug": "debug",
            "end_fail": "end_fail"
        })
    except Exception:
        # Fallback: simple edge to debug, end will be decided inside debug node via max_retries check
        g.add_edge("verify", "debug")

    # loop back after debug
    g.add_edge("debug", "exec")

    graph = g.compile()

    init_state: PhaseState = {
        "id": out_id,
        "phase": phase,
        "task": task_payload,
        "workdir": workdir,
        "max_retries": max_retries,
        "ana_dir": ana_dir,
        "data_dir": data_dir,
        "attempt": 0,
        "ok": False,
        "events": []
    }

    # run
    final_state = graph.invoke(init_state)

    # write logs
    write_json(trace_path, {
        "id": out_id,
        "phase": phase,
        "task": task_payload,
        "attempts": final_state.get("attempt", 0),
        "ok": final_state.get("ok", False),
        "events": final_state.get("events", [])
    })

    summary = {
        "id": out_id,
        "phase": phase,
        "ok": final_state.get("ok", False),
        "attempts": final_state.get("attempt", 0),
        "outputs": final_state.get("outputs", []),
        "expected_outputs": final_state.get("outputs", []),
        "last_exec": final_state.get("exec_result", {}),
    }
    write_json(final_path, summary)

    # return compact result for upstream
    return {
        "ok": final_state.get("ok", False),
        "attempt": final_state.get("attempt", 0),
        "outputs": final_state.get("outputs", []),
        "exec_result": final_state.get("exec_result", {}),
        "trace_path": trace_path,
        "final_path": final_path
    }

# =========================
#        Top-level nodes: two phases
# =========================
def obs_agent_node(state: ObsAgentState) -> ObsAgentState:
    # Initialize
    if "max_retries" not in state:
        state["max_retries"] = 3

    output_id = state.get("id", "001")
    ana_dir = os.path.join(".", "output", output_id, "ana")
    data_dir = os.path.join(ana_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    # LLM agents
    api_key = state.get("api_key", "")
    base_url = state.get("base_url", "")
    model = state.get("model", "claude-opus-4-1-20250805")
    task_agent = create_llm_agent(api_key, base_url, model, TASK_PROMPT, TASK_EXAMPLES)
    debug_agent = create_llm_agent(api_key, base_url, model, DEBUG_PROMPT, DEBUG_EXAMPLES)

    # ---------- Phase 1: VCF + sample_pop by agent via LangGraph
    print("[INFO] Phase 1: VCF Conversion via agent")
    task1 = {
        "phase": "vcf_conversion",
        "goal": state.get("goal", ""),
        "description": "Convert PLINK bfile to VCF and build sample-pop mapping",
        "bfile_prefix": state["bfile_prefix"],
        "pops": state.get("pops", []),            # Can be empty, agent parses itself
        "easy_sfs_py": state.get("easy_sfs_py", "./scripts/easySFS.py"),
        "proj_override": state.get("proj_override"),
        "easy_out_name": state.get("easy_out_name"),
        "ana_dir": ana_dir,
        "data_dir": data_dir
    }
    r1 = run_phase_graph(task_agent, debug_agent, task1, state["workdir"], output_id, state["max_retries"], ana_dir, data_dir)
    if not r1["ok"]:
        state["ok"] = False
        state["analysis"] = "Failed in VCF conversion phase"
        return state

    # ---------- Phase 2: easySFS by agent via LangGraph
    print("[INFO] Phase 2: OBS Generation via agent")
    
    # Collect Phase 1 output files as Phase 2 input
    vcf_file = os.path.join(data_dir, f"{output_id}_obs.vcf")
    popmap_file = os.path.join(data_dir, f"{output_id}_sample_pop.txt")
    phase1_outputs = r1.get("outputs", [])
    
    # Build input file list including Phase 1 generated files
    input_files = []
    if os.path.exists(vcf_file):
        input_files.append(vcf_file)
    if os.path.exists(popmap_file):
        input_files.append(popmap_file)
    # Add other Phase 1 outputs
    for output_file in phase1_outputs:
        if os.path.exists(output_file) and output_file not in input_files:
            input_files.append(output_file)
    
    task2 = {
        "phase": "obs_generation",
        "goal": state.get("goal", ""),
        "description": "Run easySFS on VCF and mapping from Phase 1 outputs",
        "vcf_file": vcf_file,  # VCF file generated in Phase 1
        "popmap_file": popmap_file,  # Sample-population mapping file generated in Phase 1
        "input_files": input_files,  # All input file list
        "phase1_outputs": phase1_outputs,  # Phase 1 output list
        "pops": state.get("pops", []),            # Can be empty, agent decides output dir naming and projection
        "easy_sfs_py": state.get("easy_sfs_py", "./scripts/easySFS.py"),
        "proj_override": state.get("proj_override"),
        "easy_out_name": state.get("easy_out_name"),
        "ana_dir": ana_dir,
        "data_dir": data_dir
    }
    r2 = run_phase_graph(task_agent, debug_agent, task2, state["workdir"], output_id, state["max_retries"], ana_dir, data_dir)
    if not r2["ok"]:
        state["ok"] = False
        state["analysis"] = "Failed in OBS generation phase"
        return state

    # Aggregate output paths
    vcf_dest = os.path.join(data_dir, f"{output_id}_obs.vcf")
    popmap_dest = os.path.join(data_dir, f"{output_id}_sample_pop.txt")

    # Use agent-specified easySFS output dir, or fallback scan
    easy_dir = None
    for p in r2.get("outputs", []):
        if os.path.isdir(p) and dir_nonempty(p):
            easy_dir = p; break
    if not easy_dir:
        for name in os.listdir(data_dir):
            p = os.path.join(data_dir, name)
            if os.path.isdir(p) and dir_nonempty(p):
                easy_dir = p; break

    # ---------- Phase 3: Post-processing - Move obs files and clean redundant folders
    print("[INFO] Phase 3: Post-processing - Moving obs files and cleaning up")
    obs_files_moved = []
    
    if easy_dir and os.path.isdir(easy_dir):
        # Find all .obs files and move to data_dir
        for root, dirs, files in os.walk(easy_dir):
            for file in files:
                if file.endswith('.obs'):
                    src_path = os.path.join(root, file)
                    dest_path = os.path.join(data_dir, file)
                    try:
                        # If target file exists, rename to avoid conflict
                        counter = 1
                        original_dest_path = dest_path
                        while os.path.exists(dest_path):
                            name, ext = os.path.splitext(file)
                            dest_path = os.path.join(data_dir, f"{name}_{counter}{ext}")
                            counter += 1
                        
                        # Move file
                        import shutil
                        shutil.move(src_path, dest_path)
                        obs_files_moved.append(dest_path)
                        print(f"[INFO] Moved {src_path} -> {dest_path}")
                    except Exception as e:
                        print(f"[WARNING] Failed to move {src_path}: {e}")
        
        # Remove dadi subfolder (if exists)
        dadi_dir = os.path.join(easy_dir, "dadi")
        if os.path.isdir(dadi_dir):
            try:
                import shutil
                shutil.rmtree(dadi_dir)
                print(f"[INFO] Removed dadi directory: {dadi_dir}")
            except Exception as e:
                print(f"[WARNING] Failed to remove dadi directory {dadi_dir}: {e}")

    state["ok"] = True
    state["analysis"] = f"Successfully completed VCF conversion, OBS generation, and moved {len(obs_files_moved)} obs files"
    state["outputs"] = {
        "vcf": vcf_dest,
        "popmap": popmap_dest,
        "easySFS_dir": easy_dir or "",
        "obs_files": obs_files_moved,  # Add moved obs file list
        "vcf_trace": os.path.join(ana_dir, "vcf_conversion_trace.json"),
        "vcf_final": os.path.join(ana_dir, "vcf_conversion_final.json"),
        "obs_trace": os.path.join(ana_dir, "obs_generation_trace.json"),
        "obs_final": os.path.join(ana_dir, "obs_generation_final.json")
    }
    return state

# =========================
#        Graph construction and execution
# =========================
def build_obs_graph():
    g = StateGraph(ObsAgentState)
    g.add_node("obs_agent", obs_agent_node)
    g.set_entry_point("obs_agent")
    g.add_edge("obs_agent", END)
    return g.compile()

# =========================
#        Public interface
# =========================
def run_obs_agent(goal: str, datalist: List[str],
                  output_id: str = "001", easy_sfs_py: str = "./scripts/easySFS.py",
                  proj_override: str = "", easy_out_name: str = "",
                  max_retries: int = 3,
                  api_key: str = "",
                  base_url: str = "",
                  model: str = "claude-opus-4-1-20250805",
                  workdir: str = ".") -> Dict[str, Any]:

    # Infer bfile_prefix from datalist
    bfile_prefix = None
    if datalist:
        for p in datalist:
            if p.endswith(".bed"):
                bfile_prefix = p[:-4]
                break
    if not bfile_prefix:
        return {"success": False, "analysis": "Failed to extract bfile prefix from datalist", "outputs": {}, "attempts": 0}

    original_cwd = os.getcwd()
    try:
        # os.chdir(workdir)
        graph = build_obs_graph()
        init_state: ObsAgentState = {
            "goal": goal,
            "bfile_prefix": bfile_prefix,
            "pops": [],  # Let agent parse. For forced filtering pass ['YRI','CEU','CHB']
            "id": output_id,
            "max_retries": max_retries,
            "easy_sfs_py": easy_sfs_py,
            "proj_override": proj_override.strip() or None,
            "easy_out_name": easy_out_name.strip() or None,
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "workdir": workdir,
            "ok": False,
            "analysis": "",
            "outputs": {}
        }
        final_state = graph.invoke(init_state)
        return {
            "success": final_state.get("ok", False),
            "analysis": final_state.get("analysis", ""),
            "outputs": final_state.get("outputs", {}),
            "attempts": 1
        }
    finally:
        os.chdir(original_cwd)

# Test
if __name__ == "__main__":
    print("Testing ObsAgent...")
    datalist = [
        "./data/1000GP_pruned.bed",
        "./data/1000GP_pruned.bim",
        "./data/1000GP_pruned.fam"
    ]
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from config_loader import get_llm_config
    cfg = get_llm_config()

    result = run_obs_agent(
        goal="I have a data about YRI, CEU, CHB populations obs data, Based on the available data, conduct an inference of a migration and separation model for three populations.",
        datalist=datalist,
        easy_sfs_py="./scripts/easySFS.py",
        output_id="061",
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        model=cfg.get("default_model", "claude-opus-4-1-20250805"),
        workdir=os.getcwd(),
        max_retries=3,
    )
    print("ObsAgent Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
