# Ensure dorado model is installed before calling dorado basecaller
pod5dir=$1 
out=$2
# Adjust according to actual dorado path
../dorado-0.9.1-linux-x64/bin/dorado basecaller hac --models-directory ./model/ $pod5dir > $out