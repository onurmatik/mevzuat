#!/usr/bin/env python3
import aws_cdk as cdk
from app_stack import AppStack

app = cdk.App()
AppStack(app, "AppStack", env=cdk.Environment(region="us-east-1"))
app.synth()
