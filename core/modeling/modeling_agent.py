#!/usr/bin/env python3
"""
ModelingAgent - Comprehensive Analysis and FastSimCoal Parameter Recommendation Agent

Provides comprehensive population genetics modeling recommendations and FastSimCoal parameter suggestions based on all analysis results
"""

import os
import json
import glob
from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, END

# LLM
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser

# =========================
#         State definition
# =========================
class ModelingAgentState(TypedDict, total=False):
    goal: str
    output_id: str
    ana_dir: str
    
    # Analysis report content
    pca_report: Optional[str]
    treemix_report: Optional[str]
    admixture_report: Optional[str]
    other_analysis_report: Optional[str]
    single_pop_report: Optional[str]
    
    # Modeling recommendation results
    modeling_recommendations: Optional[str]
    fastsimcoal_parameters: Optional[Dict[str, Any]]
    
    # Run status
    ok: bool
    analysis: str
    outputs: Dict[str, str]

# =========================
#       Utility functions
# =========================
def write_text(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def read_file_content(file_path: str) -> str:
    """Read file content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"[WARNING] Failed to read {file_path}: {e}")
        return ""

# =========================
#       PROMPT definition
# =========================
MODELING_PROMPT = """You are a senior bioinformatics and population genetics expert specializing in demographic modeling and FastSimCoal parameter optimization.

Your task is to analyze population genetics analysis results and provide expert recommendations for demographic modeling using FastSimCoal2.

IMPORTANT: You will receive analysis results that may be incomplete. Some analyses may have failed or not been completed. You must work with whatever data is available and provide the best possible recommendations based on the available information.

ANALYSIS REQUIREMENTS:
1. **Data Integration**: Synthesize findings from available analyses (PCA, TreeMix, Admixture, single population analysis, etc.)
2. **Demographic Model Design**: Propose appropriate demographic models based on available analysis results
3. **Parameter Recommendations**: Provide scientifically-informed FastSimCoal2 parameter ranges and settings
4. **Biological Interpretation**: Connect statistical findings to biological and evolutionary processes
5. **Robust Recommendations**: When some analyses are missing, focus on the available data and acknowledge limitations

INPUT DATA ANALYSIS:
- PCA Analysis: Population structure, genetic distances, clustering patterns (if available)
- TreeMix Analysis: Phylogenetic relationships, migration events, gene flow patterns (if available)
- Admixture Analysis: Ancestral components, admixture levels, population stratification (if available)
- Single Population Analysis: Effective population sizes, demographic history, expansion/contraction events (if available)
- Other Analyses: Additional population genetics insights (LD decay, heterozygosity, etc.) (if available)

HANDLING MISSING DATA:
- If some analyses are missing, clearly state which analyses are unavailable
- Focus on the available data and provide the best possible recommendations
- Acknowledge limitations due to missing analyses
- Suggest alternative approaches when possible

OUTPUT REQUIREMENTS:
Provide a comprehensive modeling report in the following structure:

## 1. EXECUTIVE SUMMARY
- Brief overview of key findings from all analyses
- Main demographic patterns identified
- Recommended modeling approach

## 2. DATA CHARACTERIZATION
- Population structure assessment
- Genetic diversity patterns
- Migration and admixture evidence
- Demographic history insights

## 3. DEMOGRAPHIC MODEL RECOMMENDATIONS
- Proposed demographic model architecture
- Key demographic events to include
- Population relationships and migration patterns
- Temporal framework recommendations

## 4. FASTSIMCOAL2 PARAMETER RECOMMENDATIONS
- Population size parameters (Ne ranges)
- Migration rate parameters
- Divergence time parameters
- Growth/contraction parameters
- Mutation and recombination rates

## 5. MODELING STRATEGY
- Inference vs simulation approach
- Parameter estimation methodology
- Model comparison strategy
- Validation approaches

## 6. BIOLOGICAL INTERPRETATION
- Evolutionary significance of findings
- Historical context and implications
- Population-specific characteristics
- Migration and gene flow patterns

## 7. TECHNICAL RECOMMENDATIONS
- FastSimCoal2 execution parameters
- Computational requirements
- Quality control measures
- Expected analysis duration

Provide scientifically rigorous, evidence-based recommendations that integrate all available analysis results into a coherent demographic modeling framework.
Please ensure that the content is as concise as possible and avoid redundant information.
Return the complete modeling report as structured text.
"""

# Example configuration
MODELING_EXAMPLES = [
    {
        "input": {
            "goal": "Analyze YRI, CEU, CHB populations for demographic modeling",
            "pca_report": "PCA shows clear separation between African (YRI) and non-African (CEU, CHB) populations with PC1 explaining 36% variance...",
            "treemix_report": "TreeMix analysis reveals migration events between populations with YRI as outgroup...",
            "admixture_report": "Admixture analysis shows K=3 optimal with distinct ancestral components...",
            "single_pop_report": "Single population analysis indicates YRI has largest Ne (~50,000), CEU shows bottleneck signature...",
            "other_analysis_report": "LD decay analysis shows different patterns across populations..."
        },
        "output": {
            "modeling_recommendations": "## EXECUTIVE SUMMARY\nBased on comprehensive analysis, the data shows clear African vs non-African population structure with evidence of out-of-Africa bottleneck and subsequent population expansions...\n\n## DEMOGRAPHIC MODEL RECOMMENDATIONS\nPropose a three-population model with:\n- Ancestral African population (YRI-like)\n- Out-of-Africa bottleneck population\n- European (CEU) and East Asian (CHB) populations\n\n## FASTSIMCOAL2 PARAMETER RECOMMENDATIONS\n- YRI Ne: 40,000-60,000\n- CEU Ne: 8,000-15,000 (post-bottleneck)\n- CHB Ne: 10,000-20,000 (post-bottleneck)\n- Divergence time: 50,000-80,000 years ago\n- Migration rates: 1e-5 to 1e-4 per generation\n\n## BIOLOGICAL INTERPRETATION\nThe analysis supports the out-of-Africa model with subsequent population expansions in Europe and East Asia..."
        }
    }
]

# =========================
#       LLM construction
# =========================
def create_modeling_agent(api_key: str, base_url: str, model: str):
    """Create modeling analysis Agent"""
    print(f"[DEBUG] Creating Modeling Agent with model: {model}")
    
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
        examples=MODELING_EXAMPLES
    )
    
    parser = StrOutputParser()
    
    final_prompt = ChatPromptTemplate.from_messages([
        ("system", MODELING_PROMPT),
        few_shot_prompt,
        ("human", "{input}")
    ])
    
    agent = final_prompt | llm | parser
    print(f"[DEBUG] Modeling Agent created successfully")
    return agent

# =========================
#        LangGraph nodes
# =========================
def collect_reports_node(state: ModelingAgentState) -> ModelingAgentState:
    """Collect all analysis reports, supporting missing reports"""
    print("[INFO] Collecting analysis reports...")
    
    ana_dir = state["ana_dir"]
    reports = {}
    
    # Define report file paths (support multiple possible filenames)
    report_files = {
        "pca_report": [
            os.path.join(ana_dir, "pca_analysis_report.txt"),
            os.path.join(ana_dir, "pca_report.txt")
        ],
        "treemix_report": [
            os.path.join(ana_dir, "treemix_analysis_report.txt"),
            os.path.join(ana_dir, "treemix_report.txt")
        ],
        "admixture_report": [
            os.path.join(ana_dir, "admixture_analysis_report.txt"),
            os.path.join(ana_dir, "admixture_report.txt")
        ],
        "other_analysis_report": [
            os.path.join(ana_dir, "other_analysis_report.txt"),
            os.path.join(ana_dir, "other_analysis_analysis_report.txt")  # Backward compatibility
        ],
        "single_pop_report": [
            os.path.join(ana_dir, "single_pop_report.txt")
        ]
    }
    
    # Read all reports, try multiple possible file paths
    for report_type, possible_paths in report_files.items():
        content = None
        used_path = None
        
        for file_path in possible_paths:
            if os.path.exists(file_path):
                content = read_file_content(file_path)
                if content:
                    used_path = file_path
                    break
        
        if content:
            reports[report_type] = content
            print(f"[INFO] Loaded {report_type} from {used_path}: {len(content)} characters")
        else:
            print(f"[WARNING] No content found for {report_type} (tried: {possible_paths})")
            reports[report_type] = f"No {report_type} available - analysis may have failed or not been completed"
    
    # Count available reports
    available_reports = [k for k, v in reports.items() if not v.startswith("No ")]
    missing_reports = [k for k, v in reports.items() if v.startswith("No ")]
    
    print(f"[INFO] Available reports: {len(available_reports)} ({', '.join(available_reports)})")
    if missing_reports:
        print(f"[WARNING] Missing reports: {len(missing_reports)} ({', '.join(missing_reports)})")
        print("[INFO] Will proceed with available reports only")
    
    # Update state
    for key, value in reports.items():
        state[key] = value
    
    return state

def generate_modeling_recommendations_node(state: ModelingAgentState, modeling_agent) -> ModelingAgentState:
    """Generate modeling recommendations and parameter suggestions, supporting missing reports"""
    print("[INFO] Generating modeling recommendations...")
    
    # Build input data, distinguish available and missing reports
    available_reports = {}
    missing_reports = []
    
    report_types = ["pca_report", "treemix_report", "admixture_report", "other_analysis_report", "single_pop_report"]
    
    for report_type in report_types:
        report_content = state.get(report_type, "")
        if report_content and not report_content.startswith("No "):
            available_reports[report_type] = report_content
        else:
            missing_reports.append(report_type)
    
    # Build input data
    input_data = {
        "goal": state["goal"],
        "available_reports": available_reports,
        "missing_reports": missing_reports,
        "total_reports_expected": len(report_types),
        "reports_available": len(available_reports)
    }
    
    # Add available report content
    for report_type, content in available_reports.items():
        input_data[report_type] = content
    
    # Add placeholder for missing reports
    for report_type in missing_reports:
        input_data[report_type] = f"No {report_type} available - analysis may have failed or not been completed"
    
    print(f"[AGENT INPUT] Modeling analysis input:")
    print(f"[AGENT INPUT] Goal: {input_data['goal']}")
    print(f"[AGENT INPUT] Available reports: {len(available_reports)}/{len(report_types)}")
    print(f"[AGENT INPUT] Available: {list(available_reports.keys())}")
    if missing_reports:
        print(f"[AGENT INPUT] Missing: {missing_reports}")
    
    try:
        # Call LLM to generate modeling recommendations
        response = modeling_agent.invoke({"input": json.dumps(input_data)})
        
        print(f"[AGENT OUTPUT] Raw response:")
        print(f"[AGENT OUTPUT] {response[:500]}...")
        
        # Save modeling recommendations
        state["modeling_recommendations"] = response
        
        print(f"[INFO] Generated modeling recommendations ({len(response)} characters)")
        
    except Exception as e:
        error_msg = f"Failed to generate modeling recommendations: {e}"
        print(f"[ERROR] {error_msg}")
        state["modeling_recommendations"] = error_msg
    
    return state

def save_modeling_report_node(state: ModelingAgentState) -> ModelingAgentState:
    """Save modeling report"""
    print("[INFO] Saving modeling report...")
    
    ana_dir = state["ana_dir"]
    output_id = state["output_id"]
    
    # Generate full modeling report
    report_content = state.get("modeling_recommendations", "No modeling recommendations available")
    
    # Add report header
    header = f"""# FastSimCoal Demographic Modeling Recommendations
**Analysis ID**: {output_id}
**Goal**: {state['goal']}
**Generated**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

"""
    
    full_report = header + report_content
    
    # Save report
    report_path = os.path.join(ana_dir, "modeling_report1.txt")
    write_text(report_path, full_report)
    
    print(f"[INFO] Modeling report saved to: {report_path}")
    report_path = os.path.join(ana_dir, "modeling_report.txt")
    # Update state
    state["ok"] = True
    state["analysis"] = "Modeling recommendations generated successfully"
    state["outputs"] = {
        "modeling_report": report_path,
        "report_content": full_report
    }
    
    return state

# =========================
#       Graph construction and execution
# =========================
def build_modeling_graph(modeling_agent):
    """Build modeling analysis graph"""
    g = StateGraph(ModelingAgentState)
    
    # Add nodes
    g.add_node("collect_reports", collect_reports_node)
    g.add_node("generate_recommendations", lambda state: generate_modeling_recommendations_node(state, modeling_agent))
    g.add_node("save_report", save_modeling_report_node)
    
    # Set edges
    g.set_entry_point("collect_reports")
    g.add_edge("collect_reports", "generate_recommendations")
    g.add_edge("generate_recommendations", "save_report")
    g.add_edge("save_report", END)
    
    return g.compile()

# =========================
#       Public interface
# =========================
def run_modeling_agent(goal: str, output_id: str, ana_dir: str,
                      api_key: str, base_url: str, 
                      model: str = "claude-opus-4-1-20250805") -> Dict[str, Any]:
    """
    Run modeling analysis Agent
    
    Args:
        goal: Analysis goal
        output_id: Output ID
        ana_dir: Analysis directory
        api_key: API key
        base_url: API base URL
        model: Model name
    
    Returns:
        Analysis result dictionary
    """
    
    # Create modeling Agent
    modeling_agent = create_modeling_agent(api_key, base_url, model)
    
    # Build graph
    graph = build_modeling_graph(modeling_agent)
    
    # Initialize state
    init_state: ModelingAgentState = {
        "goal": goal,
        "output_id": output_id,
        "ana_dir": ana_dir,
        "pca_report": None,
        "treemix_report": None,
        "admixture_report": None,
        "other_analysis_report": None,
        "single_pop_report": None,
        "modeling_recommendations": None,
        "fastsimcoal_parameters": None,
        "ok": False,
        "analysis": "",
        "outputs": {}
    }
    
    # Run graph
    final_state = graph.invoke(init_state)
    
    return {
        "success": final_state.get("ok", False),
        "analysis": final_state.get("analysis", ""),
        "outputs": final_state.get("outputs", {}),
        "modeling_recommendations": final_state.get("modeling_recommendations", "")
    }

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from config_loader import get_llm_config
    cfg = get_llm_config()

    print("Testing ModelingAgent...")
    result = run_modeling_agent(
        goal="I have data about YRI, CEU, CHB populations. Based on the available data, conduct an inference of a migration and separation model for three populations.",
        output_id="test_modeling",
        ana_dir="./output/test_integrated_001/ana",
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        model=cfg.get("default_model", "claude-opus-4-1-20250805"),
    )
    print("ModelingAgent Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
