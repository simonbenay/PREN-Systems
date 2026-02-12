from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    Tags,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigwv2_integrations,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_logs as logs,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
)
from constructs import Construct

class PrenLiteStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Common tags for all resources
        Tags.of(self).add("Project", "PREN")
        Tags.of(self).add("Team", "PREN Systems")
        Tags.of(self).add("City", "Paris")
        Tags.of(self).add("Env", "dev")

        # 1) S3 Buckets
        raw_bucket = s3.Bucket(
            self, "RawBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(30)
                )
            ],
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        artifacts_bucket = s3.Bucket(
            self, "ArtifactsBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(30)
                )
            ],
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # 2) DynamoDB Tables
        signals_table = dynamodb.Table(
            self, "PrenSignalsTable",
            partition_key=dynamodb.Attribute(
                name="pk",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sk",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.DESTROY
        )

        scores_table = dynamodb.Table(
            self, "PrenScoresTable",
            partition_key=dynamodb.Attribute(
                name="iris_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.DESTROY
        )

        # 3) Lambda Functions
        # Ingest handler
        ingest_handler = lambda_.Function(
            self, "IngestHandler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="ingest_handler.handler",
            code=lambda_.Code.from_asset("infra/lambda"),
            log_retention=logs.RetentionDays.ONE_WEEK,
            environment={
                "SIGNALS_TABLE": signals_table.table_name,
                "RAW_BUCKET": raw_bucket.bucket_name
            }
        )

        # Grant permissions to ingest handler
        signals_table.grant_write_data(ingest_handler)
        raw_bucket.grant_read(ingest_handler)

        # Score handler
        score_handler = lambda_.Function(
            self, "ScoreHandler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="score_handler.handler",
            code=lambda_.Code.from_asset("infra/lambda"),
            log_retention=logs.RetentionDays.ONE_WEEK,
            environment={
                "SCORES_TABLE": scores_table.table_name,
                "SIGNALS_TABLE": signals_table.table_name
            }
        )

        # Grant read permissions
        scores_table.grant_read_data(score_handler)
        signals_table.grant_read_data(score_handler)

        # Explain handler
        explain_handler = lambda_.Function(
            self, "ExplainHandler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="explain_handler.handler",
            code=lambda_.Code.from_asset("infra/lambda"),
            log_retention=logs.RetentionDays.ONE_WEEK,
            environment={
                "SCORES_TABLE": scores_table.table_name,
                "SIGNALS_TABLE": signals_table.table_name
            }
        )

        # Grant read permissions
        scores_table.grant_read_data(explain_handler)
        signals_table.grant_read_data(explain_handler)

        # Health handler
        health_handler = lambda_.Function(
            self, "HealthHandler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="health_handler.handler",
            code=lambda_.Code.from_asset("infra/lambda"),
            log_retention=logs.RetentionDays.ONE_WEEK,
            environment={
                "SCORES_TABLE": scores_table.table_name
            }
        )

        # Grant read permissions
        scores_table.grant_read_data(health_handler)

        # 4) API Gateway HTTP API
        http_api = apigwv2.HttpApi(
            self, "PrenHttpApi",
            api_name="pren-lite-api"
        )

        # Score integration
        score_integration = apigwv2_integrations.HttpLambdaIntegration(
            "ScoreIntegration",
            score_handler
        )

        http_api.add_routes(
            path="/score",
            methods=[apigwv2.HttpMethod.GET],
            integration=score_integration
        )

        # Explain integration
        explain_integration = apigwv2_integrations.HttpLambdaIntegration(
            "ExplainIntegration",
            explain_handler
        )

        http_api.add_routes(
            path="/explain",
            methods=[apigwv2.HttpMethod.GET],
            integration=explain_integration
        )

        # Health integration
        health_integration = apigwv2_integrations.HttpLambdaIntegration(
            "HealthIntegration",
            health_handler
        )

        http_api.add_routes(
            path="/health",
            methods=[apigwv2.HttpMethod.GET],
            integration=health_integration
        )

        # 5) CloudWatch Alarm for API 5XX Errors
        api_5xx_alarm = cloudwatch.Alarm(
            self, "Api5xxAlarm",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="5XXError",
                dimensions_map={
                    "ApiId": http_api.api_id,
                    "Stage": "$default"
                },
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )

        # Apply tags to the alarm
        Tags.of(api_5xx_alarm).add("Project", "PREN")
        Tags.of(api_5xx_alarm).add("Team", "PREN Systems")
        Tags.of(api_5xx_alarm).add("City", "Paris")
        Tags.of(api_5xx_alarm).add("Env", "dev")

        # 6) Step Functions State Machine
        # ValidateInput task
        validate_input_task = tasks.LambdaInvoke(
            self, "ValidateInput",
            lambda_function=ingest_handler,
            output_path="$.Payload"
        )

        # StoreSignals pass state
        store_signals_state = sfn.Pass(
            self, "StoreSignals",
            comment="Pass through input"
        )

        # Define the workflow
        definition = validate_input_task.next(store_signals_state)

        state_machine = sfn.StateMachine(
            self, "PrenIngestionStateMachine",
            state_machine_name="PrenIngestionStateMachine",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            logs=sfn.LogOptions(
                destination=logs.LogGroup(
                    self, "StateMachineLogGroup",
                    retention=logs.RetentionDays.ONE_WEEK,
                    removal_policy=RemovalPolicy.DESTROY
                ),
                level=sfn.LogLevel.ALL
            )
        )

        # 7) CDK Outputs
        CfnOutput(
            self, "RawBucketName",
            value=raw_bucket.bucket_name,
            description="Raw bucket for PDFs and datasets"
        )

        CfnOutput(
            self, "ArtifactsBucketName",
            value=artifacts_bucket.bucket_name,
            description="Artifacts bucket for batch outputs"
        )

        CfnOutput(
            self, "SignalsTableName",
            value=signals_table.table_name,
            description="DynamoDB signals table"
        )

        CfnOutput(
            self, "ScoresTableName",
            value=scores_table.table_name,
            description="DynamoDB scores table"
        )

        CfnOutput(
            self, "ApiEndpointUrl",
            value=http_api.url or "",
            description="HTTP API endpoint URL"
        )

        CfnOutput(
            self, "HealthEndpointUrl",
            value=(http_api.url or "") + "health",
            description="Health check endpoint URL"
        )

        CfnOutput(
            self, "StateMachineArn",
            value=state_machine.state_machine_arn,
            description="Step Functions state machine ARN"
        )

        CfnOutput(
            self, "Api5xxAlarmName",
            value=api_5xx_alarm.alarm_name,
            description="CloudWatch Alarm name for API 5XX errors"
        )
