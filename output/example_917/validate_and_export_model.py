import demes
import yaml

# Load and validate the demographic model
print("Loading and validating demographic model...")
try:
    graph = demes.load("./output/917/ooa_model.yaml")
    print("Model loaded and validated successfully!")
except Exception as e:
    print(f"Validation error: {e}")
    raise

# Export validated model to YAML
print("\nExporting validated model...")
demes.dump(graph, "./output/917/ooa_model_validated.yaml")
print("Validated model saved to: ./output/917/ooa_model_validated.yaml")

# Create summary of demographic events and parameters
print("\nGenerating model summary...")
with open("./output/917/model_summary.txt", "w") as f:
    f.write("=" * 70 + "\n")
    f.write("DEMOGRAPHIC MODEL SUMMARY\n")
    f.write("=" * 70 + "\n\n")
    
    # Model description
    f.write("MODEL DESCRIPTION:\n")
    f.write("-" * 40 + "\n")
    if graph.description:
        f.write(f"{graph.description}\n")
    else:
        f.write("No description provided\n")
    f.write(f"Time units: {graph.time_units}\n")
    if graph.generation_time:
        f.write(f"Generation time: {graph.generation_time} years\n")
    f.write("\n")
    
    # Demes (populations)
    f.write("DEMES (POPULATIONS):\n")
    f.write("-" * 40 + "\n")
    f.write(f"Total number of demes: {len(graph.demes)}\n\n")
    
    for deme in graph.demes:
        f.write(f"  Deme: {deme.name}\n")
        if deme.description:
            f.write(f"    Description: {deme.description}\n")
        if deme.ancestors:
            f.write(f"    Ancestors: {', '.join(deme.ancestors)}\n")
        f.write(f"    Start time: {deme.start_time}\n")
        f.write(f"    End time: {deme.end_time}\n")
        f.write(f"    Number of epochs: {len(deme.epochs)}\n")
        
        for i, epoch in enumerate(deme.epochs):
            f.write(f"      Epoch {i+1}:\n")
            f.write(f"        Time interval: {epoch.start_time} -> {epoch.end_time}\n")
            f.write(f"        Start size: {epoch.start_size}\n")
            f.write(f"        End size: {epoch.end_size}\n")
            f.write(f"        Size function: {epoch.size_function}\n")
        f.write("\n")
    
    # Migrations
    f.write("MIGRATIONS (CONTINUOUS GENE FLOW):\n")
    f.write("-" * 40 + "\n")
    if graph.migrations:
        f.write(f"Total number of migration events: {len(graph.migrations)}\n\n")
        for i, mig in enumerate(graph.migrations):
            f.write(f"  Migration {i+1}:\n")
            f.write(f"    Source: {mig.source}\n")
            f.write(f"    Dest: {mig.dest}\n")
            f.write(f"    Rate: {mig.rate}\n")
            f.write(f"    Start time: {mig.start_time}\n")
            f.write(f"    End time: {mig.end_time}\n")
            f.write("\n")
    else:
        f.write("No continuous migrations defined\n\n")
    
    # Pulses (admixture events)
    f.write("PULSES (ADMIXTURE EVENTS):\n")
    f.write("-" * 40 + "\n")
    if graph.pulses:
        f.write(f"Total number of pulse events: {len(graph.pulses)}\n\n")
        for i, pulse in enumerate(graph.pulses):
            f.write(f"  Pulse {i+1}:\n")
            f.write(f"    Sources: {pulse.sources}\n")
            f.write(f"    Dest: {pulse.dest}\n")
            f.write(f"    Proportions: {pulse.proportions}\n")
            f.write(f"    Time: {pulse.time}\n")
            f.write("\n")
    else:
        f.write("No pulse (admixture) events defined\n\n")
    
    # Summary statistics
    f.write("SUMMARY STATISTICS:\n")
    f.write("-" * 40 + "\n")
    f.write(f"Number of demes: {len(graph.demes)}\n")
    f.write(f"Number of migrations: {len(graph.migrations)}\n")
    f.write(f"Number of pulses: {len(graph.pulses)}\n")
    
    # List leaf demes (present-day populations)
    leaf_demes = [d.name for d in graph.demes if d.end_time == 0]
    f.write(f"Leaf demes (present-day): {', '.join(leaf_demes)}\n")
    
    f.write("\n" + "=" * 70 + "\n")
    f.write("Validation: PASSED\n")
    f.write("=" * 70 + "\n")

print("Model summary saved to: ./output/917/model_summary.txt")

# Print summary to console
print("\n" + "=" * 50)
print("MODEL VALIDATION SUMMARY")
print("=" * 50)
print(f"Number of demes: {len(graph.demes)}")
print(f"Number of migrations: {len(graph.migrations)}")
print(f"Number of pulses: {len(graph.pulses)}")
print(f"Time units: {graph.time_units}")
print(f"Deme names: {[d.name for d in graph.demes]}")
print("\nValidation: PASSED")
