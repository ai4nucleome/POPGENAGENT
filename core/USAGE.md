# Population Genetics Analysis Framework - LangGraph Integration

## Overview

The population genetics analysis framework has been refactored to integrate LangGraph workflow while maintaining backward compatibility. The main interface `interpret_plan` remains unchanged for seamless backend integration.

## Key Features

- **Chain-of-thought analysis**: Step-by-step analysis using specialized agents
- **Intelligent routing**: Automatic detection of available analysis images and dynamic planning
- **Specialized analysis**: Dedicated agents for PCA, TreeMix, Admixture, and LD analysis
- **Integrated modeling**: FastSimCoal and Demes modeling with parameter estimation
- **Backward compatibility**: Existing `interpret_plan` interface preserved
- **Fallback mechanism**: Automatic fallback to legacy method if LangGraph fails

## File Structure

```
agents/
├── AnaAgent.py          # Main analysis agent (streamlined, delegates to modelingagent)
├── modelingagent.py     # Comprehensive modeling, image analysis, and demes agents
├── prompts.py           # Analysis prompts and examples
└── USAGE.md            # This documentation
```

## Usage

### Basic Usage (Interface Unchanged)

```python
from agents.AnaAgent import AnaAgent

# Initialize the agent
ana_agent = AnaAgent(api_key, base_url, model)

# Use the same interface as before
result = ana_agent.interpret_plan(
    goal="Analyze population genetic structure and evolutionary history",
    datalist=["sample1.vcf", "sample2.vcf", "observed.obs"],
    id="015"
)
```

### Dependencies

The framework requires these additional packages:
- `langgraph>=0.2.0`
- `langchain>=0.3.0`
- `langchain-openai>=0.2.0`

## Analysis Workflow

1. **Decision Node**: Scans `./output/{id}/ana/` for available images
2. **Image Analysis**: Specialized analysis for each detected image type
3. **Modeling**: FastSimCoal configuration generation and execution
4. **Demes Modeling**: Demographic model generation and visualization
5. **Integration**: Comprehensive report generation

## Image Detection

The system automatically detects analysis images based on filename patterns:
- PCA: `pca.png`, `PCA.png`, `principal_component.png`
- TreeMix: `treemix.png`, `TreeMix.png`, `tree_mix.png`
- Admixture: `admixture.png`, `Admixture.png`, `structure.png`
- LD: `ld.png`, `LD.png`, `linkage.png`

## Error Handling

- **Graceful degradation**: If LangGraph fails, automatically falls back to legacy method
- **Individual node failures**: Single node failures don't affect the entire workflow
- **Comprehensive logging**: Detailed logs for debugging and monitoring

## Compatibility

- **Interface preservation**: `interpret_plan` method signature unchanged
- **Return type consistency**: Same return format as original implementation
- **Backend integration**: No changes required for existing backend systems

## Configuration

The framework uses the same configuration as the original AnaAgent:
- API keys and base URLs
- Model specifications
- Vector store configurations
- Knowledge base paths

## Key Improvements

- **Modular Design**: Complex prompts and agent logic moved to `modelingagent.py`
- **Clean Main File**: `AnaAgent.py` streamlined by delegating specialized functionality
- **Full Prompt Preservation**: All original prompt functionality maintained in modelingagent
- **Simple Instantiation**: Main file only handles initialization and delegation

This ensures seamless integration with existing systems while providing enhanced analysis capabilities through a cleaner, more maintainable codebase.
