#!/usr/bin/env python
import boto3

ec2 = boto3.client('ec2')
result = {}

# VPC ID を取得する
vpcs_response = ec2.describe_vpcs()

vpcids = []
for vpc in vpcs_response['Vpcs']:
    result[vpc['VpcId']] = {}
    vpcids.append(vpc['VpcId'])

# Subet ID を取得する
subnets_response = ec2.describe_subnets(
    Filters=[
        {
            'Name': 'vpc-id',
            'Values': vpcids,
        },
    ],
)

subnets = []
for subnet in subnets_response['Subnets']:
    result[subnet['VpcId']][subnet['SubnetId']] = []
    subnets.append(subnet['SubnetId'])

#TODO describe-instances でも　良いのではないか
instances = []
instances_response = ec2.describe_instances(
    Filters=[
        {
            'Name': 'subnet-id',
            'Values': subnets,
        },
    ],   
)

for reservation in instances_response['Reservations']:
    for instance in reservation['Instances']:
        result[instance['VpcId']][instance['SubnetId']].append(instance)

print(result)

# resultは下記のような構成となります。
'''
{'vpc-04bf2fec1720945c9': 
    {'subnet-0dca4c345f3c5cec7': [],
     'subnet-01295880b1ba0624b': [], 
     'subnet-0b936e69a916f7174': [], 
     'subnet-0f12fd38c571aa136': []}, 
'vpc-6080b907': 
    {'subnet-2a11dc01': [], 
    'subnet-3f073364': 
        ['i-0d7a8a237dd2654a9'], 
    'subnet-0030ca48': 
        ['i-082812ddb6657a71b']
    }
}
'''

# 結果の出力
for vpc in result:
    print(vpc)
    for subnet in result[vpc]:
        print('    ' + subnet)
        for instance in result[vpc][subnet]:
            print('        ' + instance['InstanceId'] + ' ' + instance['State']['Name'])

'''
vpc-04bf2fec1720945c9
    subnet-0dca4c345f3c5cec7
    subnet-01295880b1ba0624b
    subnet-0b936e69a916f7174
    subnet-0f12fd38c571aa136
vpc-6080b907
    subnet-2a11dc01
    subnet-3f073364
        i-0d7a8a237dd2654a9 stopped
    subnet-0030ca48
        i-082812ddb6657a71b stopped
'''
