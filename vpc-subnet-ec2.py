#!/usr/bin/env python
import boto3
import json

ec2 = boto3.client('ec2')
result = {'Vpcs':{}}

# リージョン内の VPC を取得する
vpcs_response = ec2.describe_vpcs()

vpcids = []
for vpc in vpcs_response['Vpcs']:
    vpc_elem = {
        'VpcId': vpc['VpcId'],
        'Subnets': {}
    }    

    if 'Tags' in vpc:
        for tag in vpc['Tags']:
            if tag['Key'] == 'Name':
                 vpc_elem['VpcName'] = tag['Value']
                 break

    result['Vpcs'][vpc['VpcId']] = vpc_elem
    vpcids.append(vpc['VpcId'])

# VPC に紐づくサブネットの情報を取得する
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
    subnet_elem = {
            'SubnetId': subnet['SubnetId'],
            'Instances': {},
            'AssociatedRouteTables': {},
        }

    if 'Tags' in subnet:
        for tag in subnet['Tags']:
            if tag['Key'] == 'Name':
                 subnet_elem['SubnetName'] = tag['Value']
                 break

    result['Vpcs'][subnet['VpcId']]['Subnets'][subnet['SubnetId']] = subnet_elem
    subnets.append(subnet['SubnetId'])

# サブネットに紐づくルートテーブル情報を取得する
# サブネットに明示的に紐付けられていない場合、紐付けが取得できない点に注意すること
rt_response = ec2.describe_route_tables(
    Filters=[
        {
            'Name': 'vpc-id',
            'Values': vpcids,
        },
    ],
)
# print(json.dumps(rt_response, indent=2))
for rt in rt_response['RouteTables']:
    rt_elem = {
        'RouteTableId': rt['RouteTableId'],
        'Route': rt['Routes']
    }

    if 'Tags' in rt:
        for tag in rt['Tags']:
            if tag['Key'] == 'Name':
                 rt_elem['RouteTableName'] = tag['Value']
                 break
    
    for rt_assoc in rt['Associations']:
        if 'SubnetId' in rt_assoc:
            result['Vpcs'][rt['VpcId']]['Subnets'][rt_assoc['SubnetId']]['AssociatedRouteTables'][rt_assoc['RouteTableId']] = rt_elem
    
print(subnets)
# サブネットに紐づく EC2インスタンス情報を取得する
instances = []
instances_response = ec2.describe_instances(
    Filters=[
        {
            'Name': 'subnet-id',
            'Values': subnets,
        },
    ],
)
print(instances_response)
for reservation in instances_response['Reservations']:
    for instance in reservation['Instances']:
        instance_elem = {
            'InstanceId': instance['InstanceId'],
            'State': instance['State']['Name'],           
        }

        if 'Tags' in instance:
            for tag in instance['Tags']:
                if tag['Key'] == 'Name':
                    instance_elem['InstanceName'] = tag['Value']
                    break
        print(instance['SubnetId'] + ' ' + instance['InstanceId'])
        for eni in instance['NetworkInterfaces']:
            result['Vpcs'][instance['VpcId']]['Subnets'][eni['SubnetId']]['Instances'][instance['InstanceId']] = instance_elem

# result は下記のような構成となる
'''
{
  "Vpcs": {
    "vpc-0000000000000000": {
      "VpcId": "vpc-0000000000000000",
      "Subnets": {        
        "subnet-000000000000000000": {
          "SubnetId": "subnet-000000000000000000",
          "Instances": {
            "i-00000000000000000": {
              "InstanceId": "i-00000000000000000",
              "State": "stopped",
              "InstanceName": "test-0"
            },
            "i-111111111111111111": {
              "InstanceId": "i-111111111111111111",
              "State": "stopped",
              "InstanceName": "test-1"
            }
          },
          "AssociatedRouteTables": {
            "rtb-000000000": {
              "RouteTableId": "rtb-000000000",
              "Route": [
                {
                  "DestinationCidrBlock": "172.31.0.0/16",
                  "GatewayId": "local",
                  "Origin": "CreateRouteTable",
                  "State": "active"
                },
                {
                  "DestinationCidrBlock": "0.0.0.0/0",
                  "GatewayId": "igw-000000000",
                  "Origin": "CreateRoute",
                  "State": "active"
                }
              ],
              "RouteTableName": "default_rtb"
            }
          },
          "SubnetName": "subnet-test-0"
        }
      },
      "VpcName": "vpc-test-0"
    },
    （以下略）
'''

# resultの内容を整形して結果として出力する
for vpcid in result['Vpcs']:
    vpc = result['Vpcs'][vpcid]
    vpcstr = vpcid
    if 'VpcName' in vpc:
        vpcstr += ' [' + vpc['VpcName'] + ']'
    print(vpcstr)
    for subnetid in vpc['Subnets']:
        subnet = vpc['Subnets'][subnetid]
        subnetstr = '    ' + subnetid
        if 'SubnetName' in subnet:
            subnetstr += ' [' + subnet['SubnetName'] + ']'
        print(subnetstr)
        for instanceid in subnet['Instances']:
            instance = subnet['Instances'][instanceid]
            instancestr = '        EC2 Instance:' + instance['InstanceId']
            if 'InstanceName' in instance:
                instancestr += '[' + instance['InstanceName'] + ']'
            instancestr += '  Status:' + instance['State']
            print(instancestr)
        for rtid in subnet['AssociatedRouteTables']:
            rt = subnet['AssociatedRouteTables'][rtid]
            rtstr = '        RouteTable:'
            if 'RouteTableName' in rt:
                rtstr += '[' + rt['RouteTableName'] + ']'
            print(rtstr) 
            for route in rt['Route']:
                print('                Destination:{}  GatewayId:{}  State:{}'.format(route['DestinationCidrBlock'], route['GatewayId'], route['State']))

# 出力イメージ
'''
vpc-0000000000000000[vpc-test]
    subnet-000000000000000000[subnet-test]
        EC2 Instance:i-00000000000000000[ec2-test1]  Status:stopped
        EC2 Instance:i-11111111111111111[ec2-test2]  Status:stopped
        RouteTable:rtb-000000000[test-rtb]
                Destination:172.31.0.0/16  GatewayId:local  State:active
                Destination:0.0.0.0/0  GatewayId:igw-c40314a0  State:active
（以下略）
'''