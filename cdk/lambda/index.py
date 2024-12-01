import os
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['API_KEYS_TABLE'])

def handler(event, context):
    api_key = event['authorizationToken']
    
    try:
        response = table.get_item(Key={'api_key': api_key})
        if 'Item' in response:
            return generate_policy('Allow', event['methodArn'])
        else:
            return generate_policy('Deny', event['methodArn'])
    except:
        return generate_policy('Deny', event['methodArn'])

def generate_policy(effect, resource):
    return {
        'principalId': 'user',
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }