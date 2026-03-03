//Parameters for the coalescence simulation program : fastsimcoal.exe 
12 samples to simulate : 
//Population effective sizes (number of genes) 
1000 
1000 
1000 
1000 
1000 
1000 
1000 
1000 
1000 
1000 
20000000 
20000000 
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
0 
0 
//Growth rates : negative growth implies population expansion 
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
0 
0 
//Number of migration matrices : 0 implies no migration between demes 
3 
//Migration matrix 0 
0 0 0 0 0 0 0 0 0 0 M010 0 
0 0 0 0 0 0 0 0 0 0 M110 0 
0 0 0 0 0 0 0 0 0 0 M210 0 
0 0 0 0 0 0 0 0 0 0 M310 0 
0 0 0 0 0 0 0 0 0 0 M410 0 
0 0 0 0 0 0 0 0 0 0 0 M511 
0 0 0 0 0 0 0 0 0 0 0 M611 
0 0 0 0 0 0 0 0 0 0 0 M711 
0 0 0 0 0 0 0 0 0 0 0 M811 
0 0 0 0 0 0 0 0 0 0 0 M911 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
//Migration matrix 1 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 M511 
0 0 0 0 0 0 0 0 0 0 0 M611 
0 0 0 0 0 0 0 0 0 0 0 M711 
0 0 0 0 0 0 0 0 0 0 0 M811 
0 0 0 0 0 0 0 0 0 0 0 M911 
0 0 0 0 0 0 0 0 0 0 0 M1211 
0 0 0 0 0 0 0 0 0 0 0 0 
//Migration matrix 2 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
0 0 0 0 0 0 0 0 0 0 0 0 
//historical event: time, source, sink, migrants, new deme size, new growth rate, migration matrix index 
13 historical event 
TISLAND1 0 10 1 1 0 1 
TISLAND1 1 10 1 1 0 1 
TISLAND1 2 10 1 1 0 1 
TISLAND1 3 10 1 1 0 1 
TISLAND1 4 10 1 1 0 1 
TISLAND1 10 10 0 0.0001 0 1 
TISLAND2 5 11 1 1 0 2 
TISLAND2 6 11 1 1 0 2 
TISLAND2 7 11 1 1 0 2 
TISLAND2 8 11 1 1 0 2 
TISLAND2 9 11 1 1 0 2 
TISLAND2 10 11 1 1 0 2 
TISLAND2 11 11 0 RESIZE 0 2//Number of independent loci [chromosome]  
1 0 
//Per chromosome: Number of contiguous linkage Block: a block is a set of contiguous loci 
1 
//per Block:data type, number of loci, per gen recomb and mut rates 
FREQ 1 0 2.5e-8