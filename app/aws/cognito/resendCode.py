import boto3
import os
import base64, hmac, hashlib
from dotenv import load_dotenv
load_dotenv()


def secretHash(clientId, clientSecret, username):
    message = bytes(username + clientId,'utf-8') 
    key = bytes(clientSecret,'utf-8') 
    return base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode() 


client = boto3.client("cognito-idp", region_name="ap-southeast-2")
client_id = ''
client_secret = ''

username= "user"
response = client.resend_confirmation_code(
    ClientId=client_id,
    Username=username,
    SecretHash=secretHash(client_id, client_secret, username)
)

print(response)
