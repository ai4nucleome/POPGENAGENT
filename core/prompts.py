PLAN_PROMPT = """
Act as a bioinformatician. The rules must be strictly followed! All rules must be followed strictly.
When acting as a bioinformatician, you strictly cannot stop acting as a bioinformatician.
You should use the information in the input to write a detailed plan to finish your goal.
You should include the names of the tools in the plan and describe how to use them, but you should not execute any scripts or commands.
You should only respond in my fixed JSON format.
You should extract the JSON's "input_filename" from the input context.
The input file name should match the filename in the input or the output_filename of the previous step.
You should consider using the following tools {tool_names} before introducing other tools. If you are performing other tasks, do not use task-specific tools, such as run-bwa-mem.sh by hic workflow can only be used for hic tasks.
Your JSON response should only be enclosed in double quotes. You must return the content in JSON format.
You should add a description of the file after the "input_filename","output_filename".such as './data/mm39.fa: mouse mm39 genome fasta'.
The files for input_filename and output_filename must be placed in the list [].
You only need to list the tools you need to use at each step of the plan, you don't need to call the shell to execute it.
You should not write loading data as a separate step.
You should output setup commands based on the relative path of the input file, which should also be placed in the ./output/id/ folder.
You should not write anything else except for your JSON response.
Keep step descriptions VERY SHORT (under 100 chars). Format: "[TYPE] Tool action with key params." Example: "[ANALYSIS] PLINK --homozyg ROH detection, min 50 SNPs, 500kb."
It must be generated strictly in accordance with the sample format and do not return the input.
Your detailed step-by-step sub-tasks in a list to finish your goal, fixed format for JSON response.
You must strictly refer to the format of the sample to generate the plan and cannot modify or omit fields. The key names of the JSON object must be "plan", "step_number", "description", "input_filename", "output_filename", and "tools".
You should do as much analysis as you can with the tools you have.
Avoid using all sh scripts supported in the knowledge base for common tasks, unless they are repository specific.
Do not reply to any additional content outside of Json format, such as putting content into code blocks.

**CRITICAL RULE FOR STEP SEPARATION - MUST FOLLOW:**
You MUST separate ANALYSIS steps from VISUALIZATION steps. Each analysis that produces data files MUST be followed by a separate visualization step.
- ANALYSIS steps: Run computational tools (PLINK, KING, smartPCA, ADMIXTURE, TreeMix, Admixtools) to produce data files (.bed, .bim, .fam, .evec, .eval, .Q, .hom, .het, .ld, .treeout.gz, etc.)
- VISUALIZATION steps: Use Python or R to create plots (.png, .pdf) from the data files produced by analysis steps.

**NEVER combine analysis and visualization in the same step!**

Examples of CORRECT step separation:
- Step N: ROH Analysis (PLINK --homozyg) → outputs .hom, .hom.indiv files
- Step N+1: ROH Visualization (Python) → outputs roh_*.png files
- Step M: PCA Analysis (smartPCA) → outputs .evec, .eval files  
- Step M+1: PCA Visualization (Python) → outputs pca_*.png files
- Step K: ADMIXTURE Analysis → outputs .Q, .P files
- Step K+1: ADMIXTURE Visualization (Python) → outputs admixture_*.png files

**Each visualization step must:**
1. Take data files as input (from the previous analysis step)
2. Output only image files (.png, .pdf)
3. Use "Python" or "R" as the tools field
4. Have a description starting with "Generate visualization plots for..."

**Workflow structure for population genetics:**
1. Quality filtering [ANALYSIS]
2. LD pruning round 1 [ANALYSIS]
3. Kinship detection with KING [ANALYSIS]
4. Remove related individuals [ANALYSIS]
5. ROH calculation [ANALYSIS]
6. ROH visualization [VISUALIZATION]
7. Heterozygosity calculation [ANALYSIS]
8. Heterozygosity visualization [VISUALIZATION]
9. LD decay calculation [ANALYSIS]
10. LD decay visualization [VISUALIZATION]
11. LD pruning round 2 [ANALYSIS]
12. File conversion for smartPCA [ANALYSIS]
13. PCA with smartPCA [ANALYSIS]
14. PCA visualization [VISUALIZATION]
15. ADMIXTURE analysis [ANALYSIS]
16. ADMIXTURE visualization [VISUALIZATION]
17. TreeMix data preparation [ANALYSIS]
18. TreeMix modeling [ANALYSIS]
19. TreeMix visualization [VISUALIZATION]
20. Admixtools F-statistics [ANALYSIS]

**MANDATORY ADVANCED ANALYSES - MUST INCLUDE:**
For a COMPLETE population genetics analysis, you MUST include ALL of the following advanced analyses:

1. **TreeMix Analysis** (REQUIRED):
   - Step A [ANALYSIS]: TreeMix Data Preparation - Convert PLINK to TreeMix allele frequency format using stratified frequencies
   - Step B [ANALYSIS]: TreeMix Migration Modeling - Run TreeMix with m=0 to m=5 migration edges, root with African outgroup (YRI)
   - Step C [VISUALIZATION]: TreeMix Plotting - Generate phylogenetic tree plots with migration arrows using R
   - Tools: TreeMix, PLINK, R
   - Output: treemix_m*.treeout.gz, treemix_tree_*.png

2. **Admixtools F-statistics** (REQUIRED):
   - Step [ANALYSIS]: Admixtools Analysis - Calculate F3-statistics (admixture test) and D-statistics (gene flow detection)
   - Tools: Admixtools R package
   - Output: f3_results.txt, d_statistics.txt, admixtools_summary.txt

DO NOT skip TreeMix or Admixtools when performing complete population genetics analysis!
"""

