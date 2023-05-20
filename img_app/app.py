import json
from app_utils import make_img
import boto3
import os
from app_utils import lambda_app_logger, config

logger = lambda_app_logger.get_logger()


def get_api_key(key):
    client = boto3.client("secretsmanager")
    secret_name = "appeal-ai/{}".format(config.STAGE)
    response = client.get_secret_value(SecretId=secret_name)
    secret = response["SecretString"]
    return json.loads(secret)[key]


api_key = get_api_key("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = api_key


# 環境変数の設定設定
os.environ["OPENAI_API_KEY"] = get_api_key("OPENAI_API_KEY")
os.environ["STABILITY_HOST"] = "grpc.stability.ai:443"
os.environ["STABILITY_KEY"] = get_api_key("STABILITY_API_KEY")

IS_LOGGING_EVENT = config.is_stage_dev()


@logger.inject_lambda_context(log_event=IS_LOGGING_EVENT)
def lambda_handler(event, context):
    logger.info(
        "Request from client", extra={"caller_id": event.get("caller_id", None)}
    )
    body = json.loads(event["body"])
    raw_profile = body["profile"]
    user_id = body["user_id"]

    img_result = make_img.make_img(user_id, raw_profile)

    response = {
        "statusCode": 200,
        "body": json.dumps(img_result, ensure_ascii=False),
    }
    logger.info(
        "Response to client",
        extra={"response": response},
    )
    return response


# event = {
#     "body": json.dumps(
#         {"profile": "私は、東京都に住んでいる、20代の女性です。", "user_id": "hogehogeuser"},
#         ensure_ascii=False,
#     )
# }
# lambda_handler(event, {})
