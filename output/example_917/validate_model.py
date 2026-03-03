import demes

# Load and validate the YAML model
graph = demes.load("./output/917/ooa_model.yaml")

# Print model summary
print("Out-of-Africa Model Summary")
print("="*50)
print(f"Description: {graph.description}")
print(f"Time units: {graph.time_units}")
print(f"Number of demes: {len(graph.demes)}")
print("\nDemes:")
for deme in graph.demes:
    print(f"  - {deme.name}: {deme.description}")
    for epoch in deme.epochs:
        print(f"      start_size: {epoch.start_size}, end_size: {epoch.end_size}, end_time: {epoch.end_time}")
print(f"\nNumber of migrations: {len(graph.migrations)}")
print("Migrations:")
for mig in graph.migrations:
    print(f"  - {mig.source} <-> {mig.dest}: rate={mig.rate}, start_time={mig.start_time}, end_time={mig.end_time}")
print("\nModel validation: PASSED")
