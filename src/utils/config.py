'''
config.py
To store hardcoded values used in the solution
'''

import os

QUEUE_URL = os.environ.get('QUEUE_URL','')
ROLE_NAME = os.environ.get('ROLE_NAME', '')
PATCH_INSPECT_S3_BUCKET = os.environ.get('PATCH_INSPECT_S3_BUCKET', '')
PATCH_INSPECT_TABLE_NAME = os.environ.get('PATCH_INSPECT_TABLE_NAME', '')

REGION_USED = ['ap-south-1', 'ap-southeast-1', 'us-east-1','us-east-2']
