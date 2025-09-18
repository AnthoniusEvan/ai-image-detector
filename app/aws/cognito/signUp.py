import boto3
import hmac, hashlib, base64
import os
from dotenv import load_dotenv
load_dotenv()

username= "user"
password= "MySuperSecret99!"
email= "n12342734@qut.edu.au"
client_id = os.environ['AWS_COGNITO_CLIENT_ID']
client_secret = os.environ['AWS_COGNITO_CLIENT_SECRET']

def secretHash(clientId, clientSecret, username):
    message = bytes(username + clientId,'utf-8') 
    key = bytes(clientSecret,'utf-8') 
    return base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode() 

def signup(username, password, email):
    client = boto3.client("cognito-idp", region_name="ap-southeast-2")
    response = client.sign_up(
        ClientId=client_id,
        Username=username,
        Password=password,
        SecretHash=secretHash(client_id, client_secret, username),
        UserAttributes=[{"Name": "email", "Value": email}]
    )
    return response

if __name__ == "__main__":
    signup_response = signup(username, password, email)
    print("Sign-up successful:", signup_response)