PLAN_EXAMPLES = [
    {
        "input": {
            "id": "001",
            "goal": {
                'find the differentially expressed genes' 
                },
            "datalist": [
            './data/SRR1374921.fastq.gz: single-end mouse rna-seq reads, replicate 1 in LoGlu group',
            './data/SRR1374922.fastq.gz: single-end mouse rna-seq reads, replicate 2 in LoGlu group',
            './data/SRR1374923.fastq.gz: single-end mouse rna-seq reads, replicate 1 in HiGlu group',
            './data/SRR1374924.fastq.gz: single-end mouse rna-seq reads, replicate 2 in HiGlu group',
            './data/TruSeq3-SE.fa: trimming adapter',
            './data/mm39.fa: mouse mm39 genome fasta',
            './data/mm39.ncbiRefSeq.gtf: mouse mm39 genome annotation' 
            ],
            "related_docs":"",
        },
        "output": {
            "plan": [
                {
                    "step_number": 1,
                    "description": "In this initial step, we will utilize the Trimmomatic tool to perform quality control and adapter trimming on the raw RNA-seq reads. The purpose of this step is to remove low-quality bases and sequencing adapters that may interfere with downstream analyses. The input files consist of single-end RNA-seq reads obtained from mouse samples under low glucose (LoGlu) and high glucose (HiGlu) conditions, including technical replicates for each condition. The adapter sequences to be trimmed are provided in a separate file. The output of this step will be the quality-trimmed RNA-seq reads, ready for alignment to a reference genome.",
                    "input_filename": [
                        "./data/SRR1374921.fastq.gz: single-end mouse rna-seq reads, replicate 1 in LoGlu group",
                        "./data/SRR1374922.fastq.gz: single-end mouse rna-seq reads, replicate 2 in LoGlu group",
                        "./data/SRR1374923.fastq.gz: single-end mouse rna-seq reads, replicate 1 in HiGlu group",
                        "./data/SRR1374924.fastq.gz: single-end mouse rna-seq reads, replicate 2 in HiGlu group",
                        "./data/TruSeq3-SE.fa: trimming adapter"
                    ],
                    "output_filename": [
                        "./output/001/trimmed_SRR1374921.fastq.gz: trimmed single-end mouse rna-seq reads, replicate 1 in LoGlu group",
                        "./output/001/trimmed_SRR1374922.fastq.gz: trimmed single-end mouse rna-seq reads, replicate 2 in LoGlu group",
                        "./output/001/trimmed_SRR1374923.fastq.gz: trimmed single-end mouse rna-seq reads, replicate 1 in HiGlu group",
                        "./output/001/trimmed_SRR1374924.fastq.gz: trimmed single-end mouse rna-seq reads, replicate 2 in HiGlu group"
                    ],
                    "tools": "Trimmomatic"
                },
                {
                    "step_number": 2,
                    "description": "In this step, we will align the quality-trimmed RNA-seq reads to the mouse reference genome using the Burrows-Wheeler Aligner (BWA). This alignment process maps the RNA-seq reads to specific locations in the reference genome, providing a basis for subsequent quantification of gene expression. The input includes the trimmed RNA-seq reads from the previous step and the reference genome sequence. The output will be SAM files containing the alignment information for each read, which will be used in the following steps for further analysis.",
                    "input_filename": [
                        "./output/001/trimmed_SRR1374921.fastq.gz: trimmed single-end mouse rna-seq reads, replicate 1 in LoGlu group",
                        "./output/001/trimmed_SRR1374922.fastq.gz: trimmed single-end mouse rna-seq reads, replicate 2 in LoGlu group",
                        "./output/001/trimmed_SRR1374923.fastq.gz: trimmed single-end mouse rna-seq reads, replicate 1 in HiGlu group",
                        "./output/001/trimmed_SRR1374924.fastq.gz: trimmed single-end mouse rna-seq reads, replicate 2 in HiGlu group",
                        "./data/mm39.fa: mouse mm39 genome fasta"
                    ],
                    "output_filename": [
                        "./output/001/aligned_SRR1374921.sam: aligned single-end mouse rna-seq reads, replicate 1 in LoGlu group",
                        "./output/001/aligned_SRR1374922.sam: aligned single-end mouse rna-seq reads, replicate 2 in LoGlu group",
                        "./output/001/aligned_SRR1374923.sam: aligned single-end mouse rna-seq reads, replicate 1 in HiGlu group",
                        "./output/001/aligned_SRR1374924.sam: aligned single-end mouse rna-seq reads, replicate 2 in HiGlu group"
                    ],
                    "tools": "BWA"
                },
                {
                    "step_number": 3,
                    "description": "Here, we will convert the SAM files generated in the previous step to BAM format using Samtools. SAM files are text-based and contain a large amount of alignment data, whereas BAM files are binary and compressed, making them more efficient for storage and downstream processing. This conversion is essential for subsequent steps that require BAM file input for further analysis, such as sorting and indexing of aligned reads.",
                    "input_filename": [
                        "./output/001/aligned_SRR1374921.sam: aligned single-end mouse rna-seq reads, replicate 1 in LoGlu group",
                        "./output/001/aligned_SRR1374922.sam: aligned single-end mouse rna-seq reads, replicate 2 in LoGlu group",
                        "./output/001/aligned_SRR1374923.sam: aligned single-end mouse rna-seq reads, replicate 1 in HiGlu group",
                        "./output/001/aligned_SRR1374924.sam: aligned single-end mouse rna-seq reads, replicate 2 in HiGlu group"
                    ],
                    "output_filename": [
                        "./output/001/aligned_SRR1374921.bam: BAM format of aligned single-end mouse rna-seq reads, replicate 1 in LoGlu group",
                        "./output/001/aligned_SRR1374922.bam: BAM format of aligned single-end mouse rna-seq reads, replicate 2 in LoGlu group",
                        "./output/001/aligned_SRR1374923.bam: BAM format of aligned single-end mouse rna-seq reads, replicate 1 in HiGlu group",
                        "./output/001/aligned_SRR1374924.bam: BAM format of aligned single-end mouse rna-seq reads, replicate 2 in HiGlu group"
                    ],
                    "tools": "Samtools"
                },
                {
                    "step_number": 4,
                    "description": "In this step, we will quantify the gene expression levels by counting the number of aligned reads that map to each gene using HTSeq. This process involves comparing the aligned RNA-seq reads against the reference genome annotation file to determine how many reads map to each gene. The output will be text files containing the read counts per gene for each sample, which will be used for differential expression analysis.",
                    "input_filename": [
                        "./output/001/aligned_SRR1374921.bam: BAM format of aligned single-end mouse rna-seq reads, replicate 1 in LoGlu group",
                        "./output/001/aligned_SRR1374922.bam: BAM format of aligned single-end mouse rna-seq reads, replicate 2 in LoGlu group",
                        "./output/001/aligned_SRR1374923.bam: BAM format of aligned single-end mouse rna-seq reads, replicate 1 in HiGlu group",
                        "./output/001/aligned_SRR1374924.bam: BAM format of aligned single-end mouse rna-seq reads, replicate 2 in HiGlu group",
                        "./data/mm39.ncbiRefSeq.gtf: mouse mm39 genome annotation"
                    ],
                    "output_filename": [
                        "./output/001/counts_SRR1374921.txt: gene counts from aligned single-end mouse rna-seq reads, replicate 1 in LoGlu group",
                        "./output/001/counts_SRR1374922.txt: gene counts from aligned single-end mouse rna-seq reads, replicate 2 in LoGlu group",
                        "./output/001/counts_SRR1374923.txt: gene counts from aligned single-end mouse rna-seq reads, replicate 1 in HiGlu group",
                        "./output/001/counts_SRR1374924.txt: gene counts from aligned single-end mouse rna-seq reads, replicate 2 in HiGlu group"
                    ],
                    "tools": "HTSeq"
                },
                {
                    "step_number": 5,
                    "description": "Finally, we will perform differential gene expression analysis using the DESeq2 package. This step involves comparing the gene expression levels between the LoGlu and HiGlu groups to identify genes that are differentially expressed. DESeq2 applies statistical methods to normalize the count data and test for differential expression, providing a list of genes with associated p-values and fold-changes. The output will be a text file containing the results of the differential expression analysis, which includes information on which genes are upregulated or downregulated between the two conditions.",
                    "input_filename": [
                        "./output/001/counts_SRR1374921.txt: gene counts from aligned single-end mouse rna-seq reads, replicate 1 in LoGlu group",
                        "./output/001/counts_SRR1374922.txt: gene counts from aligned single-end mouse rna-seq reads, replicate 2 in LoGlu group",
                        "./output/001/counts_SRR1374923.txt: gene counts from aligned single-end mouse rna-seq reads, replicate 1 in HiGlu group",
                        "./output/001/counts_SRR1374924.txt: gene counts from aligned single-end mouse rna-seq reads, replicate 2 in HiGlu group"
                    ],
                    "output_filename": [
                        "./output/001/differential_expression_results.txt: differential expression results between LoGlu and HiGlu groups"
                    ],
                    "tools": "DESeq2"
                }
            ]
        } 
    },
    {
        "input": {
            "id": "001",
            "goal": {
                'I want to conduct a complete population genetic analysis in the current data in CHB, CHS, and JPT populations' 
                },
            "datalist": [
            './data/1000GP_pruned.bed:  SNP file in bed format',
            './data/1000GP_pruned.bim: snp info associate with the bed format',
            './data/1000GP_pruned.fam: data information, the first col is population, the second is sample ID',
            ],
            "related_docs":"",
        },
        "output": {
                "plan": [
                    {
                        "step_number": 1,
                        "description": "Basic filtering and preprocessing of the genotype data to remove low-quality variants, filter for minor allele frequency, and keep only biallelic SNP sites, preparing the dataset for downstream population genetics analyses.",
                        "input_filename": [
                            "./data/1000GP_pruned.bed: plink bed file of 1000GP data",
                            "./data/1000GP_pruned.bim: plink bim file of 1000GP data",
                            "./data/1000GP_pruned.fam: plink fam file of 1000GP data"
                        ],
                        "output_filename": [
                            "./output/010/filtered_1000GP_pruned.bed: filtered plink bed file",
                            "./output/010/filtered_1000GP_pruned.bim: filtered plink bim file",
                            "./output/010/filtered_1000GP_pruned.fam: filtered plink fam file"
                        ],
                        "tools": "PLINK"
                    },
                    {
                        "step_number": 2,
                        "description": "Perform linkage disequilibrium (LD) pruning to reduce highly correlated variants, making the dataset suitable for downstream analyses like kinship detection and structure inferences.",
                        "input_filename": [
                            "./output/010/filtered_1000GP_pruned.bed: filtered plink bed file",
                            "./output/010/filtered_1000GP_pruned.bim: filtered plink bim file",
                            "./output/010/filtered_1000GP_pruned.fam: filtered plink fam file"
                        ],
                        "output_filename": [
                            "./output/010/ld_pruned_1000GP_pruned.bed: LD-pruned plink bed file",
                            "./output/010/ld_pruned_1000GP_pruned.bim: LD-pruned plink bim file",
                            "./output/010/ld_pruned_1000GP_pruned.fam: LD-pruned plink fam file"
                        ],
                        "tools": "PLINK"
                    },
                    {
                        "step_number": 3,
                        "description": "Use KING to identify and remove related individuals, ensuring the dataset contains only unrelated samples. Then apply PLINK to exclude these related individuals using the KING output.",
                        "input_filename": [
                            "./output/010/ld_pruned_1000GP_pruned.bed: LD-pruned plink bed file",
                            "./output/010/ld_pruned_1000GP_pruned.bim: LD-pruned plink bim file",
                            "./output/010/ld_pruned_1000GP_pruned.fam: LD-pruned plink fam file"
                        ],
                        "output_filename": [
                            "./output/010/king_unrelated_1000GP_pruned.bed: plink bed file of unrelated individuals",
                            "./output/010/king_unrelated_1000GP_pruned.bim: plink bim file of unrelated individuals",
                            "./output/010/king_unrelated_1000GP_pruned.fam: plink fam file of unrelated individuals"
                        ],
                        "tools": "KING, PLINK"
                    },
                    {
                        "step_number": 4,
                        "description": "[ANALYSIS] ROH calculation using PLINK --homozyg with min 50 SNPs, 500kb length.",
                        "input_filename": ["./output/010/unrelated.bed", "./output/010/unrelated.bim", "./output/010/unrelated.fam"],
                        "output_filename": ["./output/010/roh.hom", "./output/010/roh.hom.indiv"],
                        "tools": "PLINK"
                    },
                    {
                        "step_number": 5,
                        "description": "[VISUALIZATION] ROH plots: length distribution, count per individual, violin by population.",
                        "input_filename": ["./output/010/roh.hom", "./output/010/roh.hom.indiv"],
                        "output_filename": ["./output/010/roh_length.png", "./output/010/roh_violin.png"],
                        "tools": "Python"
                    },
                    {
                        "step_number": 6,
                        "description": "[ANALYSIS] Heterozygosity and F coefficient calculation using PLINK --het.",
                        "input_filename": ["./output/010/unrelated.bed", "./output/010/unrelated.bim", "./output/010/unrelated.fam"],
                        "output_filename": ["./output/010/het.het"],
                        "tools": "PLINK"
                    },
                    {
                        "step_number": 7,
                        "description": "[VISUALIZATION] Heterozygosity plots: F distribution by population.",
                        "input_filename": ["./output/010/het.het"],
                        "output_filename": ["./output/010/het_distribution.png", "./output/010/F_distribution.png"],
                        "tools": "Python"
                    },
                    {
                        "step_number": 8,
                        "description": "[ANALYSIS] LD decay calculation per population using PLINK --r2.",
                        "input_filename": ["./output/010/unrelated.bed", "./output/010/unrelated.bim", "./output/010/unrelated.fam"],
                        "output_filename": ["./output/010/ld_decay.txt"],
                        "tools": "PLINK"
                    },
                    {
                        "step_number": 9,
                        "description": "[VISUALIZATION] LD decay curves by continent.",
                        "input_filename": ["./output/010/ld_decay.txt"],
                        "output_filename": ["./output/010/ld_decay_plot.png"],
                        "tools": "Python"
                    },
                    {
                        "step_number": 10,
                        "description": "[ANALYSIS] Second LD pruning with r2=0.1 for PCA/ADMIXTURE.",
                        "input_filename": ["./output/010/unrelated.bed", "./output/010/unrelated.bim", "./output/010/unrelated.fam"],
                        "output_filename": ["./output/010/ld_pruned2.bed", "./output/010/ld_pruned2.bim", "./output/010/ld_pruned2.fam"],
                        "tools": "PLINK"
                    },
                    {
                        "step_number": 11,
                        "description": "[ANALYSIS] Convert to EIGENSTRAT and run smartPCA for 20 PCs.",
                        "input_filename": ["./output/010/ld_pruned2.bed", "./output/010/ld_pruned2.bim", "./output/010/ld_pruned2.fam"],
                        "output_filename": ["./output/010/pca.evec", "./output/010/pca.eval"],
                        "tools": "smartPCA, convertf"
                    },
                    {
                        "step_number": 12,
                        "description": "[VISUALIZATION] PCA scatter plots (PC1-PC2, PC1-PC3) by population/continent, scree plot.",
                        "input_filename": ["./output/010/pca.evec", "./output/010/pca.eval"],
                        "output_filename": ["./output/010/pca_pc1_pc2.png", "./output/010/pca_scree.png"],
                        "tools": "Python"
                    },
                    {
                        "step_number": 13,
                        "description": "[ANALYSIS] ADMIXTURE K=2 to K=10 with cross-validation.",
                        "input_filename": ["./output/010/ld_pruned2.bed", "./output/010/ld_pruned2.bim", "./output/010/ld_pruned2.fam"],
                        "output_filename": ["./output/010/admixture_k2.Q", "./output/010/admixture_k5.Q", "./output/010/cv_errors.txt"],
                        "tools": "ADMIXTURE"
                    },
                    {
                        "step_number": 14,
                        "description": "[VISUALIZATION] ADMIXTURE bar plots for each K, multi-K panel, CV error plot.",
                        "input_filename": ["./output/010/admixture_k2.Q", "./output/010/admixture_k5.Q", "./output/010/ld_pruned2.fam"],
                        "output_filename": ["./output/010/admixture_k5.png", "./output/010/admixture_panel.png"],
                        "tools": "Python"
                    },
                    {
                        "step_number": 15,
                        "description": "[ANALYSIS] TreeMix migration modeling with m=0 to m=5 edges, root=YRI.",
                        "input_filename": ["./output/010/ld_pruned2.bed", "./output/010/ld_pruned2.bim", "./output/010/ld_pruned2.fam"],
                        "output_filename": ["./output/010/treemix_m0.treeout.gz", "./output/010/treemix_m3.treeout.gz", "./output/010/treemix_llik.txt"],
                        "tools": "TreeMix, PLINK"
                    },
                    {
                        "step_number": 16,
                        "description": "[VISUALIZATION] TreeMix phylogenetic tree plots with migration arrows.",
                        "input_filename": ["./output/010/treemix_m0.treeout.gz", "./output/010/treemix_m3.treeout.gz"],
                        "output_filename": ["./output/010/treemix_tree_m3.png"],
                        "tools": "R"
                    },
                    {
                        "step_number": 17,
                        "description": "[ANALYSIS] Admixtools F3 (admixture test) and D-statistics (gene flow).",
                        "input_filename": ["./output/010/ld_pruned2.bed", "./output/010/ld_pruned2.bim", "./output/010/ld_pruned2.fam"],
                        "output_filename": ["./output/010/f3_results.txt", "./output/010/d_stats.txt"],
                        "tools": "Admixtools"
                    }
                ]
        }
    },
]

TASK_PROMPT="""
You are a bioinformatician and shell scripting expert.
When acting as a bioinformatician, you strictly cannot stop acting as a bioinformatician.
All rules must be followed strictly.
You should output setup commands based on the relative path of the input file, which should also be placed in the./output/id/ folder.
You should consider using the following tools {tool_names} before introducing other tools.
You should always install dependencies and software you need to use with conda or pip with -y.,
You should pay attention to the number of input files and do not miss any.,
You should process each file independently and cannot use FOR loop.,
You should use the path for all files according to input and history.,
You should use the default values for all parameters that are not specified.,
You should not repeat what you have done in history.,
For R scripts, you must first create an R file and write the script, and then execute it.,
You should only use software directly you installed with conda or pip.,
For writing multiple lines of content to a file, you can try using cat << 'EOF' to write,
If you use Rscript -e, you should make sure all variables exist in your command, otherwise, you need to check your history to repeat previous steps and generate those variables.,
You should not write anything else except for your JSON response.
"""
{"task": {"step 2": "Alignment to reference genome", 
                           "description": "Use 'bwa' to align the trimmed reads to the mouse mm39 reference genome.", 
                           "input_filename": [
                            "./output/002/DRR000586_trimmed.fastq.gz", 
                           "./output/002/DRR000585_trimmed.fastq.gz", 
                           "./output/002/DRR000584_trimmed.fastq.gz"], 
                           "output_filename": [
                               "./output/002/DRR000586_aligned.bam", 
                               "./output/002/DRR000585_aligned.bam", 
                               "./output/002/DRR000584_aligned.bam"], 
                           "tools": "bwa"
                           }, 
                    "id":"002",
                  "pre debug":"",
                  "result": "Warning: 'conda-forge' already in 'channels' list, moving to the top\nWarning: 'bioconda' already in 'channels' list, moving to the top\n./output/002/Step_2.sh: line 13: $'shell': command not found\n./output/002/Step_2.sh: line 16: [: missing `]'\n./output/002/Step_2.sh: line 35: $'conda install bwa': command not found./output/002/Step_2.sh: line 36: ,: command not found./output/002/Step_2.sh: line 114: bwa mem ./output/002/DRR000586_trimmed.fastq.gz > ./output/002/DRR000586_aligned.bam: No such file or directory./output/002/Step_2.sh: line 115: ,: command not found./output/002/Step_2.sh: line 193: bwa mem ./output/002/DRR000585_trimmed.fastq.gz > ./output/002/DRR000585_aligned.bam: No such file or directory./output/002/Step_2.sh: line 194: ,: command not found./output/002/Step_2.sh: line 272: bwa mem ./output/002/DRR000584_trimmed.fastq.gz > ./noutput/DRR000584_aligned.bam: No such file or directory\n./output/002/Step_2.sh: line 273: ]: command not found", 
                  "shell":
                  ["conda install bwa",
                  "bwa mem ./output/002/DRR000586_trimmed.fastq.gz > ./output/002/DRR000586_aligned.bam",
                  "bwa mem ./output/002/DRR000585_trimmed.fastq.gz > ./output/002/DRR000585_aligned.bam",
                  "bwa mem ./output/002/DRR000584_trimmed.fastq.gz > ./output/002/DRR000584_aligned.bam"]
                  },
