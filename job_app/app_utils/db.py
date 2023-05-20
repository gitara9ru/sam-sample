import boto3
import datetime
from app_utils import lambda_app_logger


TABLE_NAME = "UserApiUsage"
DB_EXPIRATION_KEY = "expiredAt"

logger = lambda_app_logger.get_logger()


def setExpiration(user_id, expiration_at: datetime.datetime):
    dynamodb = boto3.client("dynamodb")

    logger.info("Request query user records to DB", extra={"user_id": user_id})

    # user_idが'hoge'のレコードを取得
    response = dynamodb.query(
        TableName=TABLE_NAME,
        KeyConditionExpression="userId = :user_id",
        ExpressionAttributeValues={":user_id": {"S": user_id}},
    )
    logger.info(
        "Response from request query user records to DB",
        extra={
            "response": len(response.get("Items", [])),
        },
    )

    # BatchWriteItemリクエスト用のPutRequestを作成
    put_requests = []
    for item in response["Items"]:
        put_requests.append(
            {
                "PutRequest": {
                    "Item": {
                        **item,
                        **{DB_EXPIRATION_KEY: {"S": expiration_at.isoformat()}},
                    }
                }
            }
        )

    # バッチでレコードを書き込む
    if put_requests:
        logger.info(
            "Request ttl put records to DB",
            extra={
                "items": len(put_requests),
            },
        )
        response = dynamodb.batch_write_item(RequestItems={TABLE_NAME: put_requests})
        logger.info(
            "Response from requet ttl put records to DB",
            extra={
                "response": response["ResponseMetadata"],
            },
        )


def removeExpiration(user_id):
    # DynamoDBクライアントを取得
    dynamodb = boto3.client("dynamodb")

    # user_idが'hoge'のレコードを取得
    response = dynamodb.query(
        TableName=TABLE_NAME,
        KeyConditionExpression="userId = :user_id",
        ExpressionAttributeValues={":user_id": {"S": user_id}},
    )

    # BatchWriteItemリクエスト用のPutRequestを作成
    put_requests = []
    for item in response["Items"]:
        item_without_expiration = {
            key: value for key, value in item.items() if key != DB_EXPIRATION_KEY
        }
        put_requests.append({"PutRequest": {"Item": item_without_expiration}})

    # バッチでレコードを書き込む
    if put_requests:
        logger.info(
            "Request put ttl-cancel records to DB",
            extra={"items": len(put_requests)},
        )
        response = dynamodb.batch_write_item(RequestItems={TABLE_NAME: put_requests})
        logger.info(
            "Response from request put ttl-cancel records to DB",
            extra={"response": response["ResponseMetadata"]},
        )


def getLatestRecord(user_id):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    logger.info(
        "Request query latest user record to DB",
        extra={"user_id": user_id},
    )
    # クエリ実行
    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("userId").eq(user_id),
        ScanIndexForward=False,  # 降順で結果を取得
        Limit=1,  # 最新の1件のみ取得
    )

    logger.info(
        "Reponse from request query latest user record to DB",
        extra={"response": len(response.get("Items", []))},
    )
    if response["Items"]:
        raw_latest_record = response["Items"][0]
        latest_record = {
            "userId": raw_latest_record["userId"],
            "resetAt": datetime.datetime.fromisoformat(raw_latest_record["resetAt"]),
            "updatedAt": datetime.datetime.fromisoformat(
                raw_latest_record["updatedAt"]
            ),
            "usage": int(raw_latest_record["usage"]),
        }
        return latest_record


def updateRecord(
    user_id, reset_at: datetime.datetime, updated_at: datetime.datetime, usage
):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    item = {
        "userId": user_id,
        "resetAt": reset_at.isoformat(),
        "updatedAt": updated_at.isoformat(),
        "usage": usage,
    }
    logger.info(
        "Request put record to DB",
        extra={"user_id": item["userId"], "resetAt": item["resetAt"]},
    )
    response = table.put_item(Item=item)
    logger.info(
        "Response from put record to DB",
        extra={"response": response["ResponseMetadata"]},
    )
    return response["ResponseMetadata"]["HTTPStatusCode"] == 200
