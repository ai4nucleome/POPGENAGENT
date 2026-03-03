//Parameters for the coalescence simulation program : fsimcoal2.exe
3 samples to simulate :
//Population effective sizes (number of genes)
NPOP1
NPOP2
NPOP3
//Samples sizes and samples age 
20
20
20
//Growth rates: negative growth implies population expansion
0
0
0
//Number of migration matrices: 0 implies no migration between demes
1
//Migration matrix 0
0 MIG12 MIG13
MIG21 0 MIG23
MIG31 MIG32 0
//Historical event: time, source, sink, migrants, new deme size, new growth rate, migration matrix index
3 historical events
TDIV1 1 0 1 ANC0 0 0
TDIV2 2 0 1 INTERMEDIATE 0 0
TDIV3 2 1 1 ANC12 0 0
//Number of independent loci [chromosome]
1 0
//Per chromosome: Number of contiguous linkage Block: a block is a set of contiguous loci
1
//per Block:data type, number of loci, per generation recombination and mutation rates and optional parameters
DNA 1 0 2.5e-8
