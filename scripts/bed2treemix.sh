#!/bin/bash
set -euo pipefail

PREFIX=$1

# Extract population labels from fam file if clust file doesn't exist
if [ ! -f ${PREFIX}.clust ]; then
    awk '{print $1, $2, $1}' ${PREFIX}.fam > ${PREFIX}.clust
fi

# Convert PLINK to stratified frequencies
plink --bfile ${PREFIX} --freq --within ${PREFIX}.clust --out ${PREFIX}

# Convert to TreeMix input format
python3 -c "
import gzip
import sys

freq_file = '${PREFIX}.frq.strat'
out_file = '${PREFIX}.treemix.frq.gz'

# Read frequency data
freq_data = {}
with open(freq_file, 'r') as f:
    next(f)  # Skip header
    for line in f:
        parts = line.strip().split()
        if len(parts) >= 8:
            snp = parts[1]
            pop = parts[2]
            mac = int(parts[6])
            nchr = int(parts[7])
            
            if snp not in freq_data:
                freq_data[snp] = {}
            freq_data[snp][pop] = (mac, nchr)

# Get populations and SNPs in order
pops = sorted(set(pop for snp_data in freq_data.values() for pop in snp_data))
snps = sorted(freq_data.keys())

# Write TreeMix format
with gzip.open(out_file, 'wt') as out:
    # Header
    out.write(' '.join(pops) + '\n')
    
    # Data
    for snp in snps:
        row = []
        for pop in pops:
            if pop in freq_data[snp]:
                mac, nchr = freq_data[snp][pop]
                row.append(f'{mac},{nchr}')
            else:
                row.append('0,0')
        out.write(' '.join(row) + '\n')
"

echo "Conversion complete: ${PREFIX}.treemix.frq.gz"
