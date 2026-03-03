import demes
import demesdraw
import matplotlib.pyplot as plt

# Load the validated demographic model
graph = demes.load('./output/917/ooa_model_validated.yaml')

# 1. Generate tube plot showing population sizes over time
fig, ax = plt.subplots(figsize=(12, 8))
demesdraw.tubes(graph, ax=ax, log_time=True)
ax.set_title('Out-of-Africa Demographic Model - Tube Plot', fontsize=14, fontweight='bold')
ax.set_xlabel('Time (generations, log scale)', fontsize=12)
ax.set_ylabel('Population', fontsize=12)
plt.tight_layout()
fig.savefig('./output/917/ooa_tube_plot.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: ooa_tube_plot.png')

# 2. Generate population size history plot
fig, ax = plt.subplots(figsize=(12, 8))
demesdraw.size_history(graph, ax=ax, log_time=True, log_size=True)
ax.set_title('Population Size History', fontsize=14, fontweight='bold')
ax.set_xlabel('Time (generations, log scale)', fontsize=12)
ax.set_ylabel('Population Size (log scale)', fontsize=12)
ax.legend(loc='best', frameon=True)
ax.grid(True, alpha=0.3)
plt.tight_layout()
fig.savefig('./output/917/ooa_size_history.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: ooa_size_history.png')

# 3. Generate migration/pulse diagram
# Check if there are migrations or pulses in the model
has_migrations = len(graph.migrations) > 0 if hasattr(graph, 'migrations') else False
has_pulses = len(graph.pulses) > 0 if hasattr(graph, 'pulses') else False

fig, ax = plt.subplots(figsize=(14, 10))

# Use tubes plot with migration arrows highlighted
demesdraw.tubes(
    graph,
    ax=ax,
    log_time=True,
    fill=True,
    labels='xticks',
    seed=42
)

# Add title with migration info
mig_info = []
if has_migrations:
    mig_info.append(f'{len(graph.migrations)} continuous migration(s)')
if has_pulses:
    mig_info.append(f'{len(graph.pulses)} pulse event(s)')

title = 'Demographic Model with Gene Flow'
if mig_info:
    title += f"\n({', '.join(mig_info)})"
else:
    title += '\n(No migration events)'

ax.set_title(title, fontsize=14, fontweight='bold')
ax.set_xlabel('Time (generations, log scale)', fontsize=12)
plt.tight_layout()
fig.savefig('./output/917/ooa_migration_plot.png', dpi=300, bbox_inches='tight')
plt.close()
print('Saved: ooa_migration_plot.png')

# Print model summary
print('\n=== Model Summary ===')
print(f'Description: {graph.description}')
print(f'Time units: {graph.time_units}')
print(f'Number of demes: {len(graph.demes)}')
print(f'Deme names: {[d.name for d in graph.demes]}')
if has_migrations:
    print(f'Number of migrations: {len(graph.migrations)}')
if has_pulses:
    print(f'Number of pulses: {len(graph.pulses)}')
print('\nVisualization complete!')
