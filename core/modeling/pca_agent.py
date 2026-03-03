#!/usr/bin/env python3
"""
PCAAgent - Principal Component Analysis Agent

Enhanced with LangGraph framework, image collection, composite generation, and multimodal analysis.
Follows the obs_agent.py and single_pop_agent.py design patterns.

Main features:
1. Collect PCA-related images from ./output/{id}/ana/ directory
2. Stitch multiple images into a composite image
3. Analyze composite image using multimodal model
4. Generate academic-level analysis report
5. Avoid re-stitching existing composite images
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from base_image_agent import (
    BaseImageAgentState, 
    run_image_analysis_agent
)
import json
from typing import Dict, Any

# =========================
#        Public interface
# =========================
def run_pca_agent(goal: str = "", output_id: str = "001", 
                  api_key: str = "", base_url: str = "", 
                  model: str = "gpt-4-vision-preview",
                  max_retries: int = 2) -> Dict[str, Any]:
    """
    Run PCAAgent for image collection, stitching and multimodal analysis
    
    Returns:
        Dict containing analysis results and outputs
    """
    if not goal:
        goal = "Principal Component Analysis for population structure and genetic diversity assessment"
    
    # Use base class generic run function directly
    return run_image_analysis_agent(
        analysis_type="pca",
        goal=goal,
        output_id=output_id,
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_retries=max_retries
    )

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from config_loader import get_llm_config
    cfg = get_llm_config()

    print("Testing Enhanced PCAAgent...")
    result = run_pca_agent(
        goal="Analyze population structure and genetic diversity in YRI, CEU, CHB populations using PCA",
        output_id="061",
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        model="gpt-4-vision-preview",
    )
    print("Enhanced PCAAgent Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))