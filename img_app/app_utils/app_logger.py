import logging
from pythonjsonlogger import jsonlogger


# json形式でログ出力
def get_logger(name):
    log_handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        json_ensure_ascii=False,
    )
    log_handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)
    return logger
