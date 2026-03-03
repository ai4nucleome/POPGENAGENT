//Parameters for the coalescence simulation program : fsimcoal2.exe
10 samples to simulate :
//Population effective sizes (number of genes)
NPOP_JPT
NPOP_IBS
NPOP_CHB
NPOP_ACB
NPOP_GBR
NPOP_CHS
NPOP_CEU
NPOP_STU
NPOP_MSL
NPOP_CHB  

//Samples sizes and samples age
20
20
20
20
20
20
20
20
20
20

//Growth rates: negative growth implies population expansion
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

//Number of migration matrices: 0 implies no migration between demes
1

//Migration matrix 0
0 0.0001 0.0001 0 0 0.0001 0.0001 0 0 0
0.0001 0 0 0 0.0001 0 0 0.0001 0 0
0.0001 0 0 0 0 0.0001 0.0001 0 0 0
0 0 0 0 0 0 0 0 0 0.0001
0 0.0001 0 0 0 0 0 0.0001 0 0
0.0001 0 0.0001 0 0 0 0.0001 0 0 0
0.0001 0 0.0001 0 0 0.0001 0 0 0 0
0 0.0001 0 0 0.0001 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0
0 0 0 0.0001 0 0 0 0 0 0

//Historical event: time, source, sink, migrants, new deme size, new growth rate, migration matrix index
9 historical events
1000 0 1 1 0 0 0
1500 2 5 1 0 0 0
2000 1 4 1 0 0 0
2500 4 7 1 0 0 0
3000 8 9 1 0 0 0
3500 0 2 1 0 0 0
4000 3 9 1 0 0 0
5000 0 7 1 0 0 0
6000 0 3 1 0 0 0

//Number of independent loci [chromosome]
1 0

//Per chromosome: Number of contiguous linkage Block: a block is a set of contiguous loci
100

//per Block:data type, number of loci, per generation recombination and mutation rates and optional parameters
FREQ 1 1e-8 2.5e-8 OUTEXP