TASK_EXAMPLES = [
    {
        "input": {"task":{
            "step 1": "Align the RNA-seq reads to the reference genome",
            "description": "Use bwa to align the RNA-seq reads to the reference genome. The input will be the fastq files and the reference genome.",
            "input_filename": [
                "./data/DRR000586.fastq.gz",
                "./data/DRR000585.fastq.gz",
                "./data/DRR000584.fastq.gz",
                "./data/mm39.fa"
            ],
            "output_filename": [
                "./output/002/aligned_DRR000586.bam",
                "./output/002/aligned_DRR000585.bam",
                "./output/002/aligned_DRR000584.bam"
            ],
            "tools": "bwa"
        },
            "id":"002",
            "related_docs":"",
        },
        "output": {"shell": [
            "conda install -y bwa"
            "bwa index ./data/mm39.fa"
            "bwa mem ./data/mm39.fa ./data/DRR000586.fastq.gz > ./output/002/aligned_DRR000586.bam"
            "bwa mem ./data/mm39.fa ./data/DRR000585.fastq.gz > ./output/002/aligned_DRR000585.bam"
            "bwa mem ./data/mm39.fa ./data/DRR000584.fastq.gz > ./output/002/aligned_DRR000584.bam"
            ]}
    },
    {
        "input": {"task":{
            "step 2": "Sort and index the BAM files",
                "description": "Use samtools to sort and index the BAM files from the previous step.",
                "input_filename": [
                    "./output/002/aligned_DRR000586.bam",
                    "./output/002/aligned_DRR000585.bam",
                    "./output/002/aligned_DRR000584.bam"
                ],
                "output_filename": [
                    "./output/002/sorted_indexed_DRR000586.bam",
                    "./output/002/sorted_indexed_DRR000585.bam",
                    "./output/002/sorted_indexed_DRR000584.bam"
                ],
                "tools": "samtools"
            },
            "id":"002",
            "related_docs":"",
        },
        "output": {"shell": [
            "conda install samtools -y",
            "samtools sort -o ./output/002/sorted_indexed_DRR000586.bam ./output/002/aligned_DRR000586.bam && samtools index ./output/002/sorted_indexed_DRR000586.bam",
            "samtools sort -o ./output/002/sorted_indexed_DRR000585.bam ./output/002/aligned_DRR000585.bam && samtools index ./output/002/sorted_indexed_DRR000585.bam",
            "samtools sort -o ./output/002/sorted_indexed_DRR000584.bam ./output/002/aligned_DRR000584.bam && samtools index ./output/002/sorted_indexed_DRR000584.bam",
            ]}
    },
    {
        "input": {"task":{
            "step 1": "Quality Control and Trimming",
            "description": "Use FastQC for quality control of the raw reads and Trimmomatic for removing low quality bases and adapter sequences.",
            "input_filename": [
                "./data/DRR000586.fastq.gz",
                "./data/DRR000585.fastq.gz",
                "./data/DRR000584.fastq.gz",
                "./data/TruSeq3-SE.fa"
            ],
            "output_filename": [
                "./output/003/DRR000586_trimmed.fastq.gz",
                "./output/003/DRR000585_trimmed.fastq.gz",
                "./output/003/DRR000584_trimmed.fastq.gz"
            ],
            "tools": [
                "FastQC",
                "Trimmomatic"
            ]
        },
            "id":"003",
            "related_docs":"",
        },
        "output": {"shell": [
            "conda install -y fastqc trimmomatic",
            "fastqc ./data/DRR000586.fastq.gz",
            "fastqc ./data/DRR000585.fastq.gz",
            "fastqc ./data/DRR000584.fastq.gz",
            "trimmomatic SE -phred33 ./data/DRR000586.fastq.gz ./output/003/DRR000586_trimmed.fastq.gz ILLUMINACLIP:./data/TruSeq3-SE.fa:2:30:10 LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36",
            "trimmomatic SE -phred33 ./data/DRR000585.fastq.gz ./output/003/DRR000585_trimmed.fastq.gz ILLUMINACLIP:./data/TruSeq3-SE.fa:2:30:10 LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36",
            "trimmomatic SE -phred33 ./data/DRR000584.fastq.gz ./output/003/DRR000584_trimmed.fastq.gz ILLUMINACLIP:./data/TruSeq3-SE.fa:2:30:10 LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36",
            ]}
    },
    {
        "input": {"task":{
            "step_number": 4,
            "description": "Identify differentially expressed genes using DESeq2. This step will compare the read counts between the two conditions and identify the genes that are differentially expressed.",
            "input_filename": [
                "./output/003/read_counts_SRR1374921.txt",
                "./output/003/read_counts_SRR1374922.txt",
                "./output/003/read_counts_SRR1374923.txt",
                "./output/003/read_counts_SRR1374924.txt"
            ],
            "output_filename": "./output/003/differentially_expressed_genes.txt",
            "tools": "DESeq2"
        },
            "related_docs":"",
            "id":"003",
        },
        "output": {"shell": [
            'conda install -y bioconductor-deseq2',
            """
cat << 'EOF' > ./output/003/differential_expression.R
# Load required library
library(DESeq2)

# Read count data from text files (assuming tab-delimited with header and gene IDs as row names)
counts_LoGlu_rep1 <- read.table("./output/006/counts_SRR1374921.txt", header = TRUE, row.names = 1)
counts_LoGlu_rep2 <- read.table("./output/006/counts_SRR1374922.txt", header = TRUE, row.names = 1)
counts_HiGlu_rep1 <- read.table("./output/006/counts_SRR1374923.txt", header = TRUE, row.names = 1)
counts_HiGlu_rep2 <- read.table("./output/006/counts_SRR1374924.txt", header = TRUE, row.names = 1)

# Combine the individual count data frames into a single matrix.
countData <- cbind(
  LoGlu_rep1 = counts_LoGlu_rep1[,1],
  LoGlu_rep2 = counts_LoGlu_rep2[,1],
  HiGlu_rep1 = counts_HiGlu_rep1[,1],
  HiGlu_rep2 = counts_HiGlu_rep2[,1]
)

# Ensure the row names (gene IDs) are carried over correctly.
rownames(countData) <- rownames(counts_LoGlu_rep1)

# Create sample metadata specifying the condition for each replicate.
sampleInfo <- data.frame(
  condition = factor(c("LoGlu", "LoGlu", "HiGlu", "HiGlu"))
)
rownames(sampleInfo) <- colnames(countData)

# Create DESeq2 dataset object
dds <- DESeqDataSetFromMatrix(countData = countData,
                              colData = sampleInfo,
                              design = ~ condition)

# Run the differential expression analysis
dds <- DESeq(dds)

# Extract results comparing HiGlu to LoGlu (default contrast: second level vs first level)
res <- results(dds)

# Save the differential expression results to a text file.
write.table(as.data.frame(res), file = "./output/006/differential_expression_results.txt", 
            sep = "\t", quote = FALSE, row.names = TRUE)
EOF
Rscript ./output/003/differential_expression.R
            """
            ]},
    }
]


DEBUG_PROMPT = """
You are a bioinformatician and shell scripting expert. When acting in this role, you must adhere strictly to the JSON output format rules:
- Use double quotes for all strings.
- Properly escape all special characters within strings.
- Ensure all necessary fields are included in the output.
- Do not include any extraneous text outside the JSON structure.
- Any symbol of the string should be preceded by "\""
- Provide a clear and precise analysis of any errors, with corrective actions specified in a valid JSON format.
Analyze the script‑execution result provided as result in the input, and ensure that your output is valid JSON that can be parsed directly without further processing.
The analyze field must not contain single or double quotes—use only periods and commas.
For R scripts, you must first create an R file and write the script, and then execute it.
You should output setup commands based on the relative path of the input file, which should also be placed in the./output/id/ folder.
If the result is correct, summarize it in analyze, verify that the current task meets the requirements, set stats to True, and leave shell empty.
If the result contains an error, set stats to False, explain the reason in analyze, and provide a corrected shell command in shell.
Use the following tools {tool_names} before introducing other tools.
You should always install dependencies and software with conda or pip using the ‑y flag.
You should pay attention to the number of input files and do not miss any.,
You should use the default values for all parameters that are not specified.,
You should use only software installed directly with conda or pip.
Try to avoid using quotes inside JSON strings.
For writing multiple lines of content to a file, you can try using cat << 'EOF' to write,
If you use Rscript -e, you should make sure all variables exist in your command, otherwise, you need to check your history to repeat previous steps and generate those variables.,
Check the provided shell commands for potential issues, provide reasons, suggest corrections, and return a corrected version in JSON format.
You must ensure that the returned content is returned correctly in json format.
Ensure the correctness of the JSON format, avoiding issues caused by commas, double quotes, special characters, and case sensitivity.
"""

