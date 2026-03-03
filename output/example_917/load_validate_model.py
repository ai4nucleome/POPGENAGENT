import demes
import yaml
import sys

# Load the demographic model from YAML file
print("Loading demographic model from ./output/917/ooa_model.yaml...")
try:
    graph = demes.load("./output/917/ooa_model.yaml")
    print("Model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {e}")
    sys.exit(1)

# Validate the model (demes.load already validates, but we can check properties)
print("\nValidating demographic model...")
try:
    # Check that the graph is fully resolved
    assert graph.time_units is not None, "Time units not specified"
    assert len(graph.demes) > 0, "No demes defined in the model"
    print(f"  - Time units: {graph.time_units}")
    print(f"  - Number of demes: {len(graph.demes)}")
    print(f"  - Number of migrations: {len(graph.migrations)}")
    print(f"  - Number of pulses: {len(graph.pulses)}")
    print("Model validation passed!")
except AssertionError as e:
    print(f"Validation failed: {e}")
    sys.exit(1)

# Export validated model to YAML
print("\nExporting validated model to ./output/917/ooa_model_validated.yaml...")
demes.dump(graph, "./output/917/ooa_model_validated.yaml")
print("Validated model exported successfully!")

# Create summary of demographic events and parameters
print("\nGenerating model summary...")
with open("./output/917/model_summary.txt", "w") as f:
    f.write("=" * 70 + "\n")
    f.write("DEMOGRAPHIC MODEL SUMMARY\n")
    f.write("=" * 70 + "\n\n")
    
    # Basic information
    f.write("BASIC INFORMATION\n")
    f.write("-" * 40 + "\n")
    if graph.description:
        f.write(f"Description: {graph.description}\n")
    f.write(f"Time units: {graph.time_units}\n")
    if graph.generation_time:
        f.write(f"Generation time: {graph.generation_time} years\n")
    f.write(f"Number of demes: {len(graph.demes)}\n")
    f.write(f"Number of migrations: {len(graph.migrations)}\n")
    f.write(f"Number of pulses: {len(graph.pulses)}\n\n")
    
    # Deme information
    f.write("DEMES (POPULATIONS)\n")
    f.write("-" * 40 + "\n")
    for deme in graph.demes:
        f.write(f"\nDeme: {deme.name}\n")
        if deme.description:
            f.write(f"  Description: {deme.description}\n")
        if deme.ancestors:
            f.write(f"  Ancestors: {', '.join(deme.ancestors)}\n")
        f.write(f"  Start time: {deme.start_time}\n")
        f.write(f"  End time: {deme.end_time}\n")
        f.write(f"  Number of epochs: {len(deme.epochs)}\n")
        for i, epoch in enumerate(deme.epochs):
            f.write(f"    Epoch {i+1}:\n")
            f.write(f"      Time interval: {epoch.start_time} -> {epoch.end_time}\n")
            f.write(f"      Start size: {epoch.start_size}\n")
            f.write(f"      End size: {epoch.end_size}\n")
            f.write(f"      Size function: {epoch.size_function}\n")
    
    # Migration information
    if graph.migrations:
        f.write("\nMIGRATIONS (CONTINUOUS GENE FLOW)\n")
        f.write("-" * 40 + "\n")
        for i, mig in enumerate(graph.migrations):
            f.write(f"\nMigration {i+1}:\n")
            f.write(f"  Source: {mig.source}\n")
            f.write(f"  Dest: {mig.dest}\n")
            f.write(f"  Rate: {mig.rate}\n")
            f.write(f"  Start time: {mig.start_time}\n")
            f.write(f"  End time: {mig.end_time}\n")
    
    # Pulse information
    if graph.pulses:
        f.write("\nPULSES (INSTANTANEOUS ADMIXTURE)\n")
        f.write("-" * 40 + "\n")
        for i, pulse in enumerate(graph.pulses):
            f.write(f"\nPulse {i+1}:\n")
            f.write(f"  Sources: {pulse.sources}\n")
            f.write(f"  Dest: {pulse.dest}\n")
            f.write(f"  Proportions: {pulse.proportions}\n")
            f.write(f"  Time: {pulse.time}\n")
    
    f.write("\n" + "=" * 70 + "\n")
    f.write("END OF SUMMARY\n")
    f.write("=" * 70 + "\n")

print("Model summary saved to ./output/917/model_summary.txt")
print("\nAnalysis complete!")
