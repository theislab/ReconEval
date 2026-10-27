.. _slurm-parameters:

Run through Slurm (optional)
----------------------------

:doc:`Back to introduction <../custom_datasets>`

Use these steps to submit any task's Python command as a cluster job.
Complete the data and configuration steps for your task first.
Skip this section for direct Python runs.

1. Create a ``.sbatch`` file starting with ``#!/bin/bash``, using a script
   from ``experiments/*/submit/`` as a reference. Set the ``#SBATCH``
   options for your cluster and workload: partition/account, time limit,
   CPUs, memory, and GPUs if needed. Existing resource requests were
   chosen for the benchmark datasets

2. Set the output and error log paths in the script, for example:

   .. code-block:: bash

      #SBATCH --output=logs/slurm/%x-%j.out
      #SBATCH --error=logs/slurm/%x-%j.err

   Place all ``#SBATCH`` directives before shell commands. Here ``%x``
   is the job name and ``%j`` is the job ID

3. Initialize Conda, activate the environment specified in your task's
   CLI instructions, and change to the repository directory:

   .. code-block:: bash

      source /path/to/miniforge3/etc/profile.d/conda.sh
      conda activate your-task-environment
      cd /path/to/ReconEval

   Replace the paths and environment name with your local setup

4. Add the complete Python command from your task's CLI section:
   :ref:`End-to-end <custom-data-e2e-cli>`,
   :ref:`Foundation model <custom-data-mlp-cli>`,
   :ref:`STATE <custom-data-state-cli>`, or
   :ref:`CellFlow <custom-data-cellflow-cli>`.
   Set your input paths, output directory, and model options there.
   When adapting an existing submission script, replace its training
   command with your own

5. Create the log directory **before** submission and submit from the
   repository root:

   .. code-block:: bash

      cd /path/to/ReconEval
      mkdir -p logs/slurm
      sbatch /path/to/train_mydata.sbatch

   Adjust the log directory to match your ``#SBATCH`` paths. The log
   files contain the job's standard output and errors; model outputs
   are saved at the locations described in each task's **Outputs** section

If you retain an existing script's environment-variable options, export
only variables that the script reads and submit with ``sbatch --export=ALL``.
Other settings belong in the Python command inside the script.
