import os

STAGE = os.environ.get("STAGE", "dev")

def is_stage_dev():
    return STAGE == "dev"