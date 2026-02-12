#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infra.pren_lite_stack import PrenLiteStack


app = cdk.App()
PrenLiteStack(app, "PrenLiteStack",
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region='eu-west-3'
    )
)

app.synth()
