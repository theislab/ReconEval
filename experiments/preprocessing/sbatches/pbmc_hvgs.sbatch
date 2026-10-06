#!/bin/bash
 
#SBATCH -o /home/icb/egor.antipov/ReconEval/experiments/preprocessing/sbatches/outputs/session_%j.out
#SBATCH -e /home/icb/egor.antipov/ReconEval/experiments/preprocessing/sbatches/outputs/session_%j.err
#SBATCH -J python
#SBATCH -p cpu_p
#SBATCH --qos cpu_normal
#SBATCH --mem 800G
#SBATCH --time=12:00:00
#SBATCH --cpus-per-task=20
#SBATCH --nice=0
 
source /home/icb/egor.antipov/miniconda3/bin/activate
conda activate scaling-transformers

python -u /home/icb/egor.antipov/ReconEval/experiments/preprocessing/pbmc_hvgs.py