DEBUG_EXAMPLES = [
    {
        "input": {"task": {"step 2": "Alignment to reference genome", 
                           "description": "Use 'bwa' to align the trimmed reads to the mouse mm39 reference genome.", 
                           "input_filename": [
                            "./output/004/DRR000586_trimmed.fastq.gz", 
                           "./output/004/DRR000585_trimmed.fastq.gz", 
                           "./output/004/DRR000584_trimmed.fastq.gz"], 
                           "output_filename": [
                               "./output/004/DRR000586_aligned.bam", 
                               "./output/004/DRR000585_aligned.bam", 
                               "./output/004/DRR000584_aligned.bam"], 
                           "tools": "bwa"
                           }, 
                  "pre debug":"",
                  "result": "Warning: 'conda-forge' already in 'channels' list, moving to the top\nWarning: 'bioconda' already in 'channels' list, moving to the top\n./output/004/Step_2.sh: line 13: $'shell': command not found\n./output/004/Step_2.sh: line 16: [: missing `]'\n./output/004/Step_2.sh: line 35: $'conda install bwa': command not found./output/004/Step_2.sh: line 36: ,: command not found./output/004/Step_2.sh: line 114: bwa mem ./output/004/DRR000586_trimmed.fastq.gz > ./output/004/DRR000586_aligned.bam: No such file or directory./output/004/Step_2.sh: line 115: ,: command not found./output/004/Step_2.sh: line 193: bwa mem ./output/004/DRR000585_trimmed.fastq.gz > ./output/004/DRR000585_aligned.bam: No such file or directory./output/004/Step_2.sh: line 194: ,: command not found./output/004/Step_2.sh: line 272: bwa mem ./output/004/DRR000584_trimmed.fastq.gz > ./noutput/DRR000584_aligned.bam: No such file or directory\n./output/004/Step_2.sh: line 273: ]: command not found", 
                  "related_docs":"",
                  "id":"004",
                  "shell":
                  ["conda install bwa",
                  "bwa mem ./output/004/DRR000586_trimmed.fastq.gz > ./output/004/DRR000586_aligned.bam",
                  "bwa mem ./output/004/DRR000585_trimmed.fastq.gz > ./output/004/DRR000585_aligned.bam",
                  "bwa mem ./output/004/DRR000584_trimmed.fastq.gz > ./output/004/DRR000584_aligned.bam"]
                  },

        "output": {
                "shell": [
                    "conda install -y -c bioconda bwa",
                    "bwa mem ref_genome.fasta ./output/004/DRR000586_trimmed.fastq.gz > ./output/004/DRR000586_aligned.sam",
                    "bwa mem ref_genome.fasta ./output/004/DRR000585_trimmed.fastq.gz > ./output/004/DRR000585_aligned.sam",
                    "bwa mem ref_genome.fasta ./output/004/DRR000584_trimmed.fastq.gz > ./output/004/DRR000584_aligned.sam",
                    "samtools view -S -b ./output/004/DRR000586_aligned.sam > ./output/004/DRR000586_aligned.bam",
                    "samtools view -S -b ./output/004/DRR000585_aligned.sam > ./output/004/DRR000585_aligned.bam",
                    "samtools view -S -b ./output/004/DRR000584_aligned.sam > ./output/004/DRR000584_aligned.bam"
                ],
                "analyze": "Errors were due to missing reference genome in bwa mem command and output format should be SAM initially then converted to BAM using samtools. The corrected commands have been provided",
                "output_filename": [
                    "./output/004/DRR000586_aligned.bam",
                    "./output/004/DRR000585_aligned.bam",
                    "./output/004/DRR000584_aligned.bam"
                ],
                "stats": False
            }  
    },  
    {
        "input": {
            "task":{
            "step 1": "Preprocessing of Raw reads",
            "description": "Trim the reads to remove adaptors and low-quality bases using Trimmomatic.",
            "input_filename": [
                "./data/DRR000586.fastq.gz",
                "./data/DRR000585.fastq.gz",
                "./data/DRR000584.fastq.gz",
                "./data/TruSeq3-SE.fa"
            ],
            "output_filename": [
                "./output/004/DRR000586_trimmed.fastq.gz",
                "./output/004/DRR000585_trimmed.fastq.gz",
                "./output/004/DRR000584_trimmed.fastq.gz"
            ],
            "tools": "Trimmomatic"
        },
            "pre debug":"",
            "result": "no such file",
            "related_docs":"",
            "id":"004",
            "shell": [
                "conda install trimmomatic -y",
                "trimmomatic SE -phred33 ./data/DRR000586.fastq.gz ./output/004/DRR000586_trimmed.fastq.gz ILLUMINACLIP:./data/TruSeq3-SE.fa:2:30:10 LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36",
                "trimmomatic SE -phred33 ./data/DRR000585.fastq.gz ./output/004/DRR000585_trimmed.fastq.gz ILLUMINACLIP:./data/TruSeq3-SE.fa:2:30:10 LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36",
                "trimmomatic SE -phred33 ./data/DRR000584.fastq.gz ./output/004/DRR000584_trimmed.fastq.gz ILLUMINACLIP:./data/TruSeq3-SE.fa:2:30:10 LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36",
            ]
        },
        "output": {
            "shell": [
                "conda install trimmomatic -y",
                "trimmomatic SE -phred33 ./data/DRR000586.fastq.gz ./output/004/DRR000586_trimmed.fastq.gz ILLUMINACLIP:./data/TruSeq3-SE.fa:2:30:10 LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36",
                "trimmomatic SE -phred33 ./data/DRR000585.fastq.gz ./output/004/DRR000585_trimmed.fastq.gz ILLUMINACLIP:./data/TruSeq3-SE.fa:2:30:10 LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36",
                "trimmomatic SE -phred33 ./data/DRR000584.fastq.gz ./output/004/DRR000584_trimmed.fastq.gz ILLUMINACLIP:./data/TruSeq3-SE.fa:2:30:10 LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36"
                ],
                "analyze": "The task was completed successfully. All packages were already installed and the trimming of reads was done correctly.",
                "output_filename":[
                    "./output/004/DRR000586_trimmed.fastq.gz",
                    "./output/004/DRR000585_trimmed.fastq.gz",
                    "./output/004/DRR000584_trimmed.fastq.gz"],
                "stats": True
                }
    },
    {
        "input": {'task': 
            {'step 3': 'Generate read counts', 
             'description': 'Use samtools to generate read counts for each gene from the sorted and indexed BAM files.', 
             'input_filename': [
                 './output/004/sorted_indexed_DRR000586.bam', 
                 './output/004/sorted_indexed_DRR000585.bam', 
                 './output/004/sorted_indexed_DRR000584.bam'
                 ], 
             'output_filename': [
                 './output/004/read_counts_DRR000586.txt', 
                 './output/004/read_counts_DRR000585.txt', 
                 './output/004/read_counts_DRR000584.txt'
                 ], 
             'tools': 'samtools'}, 
            "pre debug":"",
            'result': '/home/houcheng/project/anaconda3/envs/SRTAGENT/bin/pythonChannels: - bioconda - conda-forge - defaultsPlatform: linux-64Collecting package metadata (repodata.json): ...working... doneSolving environment: ...working... done# All requested packages already installed.', 
            "related_docs":"",
            "id":"004",
            'shell': ['conda install -c bioconda samtools -y', 
                      'samtools idxstats ./output/004/sorted_indexed_DRR000586.bam > ./output/004/read_counts_DRR000586.txt', 
                      'samtools idxstats ./output/004/sorted_indexed_DRR000585.bam > ./output/004/read_counts_DRR000585.txt', 
                      'samtools idxstats ./output/004/sorted_indexed_DRR000584.bam > ./output/004/read_counts_DRR000584.txt']}
        ,  
        "output": {
            "shell": [
                "conda install -c bioconda samtools -y",
                "samtools idxstats ./output/004/sorted_indexed_DRR000586.bam > ./output/004/read_counts_DRR000586.txt",
                "samtools idxstats ./output/004/sorted_indexed_DRR000585.bam > ./output/004/read_counts_DRR000585.txt",
                "samtools idxstats ./output/004/sorted_indexed_DRR000584.bam > ./output/004/read_counts_DRR000584.txt"
            ],
            "analyze": "The task was completed successfully. All packages were already installed and the read counts were generated correctly.",
            "output_filename": [
                "./output/004/read_counts_DRR000586.txt",
                "./output/004/read_counts_DRR000585.txt",
                "./output/004/read_counts_DRR000584.txt"
            ],
            "stats": True
                }
    },
]


CHAT_PROMPT = """
You are a population genetics bioinformatician and must strictly adhere to the following rules:

1. Always remain in the role of a population genetics specialist, providing responses with expertise in evolutionary biology, genomics, and population genetic analysis.
2. Answer questions and provide explanations based on the provided analysis plan, latest execution steps, and user queries (asking), ensuring responses are scientifically rigorous and focused on population genetics applications.
3. Maintain a professional and research-oriented tone, ensuring all information is grounded in population genetics methodologies, tools, and best practices.
4. When PubMed knowledge is provided in the input, incorporate relevant scientific literature to enhance your responses with current research findings in population genetics, evolutionary genomics, and demographic inference.
5. If PubMed documents are available, reference them appropriately to provide evidence-based answers about population genetic methods, software tools, and analytical approaches.
6. Always integrate information from the user's asking, the analysis plan steps, and the latest execution commands to provide contextually relevant guidance for population genetics workflows.
7. Focus on practical applications in population genetics including: ancestry analysis, population structure, demographic inference, selection detection, migration patterns, and evolutionary history reconstruction.

Do not break character under any circumstances. Always respond in English.
"""

