import json
from app_utils import make_catchcopy
from app_utils import lambda_app_logger
from app_utils import config
import boto3
import os

logger = lambda_app_logger.get_logger()


def get_api_key(key):
    client = boto3.client("secretsmanager")
    secret_name = "appeal-ai/{}".format(config.STAGE)
    response = client.get_secret_value(SecretId=secret_name)
    secret = response["SecretString"]
    return json.loads(secret)[key]


api_key = get_api_key("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = api_key


IS_LOGGING_EVENT = config.is_stage_dev()

@logger.inject_lambda_context(log_event=IS_LOGGING_EVENT)
def lambda_handler(event, context):
    logger.info("Request from client", extra={"caller_id": event.get("caller_id", None)})
    body = json.loads(event["body"])
    raw_profile = body["profile"]
    new_profile = make_catchcopy.make_catchcopy(raw_profile)

    response = {
        "statusCode": 200,
        "body": json.dumps({"new_profile": new_profile}, ensure_ascii=False),
    }
    logger.info(
        "Response to client",
        extra={"response": response},
    )
    return response


# profile = """
# 今日もプログラムのバグのせいでシステム障害になってしまった。私って本当にだめ
# """
# result = lambda_handler(
#     {"body": json.dumps({"profile": profile}, ensure_ascii=False)}, ""
# )
