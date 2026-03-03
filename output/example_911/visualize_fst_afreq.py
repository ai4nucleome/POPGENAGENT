import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import numpy as np
import os
from matplotlib.lines import Line2D

# ============================================================================
# CONFIGURATION
# ============================================================================
FST_SUMMARY_FILE = './output/911/fst_hudson.fst.summary'
AFREQ_STRAT_FILE = './output/911/pop_freq.afreq.strat'
POP_CLUSTERS_FILE = './output/911/pop_clusters.txt'
OUTPUT_DIR = './output/911/'

continental_groups = {
    'African': ['ACB', 'ASW', 'ESN', 'GWD', 'LWK', 'MSL', 'YRI'],
    'European': ['CEU', 'FIN', 'GBR', 'IBS', 'TSI'],
    'East Asian': ['CDX', 'CHB', 'CHS', 'JPT', 'KHV'],
    'South Asian': ['BEB', 'GIH', 'ITU', 'PJL', 'STU'],
    'American': ['CLM', 'MXL', 'PEL', 'PUR']
}

continent_colors = {
    'African': '#27ae60', 'European': '#2980b9',
    'East Asian': '#c0392b', 'South Asian': '#8e44ad', 'American': '#d35400'
}

matplotlib.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
TITLE_SIZE, LABEL_SIZE, TICK_SIZE, LEGEND_SIZE = 18, 14, 12, 12
DPI = 300

def get_continent(pop):
    for continent, pops in continental_groups.items():
        if pop in pops:
            return continent
    return 'Unknown'

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================================
# FST HEATMAP
# ============================================================================
print('Generating FST heatmap...')

try:
    fst_df = pd.read_csv(FST_SUMMARY_FILE, sep='\\s+', engine='python')
    print(f'FST summary columns: {list(fst_df.columns)}')
    
    # Get unique populations
    if 'POP1' in fst_df.columns and 'POP2' in fst_df.columns:
        pop1_col, pop2_col = 'POP1', 'POP2'
    elif '#POP1' in fst_df.columns:
        pop1_col, pop2_col = '#POP1', 'POP2'
    else:
        # Try to find population columns
        cols = fst_df.columns.tolist()
        pop1_col, pop2_col = cols[0], cols[1]
    
    # Find FST column
    fst_col = None
    for col in ['FST', 'HUDSON_FST', 'MEAN_FST', 'WC_FST', 'fst']:
        if col in fst_df.columns:
            fst_col = col
            break
    if fst_col is None:
        # Use last numeric column
        for col in reversed(fst_df.columns):
            if fst_df[col].dtype in ['float64', 'float32', 'int64']:
                fst_col = col
                break
    
    print(f'Using columns: {pop1_col}, {pop2_col}, {fst_col}')
    
    populations = sorted(list(set(fst_df[pop1_col].tolist() + fst_df[pop2_col].tolist())))
    n_pops = len(populations)
    print(f'Found {n_pops} populations')
    
    # Create FST matrix
    fst_matrix = pd.DataFrame(np.zeros((n_pops, n_pops)), index=populations, columns=populations)
    
    for _, row in fst_df.iterrows():
        p1, p2 = row[pop1_col], row[pop2_col]
        fst_val = row[fst_col]
        if pd.notna(fst_val):
            fst_matrix.loc[p1, p2] = fst_val
            fst_matrix.loc[p2, p1] = fst_val
    
    # Sort populations by continent
    sorted_pops = []
    for continent in ['African', 'European', 'East Asian', 'South Asian', 'American']:
        for pop in populations:
            if pop in continental_groups.get(continent, []):
                sorted_pops.append(pop)
    # Add any remaining populations
    for pop in populations:
        if pop not in sorted_pops:
            sorted_pops.append(pop)
    
    fst_matrix = fst_matrix.loc[sorted_pops, sorted_pops]
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(14, 12))
    
    mask = np.triu(np.ones_like(fst_matrix, dtype=bool), k=1)
    
    sns.heatmap(fst_matrix, mask=mask, annot=True, fmt='.3f', cmap='YlOrRd',
                square=True, linewidths=0.5, ax=ax,
                annot_kws={'size': 8}, cbar_kws={'label': 'FST', 'shrink': 0.8},
                vmin=0, vmax=fst_matrix.values.max())
    
    # Color tick labels by continent
    for i, label in enumerate(ax.get_yticklabels()):
        pop = label.get_text()
        continent = get_continent(pop)
        label.set_color(continent_colors.get(continent, 'black'))
        label.set_fontweight('bold')
    
    for i, label in enumerate(ax.get_xticklabels()):
        pop = label.get_text()
        continent = get_continent(pop)
        label.set_color(continent_colors.get(continent, 'black'))
        label.set_fontweight('bold')
    
    ax.set_title("Pairwise FST Between Populations (Hudson's Estimator)", 
                 fontsize=TITLE_SIZE, fontweight='bold', pad=20)
    
    # Add legend for continents
    legend_elements = [Line2D([0], [0], marker='s', color='w', 
                              markerfacecolor=c, markersize=12, label=n, markeredgecolor='black') 
                       for n, c in continent_colors.items()]
    ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.25, 1),
              fontsize=LEGEND_SIZE, title='Continental Group', framealpha=0.95)
    
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}fst_heatmap.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()
    print('  Saved: fst_heatmap.png')
    