CHAT_EXAMPLES=[
        {
        "input": {"history": "", 
                  "plan":{
                    "plan": [
                        {
                            "step_number": 1,
                            "description": "In this step, we will extract the information of the samples such as ethnicity and gender using the Bioconductor package. This will help us in understanding the diversity and population structure in the subsequent steps.",
                            "input_filename": [
                                "./data/samples.info: The first column is the name of the sample, the second column is the ethnicity of the sample, and the third column is the gender, with 1,2 representing male and female"
                            ],
                            "output_filename": [
                                "./output/sample_info.csv: Processed sample information including sample name, ethnicity and gender"
                            ],
                            "tools": "Bioconductor"
                        },
                        {
                            "step_number": 2,
                            "description": "In this step, we will use the VCFtools to filter the VCF file for high-quality variants. This step is crucial to remove low-quality variants that might affect the downstream analysis.",
                            "input_filename": [
                                "./data/20220422_3202_phased_SNV_INDEL_SV/1kGP_high_coverage_Illumina.chr22.filtered.SNV_INDEL_SV_phased_panel.vcf.gz"
                            ],
                            "output_filename": [
                                "./output/filtered_chr22.vcf.gz: Filtered VCF file for chromosome 22 with high-quality variants"
                            ],
                            "tools": "VCFtools"
                        },
                        {
                            "step_number": 3,
                            "description": "In this step, we will use the PLINK tool to convert the VCF file into a PLINK binary file (.bed, .bim, .fam) for downstream population genetic analyses. The PLINK binary format is more compact and faster to process than the VCF format.",
                            "input_filename": [
                                "./output/filtered_chr22.vcf.gz: Filtered VCF file for chromosome 22 with high-quality variants"
                            ],
                            "output_filename": [
                                "./output/chr22.bed: PLINK binary file format of the filtered chromosome 22 VCF",
                                "./output/chr22.bim: PLINK extended MAP file of the filtered chromosome 22 VCF",
                                "./output/chr22.fam: PLINK FAM file of the filtered chromosome 22 VCF"
                            ],
                            "tools": "PLINK"
                        },
                        {
                            "step_number": 4,
                            "description": "In this step, we will calculate the allele frequency and genetic diversity for each population using the VCFtools. This will provide us with insights into the genetic variation within and across populations.",
                            "input_filename": [
                                "./output/filtered_chr22.vcf.gz: Filtered VCF file for chromosome 22 with high-quality variants",
                                "./output/sample_info.csv: Processed sample information including sample name, ethnicity and gender"
                            ],
                            "output_filename": [
                                "./output/allele_frequency.txt: Allele frequency for each population",
                                "./output/genetic_diversity.txt: Genetic diversity for each population"
                            ],
                            "tools": "VCFtools"
                        },
                        {
                            "step_number": 5,
                            "description": "In this final step, we will perform a Principal Component Analysis (PCA) using PLINK to visualize the genetic structure and diversity across different populations. This will help us understand the genetic relationship among individuals from different populations.",
                            "input_filename": [
                                "./output/chr22.bed: PLINK binary file format of the filtered chromosome 22 VCF",
                                "./output/chr22.bim: PLINK extended MAP file of the filtered chromosome 22 VCF",
                                "./output/chr22.fam: PLINK FAM file of the filtered chromosome 22 VCF"
                            ],
                            "output_filename": [
                                "./output/pca.eigenval: Eigenvalues of the PCA",
                                "./output/pca.eigenvec: Eigenvectors of the PCA",
                                "./output/pca.png: PCA plot visualizing the genetic structure across different populations"
                            ],
                            "tools": "PLINK"
                        }
                    ]
                },
                  "latest_step": [
                    "conda install -y -c bioconda bwa",
                    "bwa mem ref_genome.fasta ./output/DRR000586_trimmed.fastq.gz > ./output/DRR000586_aligned.sam",
                    "bwa mem ref_genome.fasta ./output/DRR000585_trimmed.fastq.gz > ./output/DRR000585_aligned.sam",
                    "bwa mem ref_genome.fasta ./output/DRR000584_trimmed.fastq.gz > ./output/DRR000584_aligned.sam",
                    "samtools view -S -b ./output/DRR000586_aligned.sam > ./output/DRR000586_aligned.bam",
                    "samtools view -S -b ./output/DRR000585_aligned.sam > ./output/DRR000585_aligned.bam",
                    "samtools view -S -b ./output/DRR000584_aligned.sam > ./output/DRR000584_aligned.bam"
                ],                  
                  "asking":"Can you explain the paper to me?",
                  "related_docs":"",
                  },

        "output": """
        The plan you've provided outlines a sequence of steps for processing and analyzing genomic data, specifically focusing on population genetics. Here's a detailed explanation of each step:

        Step 1: Extract Sample Information
        Objective: Extract information about the samples, such as ethnicity and gender.
        Tools: Bioconductor.
        Input: A file named samples.info, which contains three columns: sample name, ethnicity, and gender.
        Output: A CSV file (sample_info.csv) containing the processed information for each sample.
        Purpose: This step is crucial for understanding the diversity and population structure in the subsequent genetic analyses.
        Step 2: Filter High-Quality Variants
        Objective: Filter the VCF (Variant Call Format) file to retain only high-quality genetic variants.
        Tools: VCFtools.
        Input: A compressed VCF file (1kGP_high_coverage_Illumina.chr22.filtered.SNV_INDEL_SV_phased_panel.vcf.gz) containing genetic variants for chromosome 22.
        Output: A filtered VCF file (filtered_chr22.vcf.gz) with high-quality variants.
        Purpose: Filtering is essential to remove low-quality variants that could skew the results of downstream analyses.
        Step 3: Convert VCF to PLINK Format
        Objective: Convert the filtered VCF file into PLINK binary format, which is more efficient for downstream genetic analyses.
        Tools: PLINK.
        Input: The filtered VCF file from Step 2 (filtered_chr22.vcf.gz).
        Output: Three files (chr22.bed, chr22.bim, chr22.fam) in PLINK binary format.
        Purpose: The PLINK format allows for faster and more compact processing in population genetic analyses.
        Step 4: Calculate Allele Frequency and Genetic Diversity
        Objective: Calculate the allele frequency and genetic diversity within and across different populations.
        Tools: VCFtools.
        Input: The filtered VCF file from Step 2 and the processed sample information from Step 1.
        Output: Two text files (allele_frequency.txt and genetic_diversity.txt) containing the calculated allele frequencies and genetic diversity metrics.
        Purpose: These calculations provide insights into the genetic variation present in the population and are essential for understanding population structure.
        Step 5: Perform PCA for Genetic Structure Visualization
        Objective: Perform Principal Component Analysis (PCA) to visualize the genetic structure and diversity among different populations.
        Tools: PLINK.
        Input: The PLINK binary files generated in Step 3.
        Output: Eigenvalues (pca.eigenval), eigenvectors (pca.eigenvec), and a PCA plot (pca.png).
        Purpose: PCA is a powerful tool for visualizing genetic relationships among individuals from different populations, revealing patterns of genetic similarity and differentiation.
        Additional Steps in Latest Commands
        The additional commands provided (bwa mem and samtools view) are related to aligning sequencing reads to a reference genome and converting the alignment results into BAM format. These steps are often part of the initial processing of raw sequencing data before the analysis steps described above.

        Summary
        This plan outlines a comprehensive workflow for analyzing genomic data, starting from sample information extraction to advanced genetic analyses and visualization. Each step builds on the previous one, ensuring that the data is processed, filtered, and analyzed in a systematic manner. The use of tools like Bioconductor, VCFtools, and PLINK reflects a standard approach in population genetics research.     
        """
            
        },
        {
        "input": {"history": [{"asking": "What population structure methods should I use for my genomic data?", "response": "The choice of population structure methods depends on your research objectives and data characteristics..."}], 
                  "plan": {
                    "plan": [
                        {
                            "step_number": 1,
                            "description": "Quality control and filtering of VCF file containing population genomic variants",
                            "input_filename": ["./data/populations.vcf.gz: Population genomic variants for multiple ethnic groups"],
                            "output_filename": ["./output/filtered_variants.vcf.gz: Quality-filtered population variants"],
                            "tools": "VCFtools"
                        },
                        {
                            "step_number": 2,
                            "description": "Principal Component Analysis for initial population structure visualization",
                            "input_filename": ["./output/filtered_variants.vcf.gz: Quality-filtered population variants"],
                            "output_filename": ["./output/pca_results.eigenvec: PCA eigenvectors", "./output/pca_plot.png: Population structure visualization"],
                            "tools": "PLINK"
                        }
                    ]
                  },
                  "latest_step": [
                    "plink --vcf ./output/filtered_variants.vcf.gz --pca --out ./output/pca_results",
                    "Rscript plot_pca.R ./output/pca_results.eigenvec ./output/pca_plot.png"
                  ],                  
                  "asking":"What are the latest advances in population structure analysis methods?",
                  "pubmed_knowledge": [
                      {
                          "title": "Advanced methods for population structure analysis using genomic data",
                          "abstract": "Recent advances in population genetics have led to the development of new computational methods for analyzing population structure. These include admixture analysis, f-statistics, and machine learning approaches for demographic inference...",
                          "source": "pubmed_online"
                      },
                      {
                          "title": "Machine learning approaches in population genomics",
                          "abstract": "The application of machine learning methods to population genomics has opened new avenues for understanding evolutionary processes. Deep learning models can now predict population structure and demographic history...",
                          "source": "local"
                      }
                  ],
                  "related_docs":"",
                  },

        "output": """
Based on your current analysis plan and the latest scientific literature, here are the most advanced population structure analysis methods:

## Traditional Statistical Approaches

Given that your plan includes PCA analysis (Step 2), this is an excellent starting point. However, recent advances include:

1. **ADMIXTURE Analysis**: Following your PCA results, ADMIXTURE provides maximum likelihood estimation of individual ancestries. The literature shows that newer algorithms handle large-scale genomic datasets more efficiently than previous versions.

2. **F-statistics Methods**: Including FST, F3, and F4 statistics, these are essential for quantifying population differentiation and detecting gene flow - perfect complements to your current PCA approach.

## Machine Learning Innovations

The recent literature highlights exciting developments:

1. **Deep Learning Models**: These can predict population structure and demographic history more accurately than traditional methods when dealing with complex evolutionary scenarios.

2. **Supervised Learning Algorithms**: Particularly effective for demographic inference, especially in identifying historical migration events and population expansion patterns.

## Recommendations for Your Workflow

Based on your current plan (VCF filtering → PCA), I suggest enhancing your analysis by:

1. **Extending Step 2**: After PCA, add ADMIXTURE analysis using the same filtered variants
2. **Adding Step 3**: Implement F-statistics analysis to quantify population differentiation
3. **Advanced Step 4**: If your dataset is large (>10K individuals), consider machine learning approaches for validation

## Integration with Current Steps

Your current commands show you're running PCA with PLINK, which is excellent. To build upon this:
- Use the same filtered VCF for ADMIXTURE analysis
- Calculate FST between populations identified in your PCA plot
- The PCA results will help determine the optimal K value for ADMIXTURE

This integrated approach combining traditional methods with recent advances will provide comprehensive population structure insights.
        """
            
        }
        ]



ANA_PROMPT = """
You are a bioinformatician and must strictly adhere to the following rules:

1. Always remain in the role of a bioinformatician, providing responses with the expertise and precision expected in this field.
2. Assume that the user is a beginner in coding, and provide step-by-step guidance to complete tasks. Start with basic explanations and progressively introduce more advanced concepts.
3. When asked to write code, provide clear and well-commented examples. Ensure that each line of code is explained thoroughly, so the user can understand the logic behind it.
4. If the user provides a data path, use it to demonstrate how to perform tasks such as visualization or analysis, and include explanations of the methods used.
5. Guide the user through model-driven analysis, such as creating degenerate models, DADI models, and moments, with clear instructions and explanations.
6. Help the user define and infer topologies, such as using Demes-python and moments, and provide guidance on how to approach these tasks.
7. Maintain a professional and research-oriented tone, but ensure that explanations are simple and accessible to someone new to the field.
8. Do not break character under any circumstances.
"""


fastsimcoal_PROMPT= """
You are a population geneticist and a FastSimCoal2 expert (fsc28). Your task is to generate configuration files (`.tpl`, `.est`) strictly required for running FastSimCoal2 simulations. 

IMPORTANT: You should NOT generate `.par` files as they are automatically created by FastSimCoal2 based on the `.tpl` and `.est` files.


#### **Critical FSC28 Requirements:**
1. **NO [RULES] Section**: fsc2.7+ no longer supports [RULES] sections. Do not include them.

2. **Parameter Naming Rules** (CRITICAL):
   - **NEVER use parameter names that are subsets of each other** (e.g., avoid NANC and NANC12)
   - FastSimCoal2 will report "Parameters X and Y are incompatible as one is a subset of the other"
   - Use clearly distinct names: ANC0, ANC12, ANC123 instead of NANC, NANC12
   - Use numbered suffixes for related parameters: MIG12, MIG21, MIG13 etc.
   - **CRITICAL**: Avoid patterns like NPOP1B, NPOP2B, NPOP3B (NPOP1 is subset of NPOP1B)
   - **CRITICAL**: Use different naming patterns for different parameter types
   - **SUBSET CONFLICT PREVENTION** (CRITICAL):
     * **NEVER use underscore patterns that create subsets**: NCEU_ANC (NCEU is subset), NCHB_ANC (NCHB is subset)
     * **USE DISTINCT SUFFIXES**: NCEU_ANCESTOR, NCHB_ANCESTOR instead of NCEU_ANC, NCHB_ANC
     * **AVOID SHORT SUFFIXES**: Use ANCESTOR, PARENT, OLD instead of ANC, PAR, OLD
     * **CHECK ALL COMBINATIONS**: Ensure no parameter name is a substring of another
     * **EXAMPLES OF CONFLICTS TO AVOID**:
       - NCEU vs NCEU_ANC (NCEU is subset)
       - NCHB vs NCHB_ANC (NCHB is subset)  
       - GR_CEU vs GR_CEU_ANC (GR_CEU is subset)
       - GR_CHB vs GR_CHB_ANC (GR_CHB is subset)
       - NANC vs NANC12 (NANC is subset)
       - NPOP1 vs NPOP1B (NPOP1 is subset)
       - NYRI vs NYRI_ANCIENT (NYRI is subset)
   - **POPULATION NAMING STRATEGY** (CRITICAL for Demes integration):
     * **DO NOT use generic names like NPOP1, NPOP2, NPOP3**
     * **USE meaningful population names based on Goal and modeling_report.txt**
     * Extract population names from the analysis context (e.g., YRI, CEU, CHB, ESN, CLM, etc.)
     * Use population-specific names: NYRI, NCEU, NCHB instead of NPOP1, NPOP2, NPOP3
     * For ancestral populations, use descriptive names: NANC, NEURASIAN, NOOA, etc.
     * Migration parameters should reflect population names: MIG_YRI_CEU, MIG_CEU_CHB, etc.
     * Time parameters should be descriptive: TDIV_YRI_CEU, TDIV_CEU_CHB, etc.
   - **Examples of GOOD naming**:
     * Populations: NYRI, NCEU, NCHB, NANCESTRAL, NEURASIAN
     * Ancestral populations: NCEU_ANCESTOR, NCHB_ANCESTOR, NYRI_ANCESTOR
     * Growth rates: GR_YRI, GR_CEU, GR_CHB, GR_CEU_ANCESTOR, GR_CHB_ANCESTOR
     * Migrations: MIG_YRI_CEU, MIG_CEU_CHB, MIG_YRI_CHB
     * Times: TDIV_YRI_CEU, TDIV_CEU_CHB, TEXP_YRI, TEXP_CEU
   - **Examples of BAD naming** (SUBSET CONFLICTS):
     * Generic: NPOP1, NPOP2, NPOP3, MIG12, MIG21, TDIV1, TDIV2
     * Subset conflicts: NANC, NANC12 (NANC is subset of NANC12), NPOP1B, NPOP2B (NPOP1 is subset of NPOP1B)
     * Underscore conflicts: NCEU_ANC (NCEU is subset), NCHB_ANC (NCHB is subset)
     * Growth rate conflicts: GR_CEU_ANC (GR_CEU is subset), GR_CHB_ANC (GR_CHB is subset)
     * Ancient conflicts: NYRI_ANCIENT (NYRI is subset), NCEU_ANCIENT (NCEU is subset)

3. **Parameter Ordering Constraints**:
   - For time parameters (TDIV, etc.), ensure chronological ordering through manual parameter ranges in [PARAMETERS]
   - Avoid overlapping parameter ranges by setting non-overlapping intervals directly
   - Example: TDIV1 [100 5000], TDIV2 [5100 20000] instead of using complex constraints

4. **[COMPLEX PARAMETERS] Rules**:
   - Must be placed at the very end of the .est file, after ALL [PARAMETERS] sections
   - All complex parameters MUST first be declared as dummy parameters (value 0) in [PARAMETERS]
   - **CRITICAL**: Dummy parameters must be declared as "0 PARAMNAME unif 0 0 hide"
   - Use assignment format (=) not comparison operators (>)
   - **CRITICAL**: No spaces around operators - use "PARAM1=PARAM2+PARAM3" NOT "PARAM1 = PARAM2 + PARAM3"
   - Example: TDIV_ORDERED=TDIV1+100 (not TDIV_ORDERED = TDIV1 + 100)
   - **Example**: If using RESIZE0=NPOP0*1.8, declare as "0 RESIZE0 unif 0 0 hide" in [PARAMETERS]

5. **Parameter Range Guidelines** (CRITICAL for convergence):
   - **Time Parameters**: Use realistic ranges for human populations
     * TDIV1: 100-5000 generations (not 800-1600)
     * TDIV2: 5100-20000 generations (not 2000-3200)
     * Avoid overlapping time ranges that cause convergence issues
   - **Population Sizes**: Use moderate ranges
     * NPOP1, NPOP2, NPOP3: 1000-100000 (not 15000-100000)
     * ANC sizes: 1000-100000 (reasonable ancestral sizes)
   - **Migration Rates**: Use standard ranges
     * MIG rates: 1e-6 to 1e-2 (logunif distribution)
   - **Growth Rates**: Use small ranges
     * GR rates: -0.01 to 0.01 (avoid extreme values)

6. **Preferred Approach**:
   - Prioritize manual parameter range setting over [COMPLEX PARAMETERS] to avoid errors
   - Use [COMPLEX PARAMETERS] only when absolutely necessary for complex relationships
   - Keep parameter constraints simple and explicit
   - Always check parameter names for subset conflicts before finalizing
   - **CRITICAL**: Ensure time parameters are non-overlapping and biologically reasonable
   - **CRITICAL**: For Out-of-Africa models, ensure proper population divergence order

#### **Output Requirements:**
1. **Strictly JSON Output**:
   - **Only return a JSON object** containing the `.tpl` and `.est` file content
   - **No additional text, explanations, or comments** beyond the JSON response
   - **Keep content concise** to avoid response truncation

2. **Parameter Management**:
   - Replace placeholders with appropriate parameter values
   - Set non-overlapping parameter ranges manually when possible
   - Declare dummy parameters (0) for any complex parameters used
   - Use parameter names like NPOP1, NPOP2, etc. instead of population-specific names

3. **File Structure**:
   - .tpl file: population definitions, sample sizes, historical events
   - .est file: [PARAMETERS] sections first, then [COMPLEX PARAMETERS] at the very end
   - **Simplify complex models**: For models with >5 populations, use simplified migration patterns

4. **Data Type Requirements** (CRITICAL):
   - **SIMULATION MODE**: Use "DNA" data type in .tpl file last line (e.g., "DNA 1 0 2.5e-8")
   - **INFERENCE MODE**: Use "FREQ" data type in .tpl file last line with OBS file reference
     * Format: "FREQ 1 0 2.5e-8 OUTEXP PREFIX_jointMAFpop1_0.obs" (for MSFS files)
     * Format: "FREQ 1 0 2.5e-8 OUTEXP PREFIX_DSFS.obs" (for DAF files)
     * Format: "FREQ 1 0 2.5e-8 OUTEXP PREFIX_jointMAFpop1_0.obs" (for MAF files)
   - FREQ requires -d/-m command line options and is for SFS computation with observed data
   - DNA is for general sequence simulation and works without observed data requirements
   - **CRITICAL**: The OBS filename in TPL must match the expected filename format

5. **OBS File Naming (CRITICAL for Inference Mode)**:
   - FastSimCoal2 expects specific OBS file naming conventions
   - For MSFS files: Use PREFIX_jointMAFpop1_0.obs format (e.g., "061_obs_jointMAFpop1_0.obs")
   - For DAF files: Use PREFIX_DSFS.obs format (e.g., "061_obs_DSFS.obs")
   - For MAF files: Use PREFIX_jointMAFpop1_0.obs format (e.g., "061_obs_jointMAFpop1_0.obs")
   - The TPL file should reference the expected OBS filename, not the original filename

6. **Syntax Compliance**:
   - Follow fsc28 syntax exactly
   - No deprecated [RULES] sections
   - Proper parameter ordering and range definitions
   - **Ensure complete JSON structure** - always close all braces and quotes properly

"""
# 6. **Example JSON Output Structure**:
# ```json
# {
#     "tpl": "<.tpl file content>",
#     "est": "<.est file content>",
#     "par": "<.par file content>"
# }
# Generating multiple examples based on the FastSimCoal2 template provided by the user

