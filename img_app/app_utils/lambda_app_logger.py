from aws_lambda_powertools import Logger
from app_utils import config
import base64


def get_logger():
    level = "DEBUG" if config.is_stage_dev() else "INFO"
    logger = Logger(
        service="img_app", level=level, location="%(module)s.%(funcName)s:%(lineno)d"
    )
    return logger


def mask_private_data(data):
    return base64.b64encode(data.encode("utf-8"))
