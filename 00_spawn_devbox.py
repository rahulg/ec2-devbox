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
