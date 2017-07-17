import base64
import boto3
import datetime
import json
import os

from typing import List


def amzn_tag(ec2, resources: List[str], tag: str):
    ec2.create_tags(
        Resources=resources,
        Tags=[{
            'Key': 'purpose',
            'Value': tag,
        }],
    )


devbox_filter = {
    'Name': 'tag:purpose',
    'Values': ['devbox'],
}


user_data = '''#!/bin/bash
set -eu

sdate() {{ date -d "$1" +%s; }}

ami_date=$(cat /var/lib/ami-date)
ami_date_s=$(sdate "$ami_date")

now_date=$(date +%Y-%m-%d)
now_date_s=$(sdate "$now_date")

if [[ $now_date_s -eq $ami_date_s ]]; then
    # we've run and updated once today
    halt
fi

pacman --noconfirm -Syu
pacman --noconfirm -Scc

echo $now_date >/var/lib/ami-date
aws --region {region} lambda invoke --function-name {func} /tmp/awscli-out
'''


def latest_image(ec2):
    response = ec2.describe_images(
        Owners=['self'],
        Filters=[devbox_filter],
    )

    images = sorted(
        response['Images'],
        key=lambda img: datetime.datetime.strptime(img['CreationDate'], '%Y-%m-%dT%H:%M:%S.%fZ'),
    )
    image_id = images[-1]['ImageId']

    return image_id


def request_node(ec2, tag: str) -> str:

    launch_spec = {
        'ImageId': latest_image(ec2),
        'InstanceType': os.environ['L_INSTANCE_TYPE'],
        'NetworkInterfaces': [
            {
                'DeviceIndex': 0,
                'NetworkInterfaceId': os.environ['L_NETIF_ID'],
            },
        ],
        'Placement': {
            'AvailabilityZone': os.environ['L_AZ'],
        },
        'KeyName': os.environ['L_KEY_NAME'],
        'IamInstanceProfile': {
            'Arn': os.environ['L_IAM_PROFILE_ARN'],
        },
        'UserData': base64.standard_b64encode(user_data.format(
            region=os.environ['L_REGION'],
            func=os.environ['L_LAMBDA_AMI_FUNC'],
        ).encode('utf-8')).decode('utf-8'),
    }

    response = ec2.request_spot_instances(
        LaunchSpecification=launch_spec,
        SpotPrice=os.environ['L_MAX_PRICE'],
        ValidUntil=datetime.datetime.now() + datetime.timedelta(minutes=3),
    )
    request_id = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
    amzn_tag(ec2, [request_id], tag)

    return request_id


def handler(event, context):
    ec2 = boto3.client('ec2')
    request_id = request_node(ec2, 'devbox')

    return json.dumps({'request_id': request_id})
