'''
list_instances
gathers list of all instances in a account across all regions
'''

import json
import time
import logging

from threading import Thread
# from concurrent.futures import ThreadPoolExecutor
from botocore.exceptions import ClientError

from utils.config import QUEUE_URL, REGION_USED
from utils.helpers import (publish_sqs_message,
    get_client)

default_log_args = {
    "level": logging.INFO,
    "format": "%(asctime)s [%(levelname)s] %(filename)s-%(lineno)d %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S",
    "force": True,
}

logging.basicConfig(**default_log_args)
log = logging.getLogger()


def lambda_handler(event, context):
    '''initialize lambda function'''
    del context
    log.info(f"Event - {json.dumps(event, default=str)}")

    account_details =    event.get('detail').get('account_details')
    compliant_server = event.get('detail').get('instance_details')

    if len(event['detail']) < 1:
        return {
            'statusCode': 500,
            'message': 'No Compliant Instance available'
        }

    app = ListInstances(account_details = account_details, compliant_server = compliant_server)
    app.run()

    return {
            'statusCode': 500,
            'message': 'Successfully initiated PatchInspect'
        }

class ListInstances():
    '''Loops over regions to create threads for listing instances in an account'''
    def __init__(self, account_details, compliant_server):
        self.account_details = account_details
        self.compliant_server = compliant_server
        self.instance_details = []

    def run(self):
        '''orchestrator function for ListInstances'''
        sqs = get_client('sqs')
        thread_list = []

        for region in REGION_USED:
            account_id = self.account_details['Id']
            account_name = self.account_details['Name']

            app = PublishInstanceDetails(account_id, account_name, region, \
                self.compliant_server, sqs)
            thread = Thread(target=app.run)
            thread.start()
            thread_list.append(thread)
            time.sleep(2)
        time.sleep(30)
        for thread in thread_list:
            thread.join()

class PublishInstanceDetails:
    ''' list servers for given account and region. Filters out desired servers and publishes them'''
    def __init__(self, account_id, account_name, region, compliant_server, sqs):
        self.account_id = account_id
        self.account_name = account_name
        self.region = region

        self.ssm = get_client('ssm', region, account_id)
        self.sqs = sqs

        self.compliant_server = compliant_server
        self.instance_details = None

    def run(self):
        '''orchestrator function for PublishInstanceDetails'''
        self.instance_details = self.list_all_ec2_instances(self.ssm)
        if len(self.instance_details) == 0:
            return
        self.publish_relevant_platforms(self.sqs, self.region, self.account_id, self.account_name)
        return

    def list_all_ec2_instances(self, ssm):
        '''list all ec2 instances that have SSM status is online'''
        try:
            instances_list = []
            response = ssm.describe_instance_information(
                Filters=[
                    {
                        'Key': 'PingStatus',
                        'Values': [
                            'Online'
                        ]
                    }
                ]
            )
            instances_list.extend(response['InstanceInformationList'])

            while 'NextToken' in response:
                response = ssm.describe_instance_information(
                    Filters=[
                        {
                            'Key': 'PingStatus',
                            'Values': [
                                'Online'
                            ]
                        }
                    ],
                    NextToken = response['NextToken']
                )
                instances_list.extend(response['InstanceInformationList'])
        except ClientError as err:
            time.sleep(5)
            log.info(f"Error: {err}")
            return self.list_all_ec2_instances(ssm)

        instance_details = []
        for instance in instances_list:
            detail = {
                'InstanceId' : instance.get('InstanceId','-'),
                'PlatformName' : instance.get('PlatformName','-'),
                'PlatformVersion' : instance.get('PlatformVersion','-'),
                'Name' : instance.get('Name','-')
            }

            instance_details.append(detail)

        return instance_details

    def publish_relevant_platforms(self, sqs, region, account_id, account_name):
        '''compare platform details and publish instance details and compliant packages'''
        count = 0
        for compliant_instance in self.compliant_server.values():
            for instance in self.instance_details:

                if instance['PlatformName'] == compliant_instance['PlatformName'] and \
                    instance['PlatformVersion'] == compliant_instance['PlatformVersion']:

                    instance['Region'] = region
                    instance['AccountId'] = account_id
                    instance['AccountName'] = account_name
                    instance['ComplaintPackages'] = compliant_instance['ComplaintPackages']
                    instance['ScanType'] = compliant_instance['ScanType']
                    instance['ScanTime'] = compliant_instance['ScanTime']

                    publish_sqs_message(sqs, QUEUE_URL, instance)
                    count += 1

        log.info(f"{count} instance details were published to SQS \
            for account {account_id} and region {region}")
