'''
initiate
gathers compliant SBOM from desired AMI and
invokes list_instances to validate compliance of all servers against compliant SBOM
'''

import os
import json
import time
import logging
from datetime import datetime

from threading import Thread

from utils.helpers import ( get_client,
    check_instance_status,
    get_instance_inventory,
    terminate_instance,
    publish_event,
    check_association_status)

default_log_args = {
    "level": logging.INFO,
    "format": "%(asctime)s [%(levelname)s] %(filename)s-%(lineno)d %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S",
    "force": True,
}

logging.basicConfig(**default_log_args)
log = logging.getLogger()


def lambda_handler(event, context):
    '''Initializing lambda handler'''
    del context
    log.info(f"Event - {json.dumps(event, default=str)}")

    # gather details to create a server
    sg_id = os.environ.get('SG_ID','')
    subnet_id = os.environ.get('SUBNET_ID', '')
    iam_profile_arn = os.environ.get('IAM_PROFILE_ARN', '')

    scan_type = event.get('SCAN_TYPE','n-1')

    app = CompliantServer(sg_id, subnet_id, iam_profile_arn, scan_type)
    app.run()

    return {
        'statusCode' : 200,
        'message' : 'captured inventory for compliant server successfully'
    }


class CompliantServer():
    '''Creates compliant server based on the AMI configuration and
    fetches the inventory for said server'''

    def __init__(self, sg_id, subnet_id, iam_profile_arn, scan_type):
        self.sg_id = sg_id
        self.subnet_id = subnet_id
        self.iam_profile_arn = iam_profile_arn

        self.scan_type = scan_type
        self.scan_time = datetime.now()
        self.instance_details = {}

    def run(self):
        '''orchestrate the application'''
        thread_list = []
        # ami_ids = []
        ec2 = get_client('ec2')
        ssm = get_client('ssm')
        events = get_client('events')

        image_details = [
            {
                "image_name": "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server*",
                "image_owner": "099720109477"
            },
            {
                "image_name": "ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server*",
                "image_owner": "099720109477"
            },
            {
                "image_name": "ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server*",
                "image_owner": "099720109477"
            },
            {
                "image_name": "amzn-ami-hvm-2018.03*",
                "image_owner": "137112412989"
            },
            {
                "image_name": "amzn2-ami-hvm-2.0*",
                "image_owner": "137112412989"
            }
        ]

        for image in image_details:
            image_id = self.get_second_latest_ami(ec2, image['image_name'], image['image_owner'])
            log.info(f"Ami Id for {image['image_name']} - {image_id}")
            # ami_ids.append(image_id)
            # for ami_id in ami_ids:
            thread = Thread(target=self.get_compliant_inventory, args=(image_id, ec2, ssm, ))
            thread.start()
            thread_list.append(thread)

        for thread in thread_list:
            thread.join()

        if not self.instance_details:
            log.info("No complaint details captured. Exiting...")
            return

        for instance in self.instance_details.values():
            instance['ScanType'] = self.scan_type
            instance['ScanTime'] = self.scan_time

        with open('accounts.json', 'r', encoding='utf8') as file:
            account_list = json.loads(file.read())

        for account in account_list['account_detail']:
            entries = []
            compliant_event ={
                'instance_details' : self.instance_details,
                'account_details' : account
            }

            entry = {
                'Time': datetime.now(),
                'Source': 'patchInspect',
                'Detail': json.dumps(compliant_event, default=str),
                'DetailType': 'listInstances',
                'EventBusName': 'default'
            }
            entries.append(entry)

            publish_event(entries, events)
            log.info(f"Published instance details for account - {account['Name']}")


    def get_compliant_inventory(self, ami_id, ec2, ssm):
        '''creates compliant server and returns once SSM is up'''
        instance_detail = self.create_compliant_instance(ami_id, ec2, ssm)
        log.info("Created the compliant server with the specified AMI. \
            Sleeping for 5 seconds before fetching inventory...")
        time.sleep(5)

        complaint_inventory = get_instance_inventory(instance_detail['InstanceId'], ssm)

        complaint_packages = {}
        for app_entry in complaint_inventory['Entries']:
            app_name = app_entry['Name']
            complaint_packages[app_name] = app_entry['Version']

        terminate_instance(instance_detail['InstanceId'], ec2)
        instance_detail['ComplaintPackages'] = complaint_packages

        # put_dynamo_db_item(PATCH_INSPECT_TABLE_NAME, complaint_inventory, dynamodb)
        # log.info(f"Created an item for compliant server in table {PATCH_INSPECT_TABLE_NAME}.")

        self.instance_details[instance_detail['InstanceId']] = instance_detail

    def create_compliant_instance(self, ami_id, ec2, ssm):
        '''creates a EC2 instance using n-1 AMI of the OS'''

        response = ec2.run_instances(
            ImageId=ami_id,
            InstanceType='t2.micro',
            MaxCount=1,
            MinCount=1,
            Monitoring={
                'Enabled': False
            },
            SecurityGroupIds=[
                self.sg_id,
            ],
            SubnetId=self.subnet_id,
            IamInstanceProfile={
                'Arn': self.iam_profile_arn
            },
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'patchInspect-compliant-server'
                        }
                    ]
                }
            ],
            MetadataOptions= {
                'HttpTokens': 'required'
            }
        )

        instance_id = response['Instances'][0]['InstanceId']
        log.info(f"Created EC2 Instance {instance_id}. \
        Sleeping for 30 seconds before checking SSM status")

        # waiting for 30 to boot up the server
        time.sleep(30)
        while True:
            if (status := check_instance_status(instance_id, ssm)) is None:
                log.info("Instance Ping Status in SSM is not 'Online'. Sleeping for 30 seconds")
                time.sleep(30)
                continue
            if check_association_status(instance_id, ssm):
                return status

    def get_second_latest_ami(self, ec2, image_name, image_owner):
        '''returns desired AMI Id for the specified image configurations'''
        response = ec2.describe_images(
            Filters=[
                {
                    'Name': 'architecture',
                    'Values': [
                        'x86_64',
                    ]
                },
                {
                    'Name': 'virtualization-type',
                    'Values': [
                        'hvm',
                    ]
                },
                {
                    'Name': 'image-type',
                    'Values': [
                        'machine',
                    ]
                },
                {
                    'Name': 'root-device-type',
                    'Values': [
                        'ebs',
                    ]
                },
                {
                    'Name': 'block-device-mapping.volume-type',
                    'Values': [
                        'gp2',
                    ]
                },
                {
                    'Name': 'name',
                    'Values': [
                        image_name,
                    ]
                },
                {
                    'Name': 'owner-id',
                    'Values': [
                        image_owner,
                    ]
                }
            ]
        )

        today = datetime.now()

        desired = int(self.scan_type[-1])
        days_list = []

        for image in response['Images']:
            diff = (today - datetime.strptime(image['CreationDate'], "%Y-%m-%dT%H:%M:%S.%fZ")).days
            days_list.append(diff)
            image['diff'] = diff

        desired_image = ""

        days_list.sort()
        for image in response['Images']:
            if image['diff'] == days_list[desired]:
                desired_image = image['ImageId']
                break
        return desired_image
