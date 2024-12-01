import secrets
import os

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_rds as rds,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    CfnOutput,
    RemovalPolicy,
    App,
    custom_resources as cr
)
from constructs import Construct

class BookLibraryStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # VPC
        vpc = ec2.Vpc(self, "BookLibraryVPC", max_azs=2)

        # ECS Cluster
        cluster = ecs.Cluster(self, "BookLibraryCluster", vpc=vpc)

        # RDS Instance
        database = rds.DatabaseInstance(
            self, "BookLibraryDatabase",
            engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_13_4),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT),
            multi_az=True,
            allocated_storage=20,
            storage_type=rds.StorageType.GP2,
            database_name="library",
            port=5432,
            deletion_protection=False,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # S3 Bucket for book covers
        book_covers_bucket = s3.Bucket(self, "BookCoversBucket")

        
        # Generate a secure API key
        api_key = secrets.token_urlsafe(32)

        # DynamoDB table for API keys
        api_keys_table = dynamodb.Table(
            self, "APIKeysTable",
            partition_key=dynamodb.Attribute(name="api_key", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        # Add API key to DynamoDB
        cr.AwsCustomResource(
            self, "AddAPIKeyToDynamoDB",
            on_create=cr.AwsSdkCall(
                service="DynamoDB",
                action="putItem",
                parameters={
                    "TableName": api_keys_table.table_name,
                    "Item": {
                        "api_key": {"S": api_key}
                    }
                },
                physical_resource_id=cr.PhysicalResourceId.of("AddAPIKeyToDynamoDB")
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            )
        )

        # Output the API key
        CfnOutput(self, "APIKey", value=api_key, description="API Key for authentication")

        # Lambda function for API key validation
    
        api_key_validator = lambda_.Function(
            self, "APIKeyValidator",
            runtime=lambda_.Runtime.PYTHON_3_8,
            handler="index.handler",
             code=lambda_.Code.from_asset("lambda", 
        exclude=["*.pyc", "__pycache__", "*.pyo"],
    ),
            environment={
                "API_KEYS_TABLE": api_keys_table.table_name,
            },
        )

        # API Gateway
        api = apigateway.RestApi(self, "BookLibraryAPI")

        # API Gateway authorizer
        authorizer = apigateway.TokenAuthorizer(
            self, "APIKeyAuthorizer",
            handler=api_key_validator,
        )

        # ECS Fargate Service
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "BookLibraryService",
            cluster=cluster,
            cpu=256,
            memory_limit_mib=512,
            desired_count=2,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset("../"),
                container_port=5000,
                environment={
                    "DATABASE_URL": f"postgresql://{database.instance_endpoint.hostname}:5432/library",
                    "S3_BUCKET": book_covers_bucket.bucket_name,
                },
            ),
            public_load_balancer=True
        )

# Allow the Fargate service to access the RDS instance and S3 bucket
        database.connections.allow_from(fargate_service.service, ec2.Port.tcp(5432))
        book_covers_bucket.grant_read_write(fargate_service.task_definition.task_role)

        # Create API Gateway resources and methods
        books_resource = api.root.add_resource("books")
        books_resource.add_method("GET", apigateway.HttpIntegration(f"{fargate_service.load_balancer.load_balancer_dns_name}/api/books"), authorizer=authorizer)
        books_resource.add_method("POST", apigateway.HttpIntegration(f"{fargate_service.load_balancer.load_balancer_dns_name}/api/books"), authorizer=authorizer)

        book_resource = books_resource.add_resource("{id}")
        book_resource.add_method("GET", apigateway.HttpIntegration(f"{fargate_service.load_balancer.load_balancer_dns_name}/api/books/{{id}}"), authorizer=authorizer)
        book_resource.add_method("PUT", apigateway.HttpIntegration(f"{fargate_service.load_balancer.load_balancer_dns_name}/api/books/{{id}}"), authorizer=authorizer)
        book_resource.add_method("DELETE", apigateway.HttpIntegration(f"{fargate_service.load_balancer.load_balancer_dns_name}/api/books/{{id}}"), authorizer=authorizer)

        cover_resource = book_resource.add_resource("cover")
        cover_resource.add_method("POST", apigateway.HttpIntegration(f"{fargate_service.load_balancer.load_balancer_dns_name}/api/books/{{id}}/cover"), authorizer=authorizer)

        search_resource = books_resource.add_resource("search")
        search_resource.add_method("GET", apigateway.HttpIntegration(f"{fargate_service.load_balancer.load_balancer_dns_name}/api/books/search"), authorizer=authorizer)

        # Output the API Gateway URL
        CfnOutput(self, "APIGatewayURL", value=api.url)

        # Output the S3 bucket name
        CfnOutput(self, "S3BucketName", value=book_covers_bucket.bucket_name)

app = App()
BookLibraryStack(app, "BookLibraryStack")
app.synth()