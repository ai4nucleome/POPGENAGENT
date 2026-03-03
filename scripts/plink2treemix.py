#!/usr/bin/env python3
"""
Convert a gzipped PLINK --freq --within output (.frq.strat.gz)
to the allele-count format required by TreeMix.

Columns expected in .frq.strat:
CHR  SNP  POP  ...  MAC  NCHROBS
Treemix output:
first line  – space-separated population names
subsequent – comma-separated allele1,allele2 counts per population
"""

import gzip
import sys
from collections import defaultdict

# ----------------------- CLI ----------------------- #
if len(sys.argv) != 3:
    sys.exit("Usage: plink2treemix.py [gzipped .frq.strat] [gzipped output]")

in_path, out_path = sys.argv[1], sys.argv[2]

# ------------------ parse input -------------------- #
pop2rs = defaultdict(dict)   # {pop: {rs: (minor_cnt, total_cnt)} }
order_rs, seen_rs = [], set()

with gzip.open(in_path, "rt") as fh:
    fh.readline()            # skip header
    fh.readline()            # skip blank line inserted by PLINK
    for ln in fh:
        cols = ln.rstrip().split()
        if len(cols) < 8:        # safety check
            continue
        rs   = cols[1]
        pop  = cols[2]
        mac  = int(cols[6])      # minor-allele count
        tots = int(cols[7])      # total called chromosomes

        if rs not in seen_rs:    # keep original SNP order
            order_rs.append(rs)
            seen_rs.add(rs)

        pop2rs[pop][rs] = (mac, tots)

pops = list(pop2rs.keys())   # TreeMix does not require sorting, keep read order

# -------------- write TreeMix file ---------------- #
with gzip.open(out_path, "wt") as out:
    out.write(" ".join(pops) + "\n")

    for rs in order_rs:
        row = []
        for pop in pops:
            mac, tots = pop2rs[pop].get(rs, (0, 0))
            maj = tots - mac
            row.append(f"{mac},{maj}")
        out.write(" ".join(row) + "\n")
