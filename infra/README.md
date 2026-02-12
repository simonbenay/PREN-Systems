
# PREN Lite Infrastructure

CDK v2 Python infrastructure for the PREN Lite system deployed to eu-west-3.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `requirements.txt` file and rerun the `python -m pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!

## Stack: PrenLiteStack

The default stack includes:

- S3 Buckets: RawBucket, ArtifactsBucket (versioned, 30-day lifecycle)
- DynamoDB: PrenSignalsTable (pk/sk), PrenScoresTable (iris_id) with PITR
- Lambda Functions: ingest_handler, score_handler, explain_handler (Python 3.11)
- API Gateway HTTP API: GET /score, GET /explain
- Step Functions: PrenIngestionStateMachine (ValidateInput → StoreSignals)
- All resources tagged: Project=PREN, Team=PREN Systems, City=Paris, Env=dev

## Prerequisites

- Node.js (required for CDK CLI)
- AWS CLI configured
- Python 3.11+

## Deployment

```bash
# Install Node.js CDK CLI globally
npm install -g aws-cdk

# Activate virtual environment
.venv\Scripts\activate.bat  # Windows
source .venv/bin/activate    # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Synthesize CloudFormation template
cdk synth

# Deploy to eu-west-3
cdk deploy PrenLiteStack
```

## Outputs

After deployment, the stack outputs:
- RawBucketName
- ArtifactsBucketName
- SignalsTableName
- ScoresTableName
- ApiEndpointUrl
- StateMachineArn