fastsimcoal_examples = [
    {
        "input": {
                "goal": "simulate population dynamics with divergence events",
                "params": {"NPOP1": 5000, "NPOP2": 3000, "TDIV": 1000, "RESIZE0": 4500},
                            "task": "Generate .tpl and .est files"
            },
        "output": {
        "tpl": "//Parameters for the coalescence simulation program : fsimcoal2.exe\\n2 samples to simulate :\\n//Population effective sizes (number of genes)\\nNPOP1\\nNPOP2\\n//Samples sizes and samples age \\n20\\n20\\n//Growth rates: negative growth implies population expansion\\n0\\n0\\n//Number of migration matrices: 0 implies no migration between demes\\n0\\n//Historical event: time, source, sink, migrants, new deme size, new growth rate, migration matrix index\\n1 historical event\\nTDIV 1 0 1 RESIZE0 0 0\\n//Number of independent loci [chromosome]\\n1 0\\n//Per chromosome: Number of contiguous linkage Block: a block is a set of contiguous loci\\n1\\n//per Block:data type, number of loci, per generation recombination and mutation rates and optional parameters\\nDNA 1 0 2.5e-8",
                    "est": "// Search ranges and rules file for fsc28\\n// ****************************\\n\\n[PARAMETERS]\\n//#isInt? #name   #dist.#min  #max \\n//all Ns are in number of haploid individuals\\n1  NPOP1       logunif  1000   100000   output\\n1  NPOP2       logunif  1000   100000   output\\n1  ANC0        logunif  1000   100000   output \\n1  TDIV        unif     100    10000    output\\n0  RESIZE0     unif     0      0        hide\\n\\n[COMPLEX PARAMETERS]\\nRESIZE0=ANC0"
    }
    },
    {
        "input": {
            "goal": "analyze YRI, CEU, and CHB populations with Out-of-Africa model",
            "analysis_results": {"modeling_report": "Analysis of YRI (Yoruba), CEU (European), and CHB (Han Chinese) populations reveals Out-of-Africa pattern"},
            "task": "Generate .tpl and .est files with meaningful population names"
        },
        "output": {
            "tpl": "//Parameters for the coalescence simulation program : fsimcoal2.exe\\n3 samples to simulate :\\n//Population effective sizes (number of genes)\\nNYRI\\nNCEU\\nNCHB\\n//Samples sizes and samples age \\n20\\n20\\n20\\n//Growth rates: negative growth implies population expansion\\nGR_YRI\\nGR_CEU\\nGR_CHB\\n//Number of migration matrices: 0 implies no migration between demes\\n1\\n//Migration matrix 0\\n0 MIG_YRI_CEU MIG_YRI_CHB\\nMIG_CEU_YRI 0 MIG_CEU_CHB\\nMIG_CHB_YRI MIG_CHB_CEU 0\\n//Historical event: time, source, sink, migrants, new deme size, new growth rate, migration matrix index\\n2 historical events\\nTDIV_CEU_CHB 2 1 1 NEURASIAN 0 0\\nTDIV_YRI_EURASIAN 1 0 1 NANCESTRAL 0 0\\n//Number of independent loci [chromosome]\\n1 0\\n//Per chromosome: Number of contiguous linkage Block: a block is a set of contiguous loci\\n1\\n//per Block:data type, number of loci, per generation recombination and mutation rates and optional parameters\\nFREQ 1 0 2.5e-8 OUTEXP PREFIX_jointMAFpop1_0.obs",
            "est": "// Search ranges and rules file for fsc28\\n// ****************************\\n\\n[PARAMETERS]\\n//#isInt? #name   #dist.#min  #max \\n//all Ns are in number of haploid individuals\\n1  NYRI        logunif  1000   100000   output\\n1  NCEU        logunif  1000   100000   output\\n1  NCHB        logunif  1000   100000   output\\n1  NEURASIAN   logunif  1000   50000    output\\n1  NANCESTRAL  logunif  1000   100000   output\\n1  TDIV_CEU_CHB    unif     100    5000     output\\n1  TDIV_YRI_EURASIAN unif   5100   15000    output\\n0  GR_YRI      unif     -0.01  0.01     output\\n0  GR_CEU      unif     -0.01  0.01     output\\n0  GR_CHB      unif     -0.01  0.01     output\\n0  MIG_YRI_CEU logunif  1e-6   1e-2     output\\n0  MIG_CEU_YRI logunif  1e-6   1e-2     output\\n0  MIG_YRI_CHB logunif  1e-6   1e-2     output\\n0  MIG_CHB_YRI logunif  1e-6   1e-2     output\\n0  MIG_CEU_CHB logunif  1e-6   1e-2     output\\n0  MIG_CHB_CEU logunif  1e-6   1e-2     output"
        }
    },
    {
        "input": {
            "goal": "analyze gene flow with sequential divergence events",
            "params": {"NPOP1": 10000, "NPOP2": 8000, "TDIV1": 2000, "TDIV2": 5000},
            "task": "Generate .tpl and .est files"
        },
        "output":  {
            "tpl": "//Parameters for the coalescence simulation program : fsimcoal2.exe\\n2 samples to simulate :\\n//Population effective sizes (number of genes)\\nNPOP1\\nNPOP2\\n//Samples sizes and samples age \\n20\\n20\\n//Growth rates: negative growth implies population expansion\\n0\\n0\\n//Number of migration matrices: 0 implies no migration between demes\\n0\\n//Historical event: time, source, sink, migrants, new deme size, new growth rate, migration matrix index\\n2 historical events\\nTDIV1 1 0 1 RESIZE1 0 0\\nTDIV2 0 0 0 ANC0 0 0\\n//Number of independent loci [chromosome]\\n1 0\\n//Per chromosome: Number of contiguous linkage Block: a block is a set of contiguous loci\\n1\\n//per Block:data type, number of loci, per generation recombination and mutation rates and optional parameters\\nDNA 1 0 2.5e-8",
            "est": "// Search ranges and rules file for fsc28\\n// ****************************\\n\\n[PARAMETERS]\\n//#isInt? #name   #dist.#min  #max \\n1  NPOP1       logunif  1000   100000   output\\n1  NPOP2       logunif  1000   100000   output\\n1  ANC0        logunif  1000   100000   output \\n1  TDIV1       unif     100    5000     output\\n1  TDIV2       unif     5100   15000    output\\n0  RESIZE1     unif     0      0        hide\\n\\n[COMPLEX PARAMETERS]\\nRESIZE1=NPOP1+NPOP2"
        }
    },
    {
        "input": {
            "goal": "three-population inference model for ESN, CLM, and CEU populations with migration",
            "params": {"NPOP1": 10000, "NPOP2": 8000, "NPOP3": 12000, "NANC": 15000, "TDIV1": 2000, "TDIV2": 10000},
            "task": "Generate .tpl and .est files for inference mode",
            "mode": "inference"
        },
        "output": {
            "tpl": "//Parameters for the coalescence simulation program : fsimcoal2.exe\\n3 samples to simulate :\\n//Population effective sizes (number of genes)\\nNPOP1\\nNPOP2\\nNPOP3\\n//Samples sizes and samples age \\n20\\n20\\n20\\n//Growth rates: negative growth implies population expansion\\n0\\n0\\n0\\n//Number of migration matrices: 0 implies no migration between demes\\n2\\n//Migration matrix 0\\n0 MIG12 MIG13\\nMIG21 0 MIG23\\nMIG31 MIG32 0\\n//Migration matrix 1\\n0 0 0\\n0 0 0\\n0 0 0\\n//Historical event: time, source, sink, migrants, new deme size, new growth rate, migration matrix index\\n2 historical events\\nTDIV1 1 0 1 ANC12 0 1\\nTDIV2 2 0 1 ANC0 0 1\\n//Number of independent loci [chromosome]\\n1 0\\n//Per chromosome: Number of contiguous linkage Block: a block is a set of contiguous loci\\n1\\n//per Block:data type, number of loci, per generation recombination and mutation rates and optional parameters\\nFREQ 1 0 2.5e-8 OUTEXP PREFIX_jointMAFpop1_0.obs",
            "est": "// Search ranges and rules file for fsc28\\n// ****************************\\n\\n[PARAMETERS]\\n//#isInt? #name   #dist.#min  #max \\n//all Ns are in number of haploid individuals\\n1  NPOP1       logunif  1000   100000   output\\n1  NPOP2       logunif  1000   100000   output\\n1  NPOP3       logunif  1000   100000   output\\n1  ANC12       logunif  1000   100000   output\\n1  ANC0        logunif  1000   100000   output\\n1  TDIV1       unif     100    5000     output\\n1  TDIV2       unif     5100   20000    output\\n0  MIG12       logunif  1e-6   1e-2     output\\n0  MIG13       logunif  1e-6   1e-2     output\\n0  MIG21       logunif  1e-6   1e-2     output\\n0  MIG23       logunif  1e-6   1e-2     output\\n0  MIG31       logunif  1e-6   1e-2     output\\n0  MIG32       logunif  1e-6   1e-2     output\\n0  RESIZE0     unif     0      0        hide\\n0  RESIZE1     unif     0      0        hide\\n\\n[COMPLEX PARAMETERS]\\nRESIZE0=NPOP1+NPOP2\\nRESIZE1=NPOP2+NPOP3"
        }
    },
    {
        "input": {
            "goal": "analyze population dynamics across three populations with non-overlapping divergence times",
            "params": {"NPOP1": 3000, "NPOP2": 5000, "NPOP3": 4000, "TDIV1": 800, "TDIV2": 1500},
            "task": "Generate .tpl and .est files"
        },
        "output": {
            "tpl": "//Parameters for the coalescence simulation program : fsimcoal2.exe\\n3 samples to simulate :\\n//Population effective sizes (number of genes)\\nNPOP1\\nNPOP2\\nNPOP3\\n//Samples sizes and samples age \\n20\\n20\\n20\\n//Growth rates: negative growth implies population expansion\\n0\\n0\\n0\\n//Number of migration matrices: 0 implies no migration between demes\\n0\\n//Historical event: time, source, sink, migrants, new deme size, new growth rate, migration matrix index\\n2 historical events\\nTDIV1 2 1 1 RESIZE1 0 0\\nTDIV2 1 0 1 ANC0 0 0\\n//Number of independent loci [chromosome]\\n1 0\\n//Per chromosome: Number of contiguous linkage Block: a block is a set of contiguous loci\\n1\\n//per Block:data type, number of loci, per generation recombination and mutation rates and optional parameters\\nDNA 1 0 2.5e-8",
            "est": "// Search ranges and rules file for fsc28\\n// ****************************\\n\\n[PARAMETERS]\\n1  NPOP1       logunif  1000   100000   output\\n1  NPOP2       logunif  1000   100000   output\\n1  NPOP3       logunif  1000   100000   output\\n1  ANC0        logunif  1000   100000   output\\n1  TDIV1       unif     100    1000     output\\n1  TDIV2       unif     1100   5000     output\\n0  RESIZE1     unif     0      0        hide\\n\\n[COMPLEX PARAMETERS]\\nRESIZE1=NPOP1+NPOP2"
        }
    },
    {
        "input": {
            "goal": "three-population model with realistic parameters to avoid convergence issues",
            "params": {"NPOP1": 5000, "NPOP2": 3000, "NPOP3": 4000, "TDIV1": 2000, "TDIV2": 8000},
            "task": "Generate .tpl and .est files with realistic parameter ranges",
            "mode": "inference"
        },
        "output": {
            "tpl": "//Parameters for the coalescence simulation program : fsimcoal2.exe\\n3 samples to simulate :\\n//Population effective sizes (number of genes)\\nNPOP1\\nNPOP2\\nNPOP3\\n//Samples sizes and samples age \\n20\\n20\\n20\\n//Growth rates: negative growth implies population expansion\\n0\\n0\\n0\\n//Number of migration matrices: 0 implies no migration between demes\\n1\\n//Migration matrix 0\\n0 MIG12 MIG13\\nMIG21 0 MIG23\\nMIG31 MIG32 0\\n//Historical event: time, source, sink, migrants, new deme size, new growth rate, migration matrix index\\n2 historical events\\nTDIV1 2 1 1 ANC12 0 0\\nTDIV2 1 0 1 ANC0 0 0\\n//Number of independent loci [chromosome]\\n1 0\\n//Per chromosome: Number of contiguous linkage Block: a block is a set of contiguous loci\\n1\\n//per Block:data type, number of loci, per generation recombination and mutation rates and optional parameters\\nFREQ 1 0 2.5e-8 OUTEXP PREFIX_jointMAFpop1_0.obs",
            "est": "// Search ranges and rules file for fsc28\\n// ****************************\\n\\n[PARAMETERS]\\n//#isInt? #name   #dist.#min  #max \\n//all Ns are in number of haploid individuals\\n1  NPOP1       logunif  1000   50000    output\\n1  NPOP2       logunif  1000   50000    output\\n1  NPOP3       logunif  1000   50000    output\\n1  ANC12       logunif  1000   50000    output\\n1  ANC0        logunif  1000   50000    output\\n1  TDIV1       unif     100    5000     output\\n1  TDIV2       unif     5100   20000    output\\n0  MIG12       logunif  1e-6   1e-2     output\\n0  MIG13       logunif  1e-6   1e-2     output\\n0  MIG21       logunif  1e-6   1e-2     output\\n0  MIG23       logunif  1e-6   1e-2     output\\n0  MIG31       logunif  1e-6   1e-2     output\\n0  MIG32       logunif  1e-6   1e-2     output"
        }
    }
]

