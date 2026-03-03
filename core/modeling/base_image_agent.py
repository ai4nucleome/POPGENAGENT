#!/usr/bin/env python3
"""
BaseImageAgent - Base class for image analysis Agents

Provides common functionality for all image analysis Agents:
1. Image collection and filtering
2. Image stitching and composite image generation
3. Multimodal LLM analysis
4. Report generation

Specialized Agents (PCA, TreeMix, Admixture, OtherAnalysis) inherit from this base class
"""

import os
import json
import glob
import subprocess
from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, END
from PIL import Image
import base64

# LLM
from langchain_openai import ChatOpenAI

# =========================
#         Base state definition
# =========================
class BaseImageAgentState(TypedDict, total=False):
    goal: str
    id: str
    max_retries: int
    analysis_type: str  # 'pca', 'treemix', 'admixture', 'other'
    
    # LLM related
    api_key: str
    base_url: str
    model: str
    
    # Image processing related
    composite_image: str
    source_images: List[str]
    analysis_text: str
    
    # Run intermediate results
    ok: bool
    analysis: str
    outputs: Dict[str, str]

# =========================
#       Common utility functions
# =========================
def write_text(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def file_nonempty(p: str) -> bool:
    return os.path.exists(p) and os.path.getsize(p) > 0

def collect_images_by_type(ana_dir: str, analysis_type: str) -> List[str]:
    """Collect related image files by analysis type"""
    image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.pdf']
    images = []
    
    if analysis_type == 'other':
        # For 'other' type, collect all images excluding specific keywords
        exclude_keywords = ['pca', 'treemix', 'admixture']
        
        for ext in image_extensions:
            pattern = os.path.join(ana_dir, "**", f"*{ext}")
            for img_path in glob.glob(pattern, recursive=True):
                basename = os.path.basename(img_path).lower()
                # Exclude composite files and files with specific keywords
                if ('composite' not in basename and 
                    not any(keyword in basename for keyword in exclude_keywords)):
                    images.append(img_path)
    else:
        # For other types, use keyword matching
        keywords = {
            'pca': ['pca'],
            'treemix': ['treemix'],
            'admixture': ['admixture']
        }
        
        search_keywords = keywords.get(analysis_type, [analysis_type])
        
        for ext in image_extensions:
            for keyword in search_keywords:
                # Find image files containing keyword, exclude composite files
                pattern = os.path.join(ana_dir, "**", f"*{keyword}*{ext}")
                for img_path in glob.glob(pattern, recursive=True):
                    # Exclude images that are already composite
                    if 'composite' not in os.path.basename(img_path).lower():
                        images.append(img_path)
    
    return sorted(list(set(images)))  # Deduplicate and sort

def convert_pdf_to_png(pdf_path: str) -> str:
    """Convert PDF to PNG"""
    png_path = pdf_path.replace('.pdf', '_converted.png')
    try:
        # Use ImageMagick for conversion
        subprocess.run(['convert', '-density', '300', pdf_path, png_path], 
                      check=True, capture_output=True)
        return png_path
    except subprocess.CalledProcessError:
        try:
            # Use pdftoppm as fallback
            subprocess.run(['pdftoppm', '-png', '-singlefile', pdf_path, 
                          png_path.replace('.png', '')], check=True, capture_output=True)
            return png_path
        except subprocess.CalledProcessError:
            print(f"[WARNING] Could not convert PDF to PNG: {pdf_path}")
            return None

def create_composite_image(image_paths: List[str], output_path: str) -> bool:
    """Create composite image"""
    if not image_paths:
        return False
    
    try:
        # Convert all PDFs to PNG
        png_paths = []
        for img_path in image_paths:
            if img_path.lower().endswith('.pdf'):
                converted = convert_pdf_to_png(img_path)
                if converted:
                    png_paths.append(converted)
            else:
                png_paths.append(img_path)
        
        if not png_paths:
            return False
        
        # Load all images
        images = []
        for img_path in png_paths:
            try:
                img = Image.open(img_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                images.append(img)
            except Exception as e:
                print(f"[WARNING] Could not load image {img_path}: {e}")
        
        if not images:
            return False
        
        # Compute stitching layout
        num_images = len(images)
        if num_images == 1:
            images[0].save(output_path)
            return True
        
        # Compute grid layout
        cols = 2 if num_images <= 4 else 3
        rows = (num_images + cols - 1) // cols
        
        # Compute standard size for each image
        max_width = max(img.width for img in images)
        max_height = max(img.height for img in images)
        
        # Create composite image
        composite_width = cols * max_width
        composite_height = rows * max_height
        composite = Image.new('RGB', (composite_width, composite_height), 'white')
        
            # Paste each image
        for i, img in enumerate(images):
            row = i // cols
            col = i % cols
            
            # Resize image preserving aspect ratio
            img_ratio = img.width / img.height
            target_ratio = max_width / max_height
            
            if img_ratio > target_ratio:
                new_width = max_width
                new_height = int(max_width / img_ratio)
            else:
                new_height = max_height
                new_width = int(max_height * img_ratio)
            
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Compute paste position (centered)
            x = col * max_width + (max_width - new_width) // 2
            y = row * max_height + (max_height - new_height) // 2
            
            composite.paste(img_resized, (x, y))
        
        composite.save(output_path, 'PNG', quality=95)
        
        # Clean up temporarily converted PNG files
        for img_path in png_paths:
            if img_path.endswith('_converted.png') and img_path not in image_paths:
                try:
                    os.remove(img_path)
                except:
                    pass
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to create composite image: {e}")
        return False

def encode_image_to_base64(image_path: str) -> str:
    """Encode image to base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def create_multimodal_llm(api_key: str, base_url: str, model: str = "gpt-4-vision-preview"):
    """Create vision-capable LLM"""
    return ChatOpenAI(
        model=model,
        base_url=base_url,
        openai_api_key=api_key,
        temperature=0.1,
        max_tokens=2000
    )

# =========================
#        LangGraph base node functions
# =========================
def collect_images_node(state: BaseImageAgentState) -> BaseImageAgentState:
    """Collect related images"""
    output_id = state.get("id", "001")
    analysis_type = state.get("analysis_type", "pca")
    ana_dir = os.path.join(".", "output", output_id, "ana")
    
    print(f"[INFO] Collecting {analysis_type} images from {ana_dir}")
    
    # Collect related images
    images = collect_images_by_type(ana_dir, analysis_type)
    
    if not images:
        print(f"[WARNING] No {analysis_type} images found in {ana_dir}")
        state["ok"] = False
        state["analysis"] = f"No {analysis_type} images found for analysis"
        return state
    
    print(f"[INFO] Found {len(images)} {analysis_type} images: {[os.path.basename(p) for p in images]}")
    
    # Create composite image
    composite_path = os.path.join(ana_dir, f"{analysis_type}_composite.png")
    
    # Check if composite image already exists
    if file_nonempty(composite_path):
        print(f"[INFO] {analysis_type} composite image already exists: {composite_path}")
        state["composite_image"] = composite_path
        state["source_images"] = images
        return state
    
    # Create new composite image
    if create_composite_image(images, composite_path):
        print(f"[INFO] Created {analysis_type} composite image: {composite_path}")
        state["composite_image"] = composite_path
        state["source_images"] = images
    else:
        print(f"[ERROR] Failed to create {analysis_type} composite image")
        state["ok"] = False
        state["analysis"] = f"Failed to create {analysis_type} composite image"
    
    return state

def analyze_images_node(state: BaseImageAgentState) -> BaseImageAgentState:
    """Analyze composite image using multimodal model"""
    composite_image = state.get("composite_image")
    analysis_type = state.get("analysis_type", "pca")
    
    if not composite_image or not file_nonempty(composite_image):
        state["ok"] = False
        state["analysis"] = "No valid composite image for analysis"
        return state
    
    api_key = state.get("api_key", "")
    base_url = state.get("base_url", "")
    goal = state.get("goal", "")
    
    if not api_key or not base_url:
        state["ok"] = False
        state["analysis"] = "Missing API credentials for multimodal analysis"
        return state
    
    print(f"[INFO] Analyzing {analysis_type} composite image with multimodal LLM")
    
    try:
        # Create multimodal LLM
        llm = create_multimodal_llm(api_key, base_url)
        
        # Encode image
        image_base64 = encode_image_to_base64(composite_image)
        
        # Build specialized prompt by analysis type
        analysis_prompts = {
            'pca': get_pca_analysis_prompt(goal),
            'treemix': get_treemix_analysis_prompt(goal),
            'admixture': get_admixture_analysis_prompt(goal),
            'other': get_other_analysis_prompt(goal)
        }
        
        analysis_prompt = analysis_prompts.get(analysis_type, analysis_prompts['other'])
        
        # Create message
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": analysis_prompt},
                    {
                        "type": "image_url", 
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]
        
        # Call LLM for analysis
        response = llm.invoke(messages)
        analysis_text = response.content if hasattr(response, 'content') else str(response)
        
        state["analysis_text"] = analysis_text
        print(f"[INFO] Completed multimodal analysis")
        
    except Exception as e:
        print(f"[ERROR] Multimodal analysis failed: {e}")
        state["analysis_text"] = f"Multimodal analysis failed: {str(e)}"
    
    return state

def generate_report_node(state: BaseImageAgentState) -> BaseImageAgentState:
    """Generate analysis report"""
    output_id = state.get("id", "001")
    analysis_type = state.get("analysis_type", "pca")
    ana_dir = os.path.join(".", "output", output_id, "ana")
    
    analysis_text = state.get("analysis_text", "")
    composite_image = state.get("composite_image", "")
    source_images = state.get("source_images", [])
    
    if not analysis_text:
        state["ok"] = False
        state["analysis"] = "No analysis text generated"
        return state
    
    # Generate report content
    from datetime import datetime
    
    analysis_names = {
        'pca': 'PCA (Principal Component Analysis)',
        'treemix': 'TreeMix Phylogenetic Analysis',
        'admixture': 'ADMIXTURE Ancestry Analysis',
        'other': 'Additional Population Genetics Analyses'
    }
    
    report_content = f"""{analysis_names.get(analysis_type, analysis_type.upper())} Report
Project ID: {output_id}
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ANALYSIS OVERVIEW:
{analysis_text}

TECHNICAL DETAILS:
- Analysis method: {analysis_names.get(analysis_type, analysis_type.upper())}
- Input images analyzed: {len(source_images)}
- Composite image: {os.path.basename(composite_image) if composite_image else 'Not created'}
- Source images: {', '.join([os.path.basename(p) for p in source_images])}

FILES GENERATED:
- Composite image: {composite_image}
- Analysis report: {ana_dir}/{analysis_type}_analysis_report.txt
"""
    
    # Save report
    report_path = os.path.join(ana_dir, f"{analysis_type}_analysis_report.txt")
    write_text(report_path, report_content)
    
    print(f"[INFO] {analysis_type} analysis report saved to: {report_path}")
    
    state["ok"] = True
    state["analysis"] = f"{analysis_type} analysis completed successfully with multimodal insights and composite image generation"
    state["outputs"] = {
        "composite_image": composite_image,
        "analysis_report": report_path,
        "analysis_text": analysis_text
    }
    
    return state

# =========================
#        Analysis prompt templates
# =========================
def get_pca_analysis_prompt(goal: str) -> str:
    return f"""You are a senior bioinformatics and population genetics expert. Analyze the provided PCA (Principal Component Analysis) composite image and provide detailed scientific insights.

Research Goal: {goal}

Please provide a comprehensive analysis covering:

1. **PCA Plot Interpretation**:
   - Population structure and clustering patterns
   - Principal component contributions to variance
   - Evidence of population stratification or admixture
   - Separation patterns between populations

2. **Population Genetics Insights**:
   - Evolutionary relationships between populations
   - Migration patterns suggested by PC plots
   - Demographic history implications
   - Genetic distance and differentiation

3. **Technical Assessment**:
   - Quality of the PCA analysis
   - Sample distribution and outliers
   - Variance explained by components
   - Recommendations for further analysis

4. **Modeling Implications**:
   - Suggestions for demographic modeling approaches
   - Relevant population parameters to consider
   - Migration models that might fit the data
   - Additional analyses that would be beneficial

Please maintain academic rigor and provide specific, actionable insights for population genetic modeling.

Respond in English with scientific precision."""

def get_treemix_analysis_prompt(goal: str) -> str:
    return f"""You are a senior bioinformatics and population genetics expert. Analyze the provided TreeMix composite image and provide detailed scientific insights.

Research Goal: {goal}

Please provide a comprehensive analysis covering:

1. **Phylogenetic Tree Interpretation**:
   - Population relationships and branching patterns
   - Migration edges and their biological significance
   - Tree topology and confidence measures
   - Rooting and outgroup relationships

2. **Migration Pattern Analysis**:
   - Inferred migration events and their directions
   - Timing and intensity of gene flow
   - Population splits and divergence events
   - Admixture proportions and sources

3. **Population History Insights**:
   - Demographic events revealed by the tree
   - Isolation and contact patterns
   - Evolutionary timescales and bottlenecks
   - Geographic and temporal context

4. **Model Selection and Quality**:
   - Likelihood comparison across different migration numbers
   - Optimal number of migration edges
   - Model fit and residual analysis
   - Statistical confidence and limitations

5. **Implications for Demographic Modeling**:
   - Suggested demographic scenarios
   - Parameter estimates for population sizes
   - Migration rates and timing constraints
   - Additional data or analyses needed

Please maintain academic rigor and provide specific, actionable insights for population genetic modeling.

Respond in English with scientific precision."""

def get_admixture_analysis_prompt(goal: str) -> str:
    return f"""You are a senior bioinformatics and population genetics expert. Analyze the provided ADMIXTURE composite image and provide detailed scientific insights.

Research Goal: {goal}

Please provide a comprehensive analysis covering:

1. **Ancestry Composition Analysis**:
   - Individual ancestry proportions and patterns
   - Population-level ancestry structure
   - Admixture gradients and clines
   - Cross-validation results and optimal K

2. **Population Structure Insights**:
   - Genetic clustering and stratification
   - Evidence of population mixing
   - Source populations and admixture events
   - Geographic ancestry patterns

3. **Historical Demographics**:
   - Migration and contact events
   - Population bottlenecks and expansions
   - Isolation by distance patterns
   - Recent vs ancient admixture

4. **Technical Quality Assessment**:
   - Model convergence and stability
   - Cross-validation error patterns
   - Ancestry coefficient reliability
   - Sample representation quality

5. **Modeling Applications**:
   - Admixture proportions for demographic models
   - Source population parameters
   - Migration timing and rates
   - Multi-way admixture scenarios

Please maintain academic rigor and provide specific, actionable insights for population genetic modeling.

Respond in English with scientific precision."""

def get_other_analysis_prompt(goal: str) -> str:
    return f"""You are a senior bioinformatics and population genetics expert. Analyze the provided population genetics composite image and provide detailed scientific insights.

Research Goal: {goal}

Please provide a comprehensive analysis covering:

1. **Diversity and Structure Patterns**:
   - Genetic diversity measures and distributions
   - Linkage disequilibrium decay patterns
   - Population differentiation (FST patterns)
   - Heterozygosity and inbreeding coefficients

2. **Demographic Signatures**:
   - Evidence of population bottlenecks
   - Selection signatures and outliers
   - Runs of homozygosity patterns
   - Effective population size estimates

3. **Evolutionary Insights**:
   - Population history and demography
   - Migration and isolation patterns
   - Adaptive evolution signatures
   - Neutral vs selected variation

4. **Technical Assessment**:
   - Analysis quality and coverage
   - Statistical significance of patterns
   - Methodological considerations
   - Data limitations and biases

5. **Integration with Other Analyses**:
   - Complementary information to PCA/TreeMix/ADMIXTURE
   - Parameter constraints for demographic modeling
   - Additional analyses recommended
   - Data quality indicators

Please maintain academic rigor and provide specific, actionable insights for population genetic modeling.

Respond in English with scientific precision."""

# =========================
#        Common graph construction function
# =========================
def build_image_analysis_graph():
    """Build generic image analysis LangGraph"""
    g = StateGraph(BaseImageAgentState)
    g.add_node("collect", collect_images_node)
    g.add_node("analyze", analyze_images_node) 
    g.add_node("report", generate_report_node)
    
    g.set_entry_point("collect")
    g.add_edge("collect", "analyze")
    g.add_edge("analyze", "report")
    g.add_edge("report", END)
    
    return g.compile()

# =========================
#        Common run function
# =========================
def run_image_analysis_agent(analysis_type: str, goal: str = "", output_id: str = "001", 
                             api_key: str = "", base_url: str = "", 
                             model: str = "gpt-4-vision-preview",
                             max_retries: int = 2) -> Dict[str, Any]:
    """
    Run image analysis Agent for image collection, stitching and multimodal analysis
    
    Args:
        analysis_type: Analysis type ('pca', 'treemix', 'admixture', 'other')
        goal: Analysis goal
        output_id: Output ID
        api_key: API key
        base_url: API base URL
        model: Model name
        max_retries: Max retry count
    
    Returns:
        Dict containing analysis results and outputs
    """
    if not goal:
        default_goals = {
            'pca': 'Principal Component Analysis for population structure and genetic diversity assessment',
            'treemix': 'TreeMix phylogenetic analysis for population relationships and migration inference',
            'admixture': 'ADMIXTURE ancestry analysis for population structure and admixture patterns',
            'other': 'Additional population genetics analyses for demographic insights'
        }
        goal = default_goals.get(analysis_type, f"{analysis_type} analysis for population genetics insights")
    
    graph = build_image_analysis_graph()
    
    init_state: BaseImageAgentState = {
        "goal": goal,
        "id": output_id,
        "analysis_type": analysis_type,
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
        "composite_image": final_state.get("composite_image", ""),
        "analysis_text": final_state.get("analysis_text", "")
    }
