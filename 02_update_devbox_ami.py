import boto3
import datetime
import json

from typing import List


def amzn_tag(ec2, resources: List[str], tag: str):
    ec2.create_tags(
        Resources=resources,
        Tags=[{
            'Key': 'purpose',
            'Value': tag,
        }],
    )


def latest_instance(ec2):
    response = ec2.describe_instances(
        Filters=[devbox_filter],
    )

    instances = []
    for resv in response['Reservations']:
        instances.extend(resv['Instances'])

    instances_sorted = sorted(
        instances,
        key=lambda inst: inst['LaunchTime'],
    )
    instance_id = instances_sorted[-1]['InstanceId']

    return instance_id


devbox_filter = {
    'Name': 'tag:purpose',
    'Values': ['devbox'],
}


def update_ami(ec2):
    instance_id = latest_instance(ec2)

    response = ec2.create_image(
        InstanceId=instance_id,
        Name='arch-linux-devbox-{}'.format(datetime.datetime.utcnow().strftime('%Y-%m-%d-%H%M')),
        BlockDeviceMappings=[
            {
                'DeviceName': '/dev/sda1',
                'Ebs': {
                    'DeleteOnTermination': True,
                    'VolumeType': 'gp2',
                },
            },
            {
                'DeviceName': '/dev/xvdb',
                'NoDevice': '',
            },
        ],
    )

    image_id = response['ImageId']
    amzn_tag(ec2, [image_id], 'devbox')
    return image_id


def handler(event, context):
    ec2 = boto3.client('ec2')
    image_id = update_ami(ec2)
    return json.dumps({'image_id': image_id})
