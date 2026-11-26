# DocVQA v29.7

The four optimizer modules load the local prompt resources. The Preconditioner uses the v29.7 design; Diagnosis, Editor and Replay use the prompts archived with the parent_memory_delta_v1 v29.6 run.

Use `scripts/runs/run_v29_7_campaign.py` with `experiments/configs/v29_7_docvqa_optimization160.json`. Train and final Test use separate commands and directories. See the [offline acceptance record](../../../docs/methods/v29_7/IMPLEMENTATION.md).
