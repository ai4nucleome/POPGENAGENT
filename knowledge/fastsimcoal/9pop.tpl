// -------- simulation.tpl  (10 demes) --------
10 samples to simulate :

// ① Effective population sizes (Ne)
NPOP_JPT
NPOP_IBS
NPOP_CHB
NPOP_ACB
NPOP_GBR
NPOP_CHS
NPOP_CEU
NPOP_STU
NPOP_MSL
NPOP_CHS       // Replace with new variable if independent needed

// ② Sample sizes  (haploid genomes)
50
50
50
50
50
50
50
50
50
50

// ③ Sample ages
0
0
0
0
0
0
0
0
0
0

// ④ Growth rates
0
0
0
0
0
0
0
0
0
0

// ----- migration matrices -----
1
0      0.0001 0.0001 0      0      0.0001 0.0001 0      0      0
0.0001 0      0      0      0.0001 0      0      0.0001 0      0
0.0001 0      0      0      0      0.0001 0.0001 0      0      0
0      0      0      0      0      0      0      0      0      0.0001
0      0.0001 0      0      0      0      0      0.0001 0      0
0.0001 0      0.0001 0      0      0      0.0001 0      0      0
0.0001 0      0.0001 0      0      0.0001 0      0      0      0
0      0.0001 0      0      0.0001 0      0      0      0      0
0      0      0      0      0      0      0      0      0      0
0      0      0      0.0001 0      0      0      0      0      0

// ----- historical events -----
10 historical events
TDIV01  0 2 0.1 -1 0 -1
TDIV02  5 2 0.1 -1 0 -1
TDIV03  1 4 0.1 -1 0 -1
TDIV04  4 6 0.1 -1 0 -1
TDIV05  3 8 0.1 -1 0 -1
TDIV06  0 5 1   -1 0 -1
TDIV07  5 5 1   -1 0 -1
TDIV08  1 6 1   -1 0 -1
TDIV09  4 6 1   -1 0 -1
TDIV10  3 8 1   -1 0 -1

// ----- loci -----
1 0
1
FREQ 100 1e-8 2.5e-8 OUTEXP