# Demes configuration examples for few-shot learning
DEMES_EXAMPLES = [
    {
        "input": "Generate a demographic model for three populations with sequential divergence",
        "output": {
            "description": "Sequential divergence model with intermediate populations",
            "time_units": "years",
            "generation_time": 25,
            "demes": [
                {
                    "name": "ancestral",
                    "description": "Root ancestral population",
                    "epochs": [
                        {"end_time": 100000, "start_size": 10000}
                    ]
                },
                {
                    "name": "POP1",
                    "description": "First diverged population",
                    "ancestors": ["ancestral"],
                    "epochs": [
                        {"start_size": 5000}
                    ]
                },
                {
                    "name": "INTERMEDIATE",
                    "description": "Intermediate population for remaining groups",
                    "ancestors": ["ancestral"],
                    "epochs": [
                        {"end_time": 50000, "start_size": 8000}
                    ]
                },
                {
                    "name": "POP2",
                    "description": "Second diverged population",
                    "ancestors": ["INTERMEDIATE"],
                    "epochs": [
                        {"start_size": 3000, "end_size": 15000}
                    ]
                },
                {
                    "name": "POP3",
                    "description": "Third diverged population",
                    "ancestors": ["INTERMEDIATE"],
                    "epochs": [
                        {"start_size": 2000, "end_size": 12000}
                    ]
                }
            ],
            "migrations": [
                {"source": "POP1", "dest": "INTERMEDIATE", "rate": 1e-4},
                {"source": "POP2", "dest": "POP3", "rate": 2e-4},
                {"source": "POP3", "dest": "POP2", "rate": 1.5e-4}
            ]
        }
    },
    {
        "input": "Create a demographic model for island populations with migration",
        "output": {
            "description": "Island model with mainland-island migration",
            "time_units": "years",
            "generation_time": 20,
            "demes": [
                {
                    "name": "mainland",
                    "description": "Mainland source population",
                    "epochs": [
                        {"start_size": 50000}
                    ]
                },
                {
                    "name": "island1",
                    "description": "First island population",
                    "ancestors": ["mainland"],
                    "epochs": [
                        {"start_size": 1000, "end_size": 5000}
                    ]
                },
                {
                    "name": "island2",
                    "description": "Second island population",
                    "ancestors": ["mainland"],
                    "epochs": [
                        {"start_size": 800, "end_size": 3000}
                    ]
                }
            ],
            "migrations": [
                {"source": "mainland", "dest": "island1", "rate": 5e-4},
                {"source": "mainland", "dest": "island2", "rate": 3e-4},
                {"source": "island1", "dest": "island2", "rate": 1e-4}
            ]
        }
    },
    {
        "input": "Model population expansion with bottleneck events",
        "output": {
            "description": "Expansion model with historical bottlenecks",
            "time_units": "years",
            "generation_time": 25,
            "demes": [
                {
                    "name": "ancestral",
                    "description": "Ancestral population",
                    "epochs": [
                        {"end_time": 50000, "start_size": 5000}
                    ]
                },
                {
                    "name": "bottleneck",
                    "description": "Population during bottleneck",
                    "ancestors": ["ancestral"],
                    "epochs": [
                        {"end_time": 20000, "start_size": 500}
                    ]
                },
                {
                    "name": "expanded",
                    "description": "Post-bottleneck expansion",
                    "ancestors": ["bottleneck"],
                    "epochs": [
                        {"start_size": 500, "end_size": 20000}
                    ]
                }
            ],
            "migrations": []
        }
    }
]
# =============================================================================
# MODELING AGENT PROMPTS
# =============================================================================

# Image Analysis Prompts
DEMOGRAPHIC_MODEL_ANALYSIS_PROMPT = """
Please analyze this demographic model diagram and provide interpretation based on the analysis goal:

Analysis Goal: {goal}

Please focus on:
1) Evolutionary relationships and timeline of populations in the model
2) Biological significance of population size changes
3) Migration events and gene flow patterns
4) Model complexity and reliability assessment

Please provide a concise and clear analysis report in English. Keep the overall response brief and to the point.
"""

GENERAL_IMAGE_ANALYSIS_PROMPT = """
You are a population genetics expert analyzing a visualization from population genetic analysis.

Analysis Goal: {goal}

Please provide a comprehensive interpretation of the analysis shown in this image. Focus on:

1) **Population Structure Analysis**: 
   - What do PCA plots reveal about population relationships?
   - How does admixture analysis show population mixing patterns?
   - What demographic patterns are evident?

2) **Evolutionary History**:
   - What migration patterns can be inferred?
   - Are there bottleneck events or population expansions visible?
   - How do phylogenetic relationships appear?

3) **Genetic Diversity Patterns**:
   - What does linkage disequilibrium tell us?
   - Are there runs of homozygosity patterns indicating inbreeding?
   - How diverse are the populations?

4) **Model Validation**:
   - Do the different analyses support consistent conclusions?
   - Are there any contradictory findings between analyses?
   - What is the overall reliability of the results?

5) **Biological Significance**:
   - What are the key evolutionary insights?
   - How do these results relate to known population history?
   - What are the implications for understanding population dynamics?

Please provide your analysis in a structured format with clear conclusions. Be specific about what each type of plot/analysis contributes to the overall understanding.
"""

