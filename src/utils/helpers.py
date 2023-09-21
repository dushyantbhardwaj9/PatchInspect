'''
helpers.py
Contain helper functions
'''

import os
import json
import time
import uuid
import logging
from random import randrange

import boto3
from botocore.exceptions import ClientError

from utils.config import ROLE_NAME

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

def check_instance_status(instance_id, ssm):
    '''return True when the instance in available'''
    response = ssm.describe_instance_information(
        Filters=[
            {
                'Key': 'InstanceIds',
                'Values': [
                    instance_id
                ]
            },
            {
                'Key': 'PingStatus',
                'Values': [
                    'Online'
                ]
            }
        ]
    )

    if len(response['InstanceInformationList']) < 1:
        return None

    instance_details = {
        'InstanceId' : instance_id,
        'PlatformType' : response['InstanceInformationList'][0]['PlatformType'],
        'PlatformName' : response['InstanceInformationList'][0]['PlatformName'],
        'PlatformVersion' : response['InstanceInformationList'][0]['PlatformVersion'] ,
    }
    return instance_details


def check_association_status(instance_id, ssm):
    '''check association status for gather software inventory status'''
    while True:

        response = ssm.describe_instance_associations_status(
            InstanceId=instance_id
        )
        # log.info(f"describe_instance_associations_status - {json.dumps(response, default=str)}")
        for association in response['InstanceAssociationStatusInfos']:
            if association['Name'] == "AWS-GatherSoftwareInventory" and \
                 association['Status'] == "Success":
                return True

        log.info("Association status is not 'Success' for AWS-GatherSoftwareInventory. \
             Sleeping for 30 seconds")
        time.sleep(30)
        continue

    return True

def get_instance_inventory(instance_id, ssm):
    '''return instance inventory information from ssm'''
    inventory = []
    inventory_type = "AWS:Application"
    try:
        response = ssm.list_inventory_entries(
            InstanceId=instance_id,
            TypeName=inventory_type,
        )

        inventory = response

        while 'NextToken' in response:
            response = ssm.list_inventory_entries(
                InstanceId=instance_id,
                TypeName=inventory_type,
                NextToken=response['NextToken']
            )
            inventory['Entries'].extend(response['Entries'])
    except ClientError as err:
        if err.response['Error']['Code'] == "ThrottlingException":
            sleep_sec = randrange(10)
            log.error(f'Error fetching inventory. Sleeping for {sleep_sec} seconds.')
            time.sleep(sleep_sec)
            return get_instance_inventory(instance_id, ssm)

    return inventory

def sanitize_iventory(instance_inventory, body):
    '''Santizing instance inventory'''
    instance_inventory['Region'] = body.get('Region','-')
    instance_inventory['AccountId'] = body.get('AccountId','-')
    instance_inventory['AccountName'] = body.get('AccountName','-')
    instance_inventory['PlatformName'] = body.get('PlatformName','-')
    instance_inventory['PlatformVersion'] = body.get('PlatformVersion','-')
    instance_inventory['ScanType'] = body.get('ScanType','-')
    instance_inventory['ScanTime'] = body.get('ScanTime','-')

    if 'NextToken' in instance_inventory:
        del instance_inventory['NextToken']
    if 'ResponseMetadata' in instance_inventory:
        del instance_inventory['ResponseMetadata']
    if 'SchemaVersion' in instance_inventory:
        del instance_inventory['SchemaVersion']
    if 'Entries' in instance_inventory:
        del instance_inventory['Entries']
    if 'CaptureTime' in instance_inventory:
        del instance_inventory['CaptureTime']

    return instance_inventory

def terminate_instance(instance_id, ec2):
    '''terminate the given instance'''

    ec2.terminate_instances(
        InstanceIds=[
            instance_id,
        ]
    )


def publish_sqs_message(sqs, queue_url, data):
    '''publish given message to patch compliance SQS queue'''

    sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(data, default=str),
        DelaySeconds=randrange(30)
    )


def publish_event(entry, events=None):
    '''publish event to evenrbridge'''

    response = events.put_events(
        Entries= entry
    )
    log.info("event published on eventbridge ")

    if response['FailedEntryCount'] < 1:
        log.info('put_events - success')
    else:
        log.info(f'put_events - error - {response}')


def get_client(service, region_name=None, account_id = None):
    '''
    creates service client for given service, region and account
    '''
    session  = _get_session(region_name, account_id)
    client = session.client(service)

    return client

def get_resource(service, region_name=None, account_id = None):
    '''
    creates resource service client for given service, region and account
    '''
    session  = _get_session(region_name, account_id)
    resource = session.resource(
        service_name = service)

    return resource


def _get_current_account_region():
    '''return default account and region'''
    client = boto3.client('sts')
    account_id = client.get_caller_identity()['Account']
    region = os.environ['AWS_REGION']

    return account_id, region

def _get_session(region_name=None, account_id = None):
    '''
    creates boto3 session for specified account and region
    '''
    default_account, default_region = _get_current_account_region()
    if region_name is None:
        region_name = default_region

    if account_id is None:
        account_id = default_account

    role_client = boto3.client('sts')
    role_arn_val = 'arn:aws:iam::' + \
        account_id + ':role/' + ROLE_NAME

    response = role_client.assume_role(
        RoleArn=role_arn_val,
        RoleSessionName=f"security-automation-{uuid.uuid4()}")

    session = boto3.Session(
        aws_access_key_id=response['Credentials']['AccessKeyId'],
        aws_secret_access_key=response['Credentials']['SecretAccessKey'],
        aws_session_token=response['Credentials']['SessionToken'],
        region_name = region_name)

    return session

def put_dynamo_db_item(table_name, data, dynamodb = None):
    '''put item to given DynamoDB table

    put_dynamo_db_item(TABLE_NAME, data)
    '''
    if dynamodb is None:
        dynamodb = get_resource('dynamodb')
    table = dynamodb.Table(table_name)

    table.put_item(
        Item=data
    )