except Exception as e:
    print(f'Error creating FST heatmap: {e}')
    # Create placeholder
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.text(0.5, 0.5, f'FST data not available\n{str(e)}', ha='center', va='center', fontsize=14)
    ax.set_title('Pairwise FST Heatmap', fontsize=TITLE_SIZE, fontweight='bold')
    plt.savefig(f'{OUTPUT_DIR}fst_heatmap.png', dpi=DPI, bbox_inches='tight')
    plt.close()

# ============================================================================
# ALLELE FREQUENCY DISTRIBUTION
# ============================================================================
print('Generating allele frequency distribution plots...')

try:
    afreq_df = pd.read_csv(AFREQ_STRAT_FILE, sep='\\s+', engine='python')
    print(f'Allele frequency columns: {list(afreq_df.columns)}')
    
    # Find relevant columns
    pop_col = None
    for col in ['POP', 'CLST', 'CLUSTER', 'Population']:
        if col in afreq_df.columns:
            pop_col = col
            break
    if pop_col is None:
        pop_col = afreq_df.columns[0]
    
    freq_col = None
    for col in ['ALT_FREQS', 'MAF', 'FREQ', 'AF', 'A1_FREQ', 'FRQ']:
        if col in afreq_df.columns:
            freq_col = col
            break
    if freq_col is None:
        # Find first numeric column after population
        for col in afreq_df.columns:
            if afreq_df[col].dtype in ['float64', 'float32']:
                freq_col = col
                break
    
    print(f'Using columns: {pop_col}, {freq_col}')
    
    populations = sorted(afreq_df[pop_col].unique())
    n_pops = len(populations)
    print(f'Found {n_pops} populations in allele frequency data')
    
    # Create figure with multiple subplots
    fig, axes = plt.subplots(2, 1, figsize=(14, 12))
    
    # Plot 1: Violin plot of allele frequencies by population
    ax1 = axes[0]
    
    # Sort populations by continent
    sorted_pops = []
    for continent in ['African', 'European', 'East Asian', 'South Asian', 'American']:
        for pop in populations:
            if pop in continental_groups.get(continent, []):
                sorted_pops.append(pop)
    for pop in populations:
        if pop not in sorted_pops:
            sorted_pops.append(pop)
    
    # Prepare data for violin plot
    plot_data = []
    plot_labels = []
    plot_colors = []
    
    for pop in sorted_pops:
        pop_data = afreq_df[afreq_df[pop_col] == pop][freq_col].dropna()
        if len(pop_data) > 0:
            plot_data.append(pop_data.values)
            plot_labels.append(pop)
            plot_colors.append(continent_colors.get(get_continent(pop), '#95a5a6'))
    
    if plot_data:
        parts = ax1.violinplot(plot_data, positions=range(len(plot_data)), showmeans=True, showmedians=True)
        
        for i, pc in enumerate(parts['bodies']):
            pc.set_facecolor(plot_colors[i])
            pc.set_alpha(0.7)
            pc.set_edgecolor('black')
        
        parts['cmeans'].set_color('red')
        parts['cmedians'].set_color('black')
        
        ax1.set_xticks(range(len(plot_labels)))
        ax1.set_xticklabels(plot_labels, rotation=45, ha='right', fontsize=TICK_SIZE)
        
        # Color x-tick labels
        for i, label in enumerate(ax1.get_xticklabels()):
            pop = label.get_text()
            label.set_color(continent_colors.get(get_continent(pop), 'black'))
            label.set_fontweight('bold')
    
    ax1.set_xlabel('Population', fontsize=LABEL_SIZE, fontweight='bold')
    ax1.set_ylabel('Allele Frequency', fontsize=LABEL_SIZE, fontweight='bold')
    ax1.set_title('Allele Frequency Distribution by Population', fontsize=TITLE_SIZE, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.set_ylim(0, 1)
    
    # Plot 2: Histogram overlay by continent
    ax2 = axes[1]
    
    for continent, color in continent_colors.items():
        continent_pops = continental_groups.get(continent, [])
        continent_data = afreq_df[afreq_df[pop_col].isin(continent_pops)][freq_col].dropna()
        if len(continent_data) > 0:
            ax2.hist(continent_data, bins=50, alpha=0.5, label=continent, color=color, density=True)
    
    ax2.set_xlabel('Allele Frequency', fontsize=LABEL_SIZE, fontweight='bold')
    ax2.set_ylabel('Density', fontsize=LABEL_SIZE, fontweight='bold')
    ax2.set_title('Allele Frequency Distribution by Continental Group', fontsize=TITLE_SIZE, fontweight='bold')
    ax2.legend(fontsize=LEGEND_SIZE, title='Continental Group')
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, 1)
    
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}allele_freq_dist.png', dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()
    print('  Saved: allele_freq_dist.png')
    
except Exception as e:
    print(f'Error creating allele frequency plot: {e}')
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.text(0.5, 0.5, f'Allele frequency data not available\n{str(e)}', ha='center', va='center', fontsize=14)
    ax.set_title('Allele Frequency Distribution', fontsize=TITLE_SIZE, fontweight='bold')
    plt.savefig(f'{OUTPUT_DIR}allele_freq_dist.png', dpi=DPI, bbox_inches='tight')
    plt.close()

print('Visualization complete!')
