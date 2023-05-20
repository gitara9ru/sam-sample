import json
import boto3
from app_utils import lambda_app_logger,config
import os

logger = lambda_app_logger.get_logger()

IS_LOGGING_EVENT = config.is_stage_dev()

@logger.inject_lambda_context(log_event=IS_LOGGING_EVENT)
def lambda_handler(event, context):
    function_name = os.environ["PROFILE_JOB_FUNCTION_ARN"]
    event_body = json.loads(event["body"])

    lambda_client = boto3.client('lambda', region_name='ap-northeast-1')
    for message_event in event_body['events']:
        # メッセージイベントごとにLambda関数を非同期で呼び出す
        lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='Event',
            Payload=json.dumps({
                "body": json.dumps({
                    "line_event": message_event
                }, ensure_ascii=False),
            }, ensure_ascii=False)
        )


    return {
        'statusCode': 200,
        'body': json.dumps('All Line Message Tasks Submit')
    }
