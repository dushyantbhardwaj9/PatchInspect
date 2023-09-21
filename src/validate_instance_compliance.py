'''
validate_instance_compliance
validates if all packages of an server are patch compliant
'''

import json
import logging

from datetime import datetime
from debian.debian_support import version_compare as vc

from utils.helpers import (publish_event, get_client,
    get_instance_inventory, sanitize_iventory)

default_log_args = {
    "level": logging.INFO,
    "format": "%(asctime)s [%(levelname)s] %(filename)s-%(lineno)d %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S",
    "force": True,
}

logging.basicConfig(**default_log_args)
log = logging.getLogger()


def lambda_handler(event, context):
    '''lambda handlers to compare instance inventory with compliant instance inventory'''
    del context
    log.info(f"event - {json.dumps(event, default=str)}")

    body_0 = event['Records'][0]['body']
    account_id = body_0['AccountId']
    region = body_0['Region']

    events = get_client('events')

    first_record = True
    for message in event['Records']:
        entries = []
        body = json.loads(message['body'])

        if not(account_id == body['AccountId'] and region == body['Region']) or first_record:
            account_id = body['AccountId']
            region = body['Region']
            ssm = get_client('ssm', region, account_id)
            first_record = False

        log.info(f"Initializing patch compliance for instance Id - {body['InstanceId']}")

        complaint_packages = body.get('ComplaintPackages')

        instance_inventory = get_instance_inventory(body['InstanceId'], ssm)

        if instance_inventory['Entries'] == []:
            instance_inventory['CompliancePercentage'] = 0
        else:
            # Compare packages versions with compliant versions
            count_packages = 0
            total_packages = 0
            for entry in instance_inventory['Entries']:
                if entry['Name'] in complaint_packages:
                    total_packages += 1
                    entry['CompliantVersion'] = complaint_packages[entry['Name']]
                    res = vc(complaint_packages[entry['Name']], entry['Version'])
                    if res > 0: # pylint: disable=consider-using-assignment-expr
                        # compliant package version in greater
                        entry['Compliant'] = False
                    else:
                        # compliant package version in lower or same
                        entry['Compliant'] = True
                        count_packages += 1
            if count_packages == 0:
                instance_inventory['CompliancePercentage'] = 0
            else:
                instance_inventory['CompliancePercentage'] = \
                    int(round(count_packages*100/total_packages, 2))

        instance_inventory = sanitize_iventory(instance_inventory, body)
        log.info(f"Instance({instance_inventory['InstanceId']})patch \
            compliance %age - {instance_inventory['CompliancePercentage']}")

        entry = {
            'Time': datetime.now(),
            'Source': 'patchInspect',
            'Detail': json.dumps(instance_inventory, default=str),
            'DetailType': 'findings',
            'EventBusName': 'default'
        }

        entries.append(entry)
        publish_event(entries, events)

    return {
        'statusCode' : 200,
        'Message' : 'Completed successfully'
    }
