import os
from pathlib import Path
from constructs import Construct
from aws_cdk import (
    Stack, Duration, RemovalPolicy
)
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_s3_deployment as s3deploy

# Manually create the Route 53 hosted zone
#  and the key pair: https://us-east-1.console.aws.amazon.com/ec2/home?region=us-east-1#KeyPairs


# DOMAIN SETUP
domain_name = "mevzuat.info"
hosted_zone_id = "Z00498653B0CJOBSP7JEQ"
repo_url = "git@github.com:onurmatik/mevzuat"


class AppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Lookup existing hosted zone
        hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
            self,
            domain_name,
            hosted_zone_id=hosted_zone_id,
            zone_name=domain_name
        )

        # Create S3 Bucket
        bucket = s3.Bucket(
            self, "AppStaticMediaBucket",
            bucket_name="mevzuat-documents",
            versioned=False,
            public_read_access=True,
            removal_policy=RemovalPolicy.RETAIN,
            block_public_access=s3.BlockPublicAccess(block_public_policy=False)
        )

        # ACL to allow public read
        bucket.add_to_resource_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            principals=[iam.AnyPrincipal()],
            actions=["s3:GetObject"],
            resources=[f"{bucket.bucket_arn}/*"]
        ))

        # Create EC2 VPC + Instance
        vpc = ec2.Vpc(self, "AppVPC",
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                )
            ]
        )

        sg = ec2.SecurityGroup(self, "AppSG", vpc=vpc)
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22), "Allow SSH")
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "Allow HTTP")
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "Allow HTTPS")

        # User data script for Ubuntu 24.04
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "sudo apt-get update -y",
            "sudo apt-get install -y python3-pip python3-venv git nginx",
            "sudo apt-get install -y build-essential libssl-dev libffi-dev python3-dev",
            "sudo apt-get install redis-server",
            "sudo apt-get install certbot python3-certbot-nginx",

            # Create necessary folders
            "mkdir -p /home/ubuntu/mevzuat/static",
            "mkdir -p /home/ubuntu/mevzuat/cache",

            # Clone and set up the project
            f"sudo -u ubuntu git clone {repo_url} /home/ubuntu/mevzuat || true",
            "sudo -u ubuntu python3 -m venv /home/ubuntu/mevzuat/venv",
            "sudo -u ubuntu /home/ubuntu/mevzuat/venv/bin/pip install --upgrade pip",
            "sudo -u ubuntu /home/ubuntu/mevzuat/venv/bin/pip install -r /home/ubuntu/mevzuat/requirements.txt",

            # Django setup
            "cd /home/ubuntu/mevzuat && sudo -u ubuntu /home/ubuntu/mevzuat/venv/bin/python manage.py migrate",
            "cd /home/ubuntu/mevzuat && sudo -u ubuntu /home/ubuntu/mevzuat/venv/bin/python manage.py collectstatic --noinput",

            # Gunicorn systemd setup
            "sudo tee /etc/systemd/system/mevzuat.service > /dev/null <<EOF",
            "[Unit]",
            "Description=Gunicorn daemon for Mevzuat",
            "After=network.target",

            "[Service]",
            "User=ubuntu",
            "Group=ubuntu",
            "WorkingDirectory=/home/ubuntu/mevzuat",
            "Environment='PATH=/home/ubuntu/mevzuat/venv/bin'",
            "ExecStart=/home/ubuntu/mevzuat/venv/bin/gunicorn mevzuat.wsgi:application --workers 3 --bind 0.0.0.0:8000",
            "Restart=always",
            "RestartSec=5",

            "[Install]",
            "WantedBy=multi-user.target",
            "EOF",

            # Celery systemd setup
            "sudo tee /etc/systemd/system/celery.service > /dev/null <<EOF",
            "[Unit]",
            "Description=Celery worker for Mevzuat",
            "After=network.target",
            "",
            "[Service]",
            "User=ubuntu",
            "Group=ubuntu",
            "WorkingDirectory=/home/ubuntu/mevzuat",
            "Environment='PATH=/home/ubuntu/mevzuat/venv/bin'",
            "ExecStart=/home/ubuntu/mevzuat/venv/bin/celery -A mevzuat worker --concurrency=1 --loglevel=INFO",
            "",
            "[Install]",
            "WantedBy=multi-user.target",
            "EOF",
            "",

            # Enable and start services
            "sudo systemctl daemon-reexec",
            "sudo systemctl daemon-reload",
            "sudo systemctl enable redis-server",
            "sudo systemctl start redis-server",
            "sudo systemctl enable celery",
            "sudo systemctl start celery",
            "sudo systemctl enable mevzuat",
            "sudo systemctl start mevzuat",

            # Nginx config
            "echo 'server {",
            "    listen 80;",
            "    server_name mevzuat.info;",
            "    location = /favicon.ico { access_log off; log_not_found off; }",
            "    location /static/ {",
            "        alias /home/ubuntu/mevzuat/static/;",
            "    }",
            "    location / {",
            "        proxy_pass http://127.0.0.1:8000;",
            "        proxy_set_header Host $host;",
            "        proxy_set_header X-Real-IP $remote_addr;",
            "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
            "        proxy_set_header X-Forwarded-Proto $scheme;",
            "    }",
            "}' | sudo tee /etc/nginx/sites-available/mevzuat > /dev/null"
            
            # Enable and restart Nginx
            "sudo ln -sf /etc/nginx/sites-available/mevzuat /etc/nginx/sites-enabled",
            "sudo rm -f /etc/nginx/sites-enabled/default",
            "sudo nginx -t",
            "sudo systemctl restart nginx"
        )

        # Ubuntu 24.04 LTS AMI
        ubuntu_ami = ec2.MachineImage.generic_linux({
            "us-east-1": "ami-0731becbf832f281e"
        })

        instance = ec2.Instance(self, "AppInstance",
            instance_type=ec2.InstanceType("t3.micro"),
            machine_image=ubuntu_ami,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group=sg,
            key_name='mevzuat-ec2-key',
            user_data=user_data,
        )

        # Elastic IP
        eip = ec2.CfnEIP(self, "AppElasticIP", domain="vpc")
        ec2.CfnEIPAssociation(
            self, "AppElasticIPAssoc",
            eip=eip.ref,
            instance_id=instance.instance_id
        )

        # Grant S3 permissions to EC2
        bucket.grant_read_write(instance.role)

        # Allow EC2 to send email via SES
        instance.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSESFullAccess")
        )

        # SES identity
        ses.EmailIdentity(self, "SESIdentity", identity=ses.Identity.domain(domain_name))
