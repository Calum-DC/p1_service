import boto3
import json
import os
from flask import Flask, jsonify
from dotenv import load_dotenv
import pymsteams
import threading

app = Flask(__name__)

# Load environment variables
load_dotenv()
sqs_client = boto3.client('sqs', region_name=os.getenv('AWS_REGION'))
QUEUE_URL = os.getenv('SQS_P1_URL')
TEAMS_WEBHOOK_URL = os.getenv('TEAMS_WEBHOOK')

stop_flag = False

def process_sqs_p1_message():
    global stop_flag
    while not stop_flag:
        try:
            # Receive the message from the SQS queue
            response = sqs_client.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10
            )

            messages = response.get('Messages', [])

            if not messages:
                continue

            message = messages[0]
            receipt_handle = message['ReceiptHandle']
            message_body = json.loads(message['Body'])
            print(f"Received message: {message_body}")

            title = message_body.get('title')
            description = message_body.get('description')


            # Use the native inference API to send a text message to Amazon Titan Text
            # and print the response stream.
            # Create a Bedrock Runtime client 
            client = boto3.client("bedrock-runtime", region_name="us-east-1")

            # Set the model ID, e.g., Titan Text Premier.
            model_id = "amazon.titan-text-express-v1"

            # Define the prompt for the model.
            prompt = "The following passage of text outlines an issue that has been reported via an online web form, please pretend you are an IT support engineer and provide a solution to the problem or statement given, also be aware that this message will be read by a recipient that is unable to provide any additional information. Dont' write too much and definitely dont say that you are a model responding to the problem. Please provide a structured solution that clearly outlines a solution: " + description

            # Format the request payload using the model's native structure.
            native_request = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 1024,
                    "temperature": 0.3,
                },
            }

            # Convert the native request to JSON.
            ai_request = json.dumps(native_request)

            try:
                ai_response = client.invoke_model(modelId=model_id, body=ai_request)
            except client.exceptions.EndpointConnectionError as e:
                print(f"Error connecting to the AI model endpoint: {str(e)}")

            # Decode the response body.
            model_response = json.loads(ai_response["body"].read())

            # Extract and print the response text.
            response_text = model_response["results"][0]["outputText"]
            print(response_text)

            formatted_message = f"**Bug report description:**\n{description}\n\n**Suggested solution:**\n{response_text}"

            # Sending the message to teams
            print("Sending message to Microsoft Teams...")
            teams_message = pymsteams.connectorcard(TEAMS_WEBHOOK_URL)
            teams_message.title(f"Priority 1 Bug: {title}")
            teams_message.text(formatted_message)
            teams_message.send()
            print("Message successfully sent to Teams.")

            # Delete the message from the SQS queue after processing
            sqs_client.delete_message(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=receipt_handle
            )
            print(f"Message deleted from SQS queue: {receipt_handle}")

        except Exception as e:
            print(f"An error occurred: {str(e)}")

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200


def background_thread():
    sqs_thread = threading.Thread(target=process_sqs_p1_message, daemon=True)
    sqs_thread.start()
    return sqs_thread

background_thread = background_thread()

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=8001)
    except KeyboardInterrupt:
        print("Shutting down...")
        stop_flag = True
        bg_thread.join()