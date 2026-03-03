# Ensure dorado model is installed before calling dorado basecaller
pod5dir=$1 
ref=$2
out=$3
# Adjust according to actual dorado path
../dorado-0.9.1-linux-x64/bin/dorado basecaller hac,5mCG_5hmCG --models-directory ./model/ $pod5dir --reference $ref > $out