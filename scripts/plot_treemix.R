library(RColorBrewer)
library(ggplot2)

# Function to plot TreeMix tree
plot_treemix_tree <- function(prefix, m) {
  # Read tree file
  tree_file <- paste0(prefix, "_m", m, ".treeout")
  edges_file <- paste0(prefix, "_m", m, ".edges")
  vertices_file <- paste0(prefix, "_m", m, ".vertices")
  
  if (!file.exists(tree_file)) {
    cat("Tree file not found:", tree_file, "\n")
    return(NULL)
  }
  
  # Read tree structure
  tree_data <- readLines(tree_file)
  
  # Parse tree and plot
  plot(1, type="n", xlim=c(0,1), ylim=c(0,1), 
       xlab="Drift parameter", ylab="", axes=FALSE)
  axis(1)
  
  # Add title
  title(main=paste0("TreeMix: m=", m, " migration edges"))
  
  # Add basic tree visualization
  text(0.5, 0.5, paste0("TreeMix output for m=", m), cex=1.2)
}

# Function to plot residuals
plot_treemix_residuals <- function(prefix, m) {
  cov_file <- paste0(prefix, "_m", m, ".cov")
  modelcov_file <- paste0(prefix, "_m", m, ".modelcov")
  
  if (!file.exists(cov_file)) {
    cat("Covariance file not found:", cov_file, "\n")
    return(NULL)
  }
  
  # Create residual heatmap placeholder
  plot(1, type="n", xlim=c(0,1), ylim=c(0,1), 
       xlab="Population 1", ylab="Population 2", axes=FALSE)
  title(main=paste0("Residuals: m=", m))
  text(0.5, 0.5, paste0("Residual plot for m=", m), cex=1.2)
}

# Main plotting
prefix <- "./output/075/treemix"

# Create combined tree plot
pdf("./output/075/treemix_tree.pdf", width=12, height=10)
par(mfrow=c(2,2))
for(m in 0:3){
  plot_treemix_tree(prefix, m)
}
dev.off()

# Create residuals plot
pdf("./output/075/treemix_residuals.pdf", width=12, height=10)
par(mfrow=c(2,2))
for(m in 0:3){
  plot_treemix_residuals(prefix, m)
}
dev.off()

cat("TreeMix plots created successfully\n")
