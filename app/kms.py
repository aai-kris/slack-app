import boto3
from botocore.exceptions import ClientError

def get_secret():

    SECRET_NAME = "prod/nexalith"
    REGION_NAME = "eu-west-2"

    # # Create a Secrets Manager client
    # session = boto3.session.Session(
    #     aws_access_key_id=AWS_ACCESS_KEY_ID,
    #     aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    #     region_name=REGION_NAME,
    # )

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=REGION_NAME
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=SECRET_NAME
        )
    except ClientError as e:
        raise e

    secret = get_secret_value_response['SecretString']

    print(secret)

    # # Get the secret data
    # if 'SecretString' in response:
    #     return json.loads(response['SecretString'])
    # else:
    #     return json.loads(response['SecretBinary'].decode('utf-8'))









# import os
# import boto3
# import json
#
# def get_aws_secrets():
#     AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
#     AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
#     SECRET_NAME = "inocul8-dev-database"
#     REGION_NAME = "eu-west-2"
#
#     # Create a Secrets Manager client
#     session = boto3.session.Session(
#         aws_access_key_id=AWS_ACCESS_KEY_ID,
#         aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#         region_name=REGION_NAME,
#     )
#     client = session.client(
#         service_name='secretsmanager'
#     )
#
#     # Get the secret value
#     response = client.get_secret_value(
#         SecretId=SECRET_NAME
#     )
#
#     # Get the secret data
#     if 'SecretString' in response:
#         return json.loads(response['SecretString'])
#         # secret_data = json.loads(response['SecretString'])
#     else:
#         return json.loads(response['SecretBinary'].decode('utf-8'))
#         # secret_data = json.loads(response['SecretBinary'].decode('utf-8'))