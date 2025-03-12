import boto3
import json
import os
from flask import Flask, jsonify
from dotenv import load_dotenv
import pymsteams
import threading

app = Flask(__name__)

# Load environment variables

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

            # Sending the message to teams
            print("Sending message to Microsoft Teams...")
            teams_message = pymsteams.connectorcard(TEAMS_WEBHOOK_URL)
            teams_message.title(f"Priority 1 Bug: {title}")
            teams_message.text(description)
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
        background_thread.join()