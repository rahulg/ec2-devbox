import boto3
import os

from typing import List, Dict


def amzn_tag(ec2, resources: List[str], tag: str):
    ec2.create_tags(
        Resources=resources,
        Tags=[{
            'Key': 'purpose',
            'Value': tag,
        }],
    )


def amzn_get_tag(tags: List[Dict[str, str]], tag: str) -> str:
    for o in tags:
        if o['Key'] == tag:
            return o['Value']


devbox_filter = {
    'Name': 'tag:purpose',
    'Values': ['devbox'],
}


def attach_vol(ec2, instance_id: str, datavol_id: str):
    response = ec2.describe_instances(
        InstanceIds=[instance_id],
    )
    sir_id = response['Reservations'][0]['Instances'][0]['SpotInstanceRequestId']

    response = ec2.describe_spot_instance_requests(
        SpotInstanceRequestIds=[sir_id],
    )
    sir_tag_purpose = amzn_get_tag(response['SpotInstanceRequests'][0]['Tags'], 'purpose')
    amzn_tag(ec2, [instance_id], sir_tag_purpose)

    if sir_tag_purpose == 'devbox':
        ec2.attach_volume(
            Device='/dev/xvdb',
            InstanceId=instance_id,
            VolumeId=os.environ['L_DATAVOL_ID'],
        )


def handler(event, context):
    ec2 = boto3.client('ec2')
    instance_id = event['detail']['instance-id']
    attach_vol(ec2, instance_id, os.environ['L_DATAVOL_ID'])