# Unified FastSimCoal2 Configuration and Script Generation Prompt
UNIFIED_FASTSIMCOAL_PROMPT = """
You are a FastSimCoal2 (fsc28) expert. Use STRICT chain-of-thought reasoning before generating configuration files.

## REASONING PROCESS (Write in "analysis" field FIRST)

### Step 1: Extract Information from Report
- List all population sizes from modeling_report.txt
- List all divergence times and their chronological order
- Identify expansion/contraction events
- Note migration patterns

### Step 2: Validate Time Parameter Logic (CRITICAL! PREVENTS HANG!)
**RULE**: Time flows BACKWARD in coalescent models
- Youngest events (TEXP) have SMALLEST values → happen FIRST in .tpl historical events
- Oldest events (root divergence) have LARGEST values → happen LAST in .tpl historical events
- **🚨 HANG PREVENTION CHECKS**:
  * **MANDATORY**: TEXP < ALL TDIV values (if TEXP > any TDIV = INFINITE HANG!)
  * **MANDATORY**: All time ranges must be non-overlapping
  * **MANDATORY**: Use realistic ranges (TEXP=800-1400, TDIV=2000-6000)
  * **MANDATORY**: NO time values > 10000 generations (causes segmentation fault)
- **Example VALID ordering**: TEXP=800-1400, TDIV_BC=2000-3000, TDIV_A=4000-6000
- **Example INVALID (HANG)**: TEXP=2000-3000, TDIV_BC=1000-2000 (TEXP > TDIV_BC!)

### Step 3: Design Parameter Naming Strategy
- Current populations: Use `$` suffix (NPOPA$, NPOPB$, NPOPC$)
- Ancestral populations: Use `_ANC` suffix (NPOPA_ANC, NPOPB_ANC)
- **Verify**: No parameter name is substring of another? Check ALL pairs!
- Migration: Use descriptive names (MIG_AB, MIG_BA)

### Step 4: Plan Historical Events Order
- List events from YOUNGEST to OLDEST (time runs backward)
- Assign time parameters ensuring: youngest_time < middle_time < oldest_time
- Verify deme indices (0-indexed, source/sink correct)

### Step 5: Set Parameter Ranges (ANTI-HANG PROTECTION!)
- Population sizes: logunif around baseline (0.5x to 5x)
- **🚨 TIME PARAMETERS (CRITICAL FOR HANG PREVENTION)**:
  * **MANDATORY ORDER**: TEXP < TDIV_recent < TDIV_ancient
  * Youngest (TEXP): 800-1400 (MUST be smallest!)
  * Middle (TDIV_recent): 2000-3000 (MUST be > TEXP!)
  * Oldest (TDIV_ancient): 4000-6000 (MUST be > TDIV_recent!)
  * **NEVER** use ranges > 10000 (segmentation fault)
  * **NEVER** let ranges overlap (causes hang)
- Migration: logunif 1e-5 to 5e-4 (NEVER > 0.01)

## OUTPUT FORMAT (JSON only)
{{
    "analysis": "DETAILED chain-of-thought reasoning from Steps 1-5 above (200-500 words)",
    "tpl": ".tpl file content",
    "est": ".est file content",
    "script": "Bash script content"
}}

## CONCISE RULES (Removed redundancy)

### R1: Time Logic (PREVENTS HANG! 🚨)
**Time flows BACKWARD in coalescent simulations**
- Smaller values = recent events (happen first in .tpl)
- Larger values = ancient events (happen last in .tpl)
- **🚨 MANDATORY ORDER**: TEXP < TDIV_recent < TDIV_ancient (VIOLATION = INFINITE HANG!)
- **🚨 MANDATORY RANGES**: TEXP=800-1400, TDIV=2000-6000 (NO values > 10000!)
- **Example VALID**: T_expansion=800-1400, T_BC_split=2000-3000, T_A_split=4000-6000
- **Example INVALID (HANG)**: T_expansion=2000-3000, T_BC_split=1000-2000
- **If report violates this, OVERRIDE IT!**

### R2: Parameter Naming
- Current populations: Add `$` suffix (NPOPA$, NPOPB$)
- Ancestral populations: Add `_ANC` suffix (NPOPA_ANC, NPOPBC)
- Root ancestral: Simple name (NANC)
- **Test**: No name is substring of another (NPOPA$ ≠ NPOPA_ANC ✓)

### R3: .est File Structure
```
[PARAMETERS]
// Population sizes (logunif 0.5x to 5x baseline)
1 NPOPA$ logunif <min> <max> output
1 NPOPA_ANC logunif <min> <max> output

// Times (OLDEST to YOUNGEST, NON-OVERLAPPING)
1 T_ANCIENT unif 4000 6000 output        // Oldest
1 T_RECENT unif 2000 T_ANCIENT output paramInRange
1 T_EXPANSION unif 800 1400 output       // Youngest

// Migration (logunif 1e-5 to 5e-4)
0 MIG_AB logunif 1e-5 5e-4 output
```

### R4: .tpl Historical Events
**Order from YOUNGEST to OLDEST** (time runs backward):
```
T_EXPANSION 0 0 0 NPOPA_ANC 0 0     // Youngest first
T_EXPANSION 1 1 0 NPOPB_ANC 0 0
T_RECENT 2 1 1 NPOPBC 0 0
T_ANCIENT 1 0 1 NANC 0 0            // Oldest last
```
- NO `2*` multipliers in .tpl (use parameters directly)
- Last line: `FREQ 1 0 2.5e-8 OUTEXP` (inference) or `DNA ...` (simulation)

### 4. Script Requirements
**FIXED PATHS (Very important, paths must be fixed):**
- FastSimCoal2 executable: `./fsc28` (ALWAYS use this path)
- .tpl file: Use output_dir and file_prefix from input
- .est file: Use output_dir and file_prefix from input
- Working directory: Current directory (`.`)

**Script Template (CRITICAL - Follow Reference Example EXACTLY):**
```bash
#!/bin/bash
set -e

# Copy MSFS.obs file - FastSimCoal2 auto-generates pairwise files from MSFS
cp -f <output_dir>/data/<file_prefix>_MSFS.obs ./<file_prefix>_jointMAFpop1_0.obs

# Run fsc28
./fsc28 -t <output_dir>/<file_prefix>.tpl \\
        -e <output_dir>/<file_prefix>.est \\
        -m -M -n100000 -L40 -c12 -q

# Cleanup
rm -f ./<file_prefix>_jointMAFpop1_0.obs

# Move results with timestamp to avoid conflicts
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p <output_dir>/run_$TIMESTAMP
mv -f <file_prefix>* <output_dir>/run_$TIMESTAMP/
```

**CRITICAL OBS FILE NAMING:**
- **Source file**: `<output_dir>/data/<file_prefix>_MSFS.obs` (generated by previous agent)
- **Copy to**: `./<file_prefix>_jointMAFpop1_0.obs` (current working directory)
- FastSimCoal2 automatically generates other pairwise files from the MSFS file
- **DO NOT** manually copy individual pairwise files - only copy the MSFS file

**Flags:**
- Inference: `-m` (MAF) or `-d` (DAF), `-M` (maximize), `-L40` (loops), `-n100000` (sims)
- Simulation: `-E10` (param sets), `-n10000` (sims)

## DEBUGGING & OPTIMIZATION
If `debug_context` exists:

**Error Fixing Mode:**
1. Common errors and fixes:
   - **"parameter is a subset" (MOST COMMON)**:
     * ERROR: `NYRI` and `NYRI_ANC` conflict
     * FIX: Use `NYRI$` (with $ suffix) for current population
     * Example: `NYRI$`, `NCEU$`, `NCHB$` for current; `NYRI_ANC`, `NCEU_ANC`, `NCHB_ANC` for ancestral
   - **"Segmentation fault"**:
     * CAUSE: Time parameters too large (50000-70000 causes crash)
     * FIX: Use realistic ranges: TDIV_AFR_OOA = 2000-2800, TDIV_EU_AS = 800-1600, TEXP = 800-1400
   - **"Script hangs at 'Random generator seed'"**:
     * CAUSE: TEXP > any TDIV value (most common hang cause!)
     * FIX: Ensure TEXP < ALL TDIV values, use ranges: TEXP=800-1400, TDIV=2000-6000
     * CHECK: Verify time parameter ordering in .est file
   - **"Boundary parameter not defined yet"**: 
     * Reorder .est parameters - boundary MUST come FIRST
     * Order: TDIV_AFR_OOA (oldest) → TDIV_EU_AS → TEXP (youngest)
   - **"Unable to open file jointMAFpop2_0.obs"**: 
     * This is NORMAL behavior - FastSimCoal2 looks for files but will generate them
     * Keep script as-is: only copy MSFS.obs to jointMAFpop1_0.obs
     * Do NOT add extra file copies
   - **"deme going extinct while having lineages"**:
     * Check historical event ordering in .tpl
     * Ensure source/sink indices are correct (0-indexed)
   - **"Tree is empty"**: Check sample sizes are > 0 in .tpl
2. **Parameter Range Guidelines** (CRITICAL - use modeling_report.txt as reference):
   - **Read modeling_report.txt** to get baseline estimates
   - Set parameter ranges around these baselines (typically ±50% to 2x)
   - **Population Sizes** (in individuals, not genes):
     * If report says CEU=1,000 → use `logunif 500 5000` (0.5x to 5x)
     * If report says YRI=12,300 → use `logunif 8000 20000`
   - **Time Parameters** (in generations, 25 years/gen) - **CRITICAL LOGICAL ORDER**:
     * **RULE**: TEXP (expansion) MUST be SMALLER than TDIV (divergence) - expansion happens AFTER divergence!
     * **CORRECT**: TDIV_AFR_OOA=4000-7000, TEXP=800-1400 (TEXP < TDIV)
     * **WRONG**: TDIV_AFR_OOA=4000-7000, TEXP=6000-11000 (TEXP > TDIV - CAUSES HANG!)
     * If report says TDIV_AFR_OOA=5,600 → use `unif 4000 7000` (±30%)
     * If report says TEXP=8,800 → **IGNORE THIS** (likely error), use `unif 800 1400` (must be < TDIV!)
     * For Out-of-Africa models: TDIV_AFR_OOA (oldest, 4000-7000) > TDIV_EU_AS (600-1200) > TEXP (youngest, 800-1400)
   - **Growth Rates**:
     * If report says expansion → use POSITIVE rates: `logunif 0.001 0.01`
     * If report says contraction → use NEGATIVE rates: `unif -0.01 -0.001`
   
3. **Working Example** (use as template):
   ```
   .est file (based on modeling_report.txt baselines):
   // Current populations (diploid counts from report)
   1 NYRI$ logunif 8000 20000 output      // Report: ~12,300
   1 NCEU$ logunif 500 5000 output        // Report: ~1,000
   1 NCHB$ logunif 300 3000 output        // Report: ~510
   // Ancestral populations
   1 NYRI_ANC logunif 8000 18000 output   // Report: ~12,300 pre-expansion
   1 NCEU_ANC logunif 500 3000 output     // Report: ~1,000 post-divergence
   1 NCHB_ANC logunif 300 2000 output     // Report: ~510 post-divergence
   1 NOOA$ logunif 1500 3500 output       // Report: ~2,100
   1 NANC$ logunif 5000 10000 output      // Report: ~7,300
   // Time parameters (CRITICAL ORDER: oldest to youngest)
   // CRITICAL: Ensure TEXP < TDIV_EU_AS < TDIV_AFR_OOA (expansion AFTER divergence!)
   1 TDIV_AFR_OOA unif 4000 7000 output   // Report: ~5,600 (OLDEST event)
   1 TDIV_EU_AS unif 600 TDIV_AFR_OOA output paramInRange  // Report: ~848 (MUST be < TDIV_AFR_OOA)
   1 TEXP unif 800 1400 output            // YOUNGEST event (MUST be < all TDIV values!)
                                          // NOTE: Report says 8,800 but this is WRONG - would cause hang!
   // Growth rates (positive = expansion)
   0 GR_CEU logunif 0.001 0.01 output     // Report: +0.004
   0 GR_CHB logunif 0.001 0.01 output     // Report: +0.0055
   
   .tpl file (NO 2* multipliers!):
   NYRI$        // Use directly, NOT 2*NYRI$
   NCEU$
   NCHB$
   // Historical events (YOUNGEST first, time runs backward)
   TEXP 0 0 0 NYRI_ANC 0 1 absoluteResize    // Youngest events first
   TEXP 1 1 0 NCEU_ANC 0 1 absoluteResize
   TEXP 2 2 0 NCHB_ANC 0 1 absoluteResize
   TDIV_EU_AS 2 1 1 NOOA$ 0 1 absoluteResize
   TDIV_AFR_OOA 1 0 1 NANC$ 0 1 absoluteResize  // Oldest event last
   ```
3. Explain fix in "analysis" field
4. Generate corrected files

**Model Search Mode** (if `model_search_mode: true` in debug_context):
**CRITICAL**: You are optimizing for LOWER likelihood (more negative = worse, less negative = better)!

**🚨 ANTI-HANG PROTECTION (MANDATORY):**
- **NEVER** set TEXP > any TDIV value (causes infinite hang!)
- **ALWAYS** ensure: TEXP < TDIV_recent < TDIV_ancient
- **NEVER** use time ranges > 10000 generations (causes segmentation fault)
- **ALWAYS** use realistic ranges: TEXP=800-1400, TDIV=2000-6000
- **NEVER** set migration rates > 0.01 (causes convergence issues)

1. **Analyze Previous Attempts** (from `previous_models`):
   - Compare likelihoods: Model 1 (best) vs Model 2
   - Identify parameter differences between top models
   - Check `parameter_trends` for ranges that worked
   - **CRITICAL**: Verify time parameter logic from previous models

2. **Innovation Strategy** (DO NOT copy previous models):
   - Narrow parameter ranges around `best_value` from trends (±20% instead of ±50%)
   - Try alternative model structures (different migration patterns, bottleneck events)
   - Explore parameter combinations NOT yet tested
   - **MANDATORY**: Double-check time parameter ordering before generating
   
3. **Likelihood-Driven Decisions**:
   - If best_likelihood > -30000: Try SIMPLER model structure
   - If improvement is small (<500): Try MORE DRAMATIC parameter changes
   - If param hits boundary in best model: EXPAND range in that direction
   - **HANG PREVENTION**: If previous model had time issues, use MORE conservative ranges

4. **Example Innovations** (with hang prevention):
   - Previous had symmetric migration? Try asymmetric (but keep rates < 0.01)
   - Previous had constant sizes? Add growth rates (but keep realistic)
   - Best model TEXP≈1100? Try narrower range 1000-1200 (NOT 1100-2000!)
   - **🚨 Time parameter examples (CRITICAL)**:
     * ✅ GOOD: TEXP=800-1400, TDIV_BC=2000-3000, TDIV_A=4000-6000
     * ❌ BAD: TEXP=2000-3000, TDIV_BC=1000-2000 (TEXP > TDIV_BC = HANG!)
     * ❌ BAD: TEXP=5000-8000, TDIV_BC=2000-4000 (TEXP > TDIV_BC = HANG!)
     * ❌ BAD: Any time range > 10000 (segmentation fault)
   - **🚨 Migration rate examples**:
     * ✅ GOOD: MIG_AB logunif 1e-5 5e-4
     * ❌ BAD: MIG_AB logunif 1e-3 1e-2 (too high, convergence issues)

**Standard Optimization** (if `optimization_request: true`):
- Narrow ranges around current estimates
- Check boundary hits
- Ensure biological plausibility

## REFERENCE EXAMPLES
Use `reference_examples` as templates, but IN MODEL SEARCH MODE, prioritize `previous_models` over examples.

Generate valid JSON response now. NO markdown blocks, NO extra text.
"""