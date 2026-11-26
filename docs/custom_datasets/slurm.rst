.. _slurm-parameters:

Slurm
-----

:doc:`Back to introduction <../custom_datasets>`

Skip this section for a direct Python run.

Finish the data and configuration steps first.

Submit a task as a cluster job.

**Follow the steps below:**

1. **Resources**

   Create a ``.sbatch`` file starting with ``#!/bin/bash``.
   Set ``#SBATCH`` for your cluster: partition, account, time, CPUs, memory, and GPUs.

2. **Logs**

   .. code-block:: bash

      #SBATCH --output=logs/slurm/%x-%j.out
      #SBATCH --error=logs/slurm/%x-%j.err

   Put every ``#SBATCH`` line before any shell command.
   ``%x`` is the job name. ``%j`` is the job ID.

3. **Environment**

   .. code-block:: bash

      source /path/to/miniforge3/etc/profile.d/conda.sh
      conda activate your-task-environment
      cd /path/to/ReconEval

   Replace the paths and environment name with your local setup.

4. **Command**

   - **Experiments**

     - Instructions: :doc:`advanced usage <advanced_usage>`
     - Code examples: ``experiments/*/submit/``

   - **Demo**

     - Instructions: :doc:`examples <examples>`
     - Code examples: ``custom_datasets_demo/*/submit/``

5. **Submit**

   .. code-block:: bash

      cd /path/to/ReconEval
      mkdir -p logs/slurm
      sbatch /path/to/run_job.sbatch

   Create the log directory before ``sbatch``.
   Results are saved where the task's **Outputs** section says.

If the script reads environment variables, submit with ``sbatch --export=ALL``.
Other settings belong in the Python command.
