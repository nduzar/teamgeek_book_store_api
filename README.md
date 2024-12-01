# Book Library API

This project is a serverless Book Library API built with AWS Lambda, API Gateway, and DynamoDB, using Python and the AWS CDK for infrastructure as code.

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.11 or later
- Node.js 14.x or later
- AWS CLI, configured with your AWS account
- AWS CDK CLI
- Docker (for building Lambda functions)

## Project Setup

1. Clone the repository:

git clone https://github.com/your-username/book-library-api.git 

2. Create and activate a virtual environment:
python -m venv venv source venv/bin/activate # On Windows, use venv\Scripts\activate


3. Install the required Python dependencies:
pip install -r requirements.txt


4. Install the required Node.js dependencies:
npm install


## Project Structure

- `app.py`: Contains the Flask application and API routes.
- `lambda_function.py`: The Lambda function handler.
- `book_library_stack.py`: The CDK stack defining the AWS resources.
- `requirements.txt`: List of Python dependencies.
- `test_app.py`: Unit tests for the application.

## Deploying the Application

1. Bootstrap your AWS environment (if you haven't already):
cdk bootstrap


2. Build and deploy the CDK stack:
cdk deploy


This command will:
- Build a Docker image for your Lambda function
- Deploy the Lambda function
- Set up the API Gateway
- Output the API endpoint URL

3. Note the API endpoint URL from the CDK output. You'll need this to interact with your API.

## Running Tests

To run the unit tests:

pytest test_app.py


## Using the API

You can use curl or any HTTP client to interact with your API. Here are some example curl commands:

1. Get all books:
curl https://your-api-id.execute-api.your-region.amazonaws.com/prod/books


2. Add a new book:
curl -X POST https://your-api-id.execute-api.your-region.amazonaws.com/prod/books
-H "Content-Type: application/json"
-d '{"title": "New Book", "author": "John Doe", "isbn": "1234567890"}'


Replace `your-api-id` and `your-region` with the actual values from your deployed API.

## Cleaning Up

To avoid incurring future charges, remember to destroy the resources when you're done:

cdk destroy
