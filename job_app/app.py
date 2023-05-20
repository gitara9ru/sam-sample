import json
import urllib.request
import boto3
import datetime
from app_utils import db
from app_utils import lambda_app_logger
from app_utils import config
import os

logger = lambda_app_logger.get_logger()
# 使用量のカウント期間
USAGE_RESET_DAYS = 1
# 退会時からレコード削除までの日数
UNFOLLOWED_EXPIRATION_DAYS = 30


def get_api_key(key):
    client = boto3.client("secretsmanager")
    secret_name = "appeal-ai/{}".format(config.STAGE)
    response = client.get_secret_value(SecretId=secret_name)
    secret = response["SecretString"]
    return json.loads(secret)[key]


def get_parameter_from_store(parameter_name):
    prefix = "/appeal-ai/{}".format(config.STAGE)
    full_parameter_name = "{}/{}".format(prefix, parameter_name)
    ssm_client = boto3.client("ssm")
    response = ssm_client.get_parameter(Name=full_parameter_name, WithDecryption=True)
    return response["Parameter"]["Value"]


LINE_CHANNEL_ACCESS_TOKEN_KEY = "LINE_CHANNEL_ACCESS_TOKEN"
LINE_CHANNEL_ACCESS_TOKEN = get_api_key(LINE_CHANNEL_ACCESS_TOKEN_KEY)
REPLY_REQUEST_URL = "https://api.line.me/v2/bot/message/reply"
PUSH_REQUEST_URL = "https://api.line.me/v2/bot/message/push"
REQUEST_HEADERS = {
    "Authorization": "Bearer " + LINE_CHANNEL_ACCESS_TOKEN,
    "Content-Type": "application/json",
}
MAX_COUNT = int(get_parameter_from_store("LINEBOT_MAX_COUNT"))


def getProfileText(profile, request_id):
    functionName = os.environ["PROFILE_TEXT_FUNCTION_ARN"]
    lambda_client = boto3.client("lambda", region_name="ap-northeast-1")
    request_payload = {
        "body": json.dumps({"profile": profile}, ensure_ascii=False),
        "caller_id": request_id,
    }
    logger.info(
        "Request to text Lambda",
        extra={
            "payload": lambda_app_logger.mask_private_data(request_payload["body"]),
            "function_name": functionName,
        },
    )
    invoke_result = lambda_client.invoke(
        FunctionName=functionName,
        InvocationType="RequestResponse",
        Payload=json.dumps(request_payload, ensure_ascii=False),
    )
    response_payload = json.loads(invoke_result["Payload"].read())
    logger.info(
        "Response from request to text Lambda",
        extra={
            "status": invoke_result["StatusCode"],
            "function_name": functionName,
        },
    )

    response = json.loads(response_payload["body"])
    return response["new_profile"]


def getProfileImg(user_id, profile, request_id):
    lambda_client = boto3.client("lambda", region_name="ap-northeast-1")
    functionName = os.environ["PROFILE_IMG_FUNCTION_ARN"]
    request_payload = {
        "body": json.dumps(
            {"profile": profile, "user_id": user_id}, ensure_ascii=False
        ),
        "caller_id": request_id,
    }
    logger.info(
        "Request to img Lambda",
        extra={
            "payload": lambda_app_logger.mask_private_data(request_payload["body"]),
            "function_name": functionName,
        },
    )
    invocation_result = lambda_client.invoke(
        FunctionName=functionName,
        InvocationType="RequestResponse",
        Payload=json.dumps(
            request_payload,
            ensure_ascii=False,
        ),
    )
    response_payload = json.loads(invocation_result["Payload"].read())

    response = json.loads(response_payload["body"])
    logger.info(
        "Response from request to img Lambda",
        extra={
            "status": invocation_result["StatusCode"],
            "function_name": functionName,
        },
    )
    return response["img_url"]


def sendMessages(url, reply_params):
    request = urllib.request.Request(
        url,
        json.dumps(reply_params).encode("utf-8"),
        method="POST",
        headers=REQUEST_HEADERS,
    )
    logger.info(
        "Request to LINE Messaging API",
        extra={
            "request_url": url,
            "method": "POST",
        },
    )
    with urllib.request.urlopen(request) as response:
        response_body = response.read().decode("utf-8")
        # レスポンスヘッダーの取得
        xLineRequestId = response.getheader("x-line-request-id")

        status_code = response.getcode()

        logger.info(
            "Response From request to LINE Messaging API",
            extra={
                "status_code": status_code,
                "x_line_request_id": xLineRequestId,
            },
        )


def updateUsage(user_id, latest_record=None):
    now = datetime.datetime.now()
    if latest_record is not None and latest_record["resetAt"] >= now:
        reset_at = latest_record["resetAt"]
        updated_at = now
        usage = latest_record["usage"] + 1
        db.updateRecord(user_id, reset_at, updated_at, usage)
        return
    reset_at = now + datetime.timedelta(days=USAGE_RESET_DAYS)
    db.updateRecord(user_id, reset_at, now, 1)


# 処理したプロファイル数を返す
def process_line_event(line_event, request_id):
    userId = line_event["source"]["userId"]
    # 友達追加
    if line_event["type"] == "follow":
        follow_message = """私は超ポジティブなAIだよ!
君のどんなメッセージも、かっこいいキャッチコピーとイラストにしてみせるよ!
"""
        params = {
            "to": line_event["source"]["userId"],
            "replyToken": line_event["replyToken"],
            "messages": [{"text": follow_message, "type": "text"}],
        }
        # レコードの削除予定があれば取り消し
        db.removeExpiration(userId)
        sendMessages(REPLY_REQUEST_URL, params)
        return 0

    if line_event["type"] == "unfollow":
        # 退会時の処理
        expired_at = datetime.datetime.now() + datetime.timedelta(
            days=UNFOLLOWED_EXPIRATION_DAYS
        )
        db.setExpiration(userId, expired_at)
        return 0

    if line_event["type"] == "message":
        latest_record = db.getLatestRecord(userId)
        usage = latest_record["usage"] if latest_record is not None else 0
        if usage >= MAX_COUNT:
            message = "今日はここまで!次の機会をお楽しみに"
            sendMessages(
                REPLY_REQUEST_URL,
                {
                    "to": userId,
                    "replyToken": line_event["replyToken"],
                    "messages": [{"text": message, "type": "text"}],
                },
            )
            return 0
        new_profile = getProfileText(line_event["message"]["text"], request_id)
        text_params = {
            "to": userId,
            "replyToken": line_event["replyToken"],
            "messages": [
                {"text": new_profile, "type": "text"},
                {"text": "次はプロフィール画像を作るので30秒待ってて!", "type": "text"},
            ],
        }

        sendMessages(REPLY_REQUEST_URL, text_params)
        img_url = getProfileImg(userId, new_profile, request_id)
        img_params = {
            "to": userId,
            "messages": [
                {
                    "type": "image",
                    "originalContentUrl": img_url,
                    "previewImageUrl": img_url,
                }
            ],
        }
        sendMessages(PUSH_REQUEST_URL, img_params)
        updateUsage(userId, latest_record)
        return 1
    return 0


IS_LOGGING_EVENT = config.is_stage_dev()


@logger.inject_lambda_context(log_event=IS_LOGGING_EVENT)
def lambda_handler(event, context):
    body = json.loads(event["body"])
    line_event = body["line_event"]
    request_id = context.aws_request_id
    count = process_line_event(line_event, request_id)

    response = {
        "statusCode": 200,
        "body": json.dumps({"count": count}, ensure_ascii=False),
    }
    logger.info(
        "Response to client",
        extra={"response": response},
    )
    return response
