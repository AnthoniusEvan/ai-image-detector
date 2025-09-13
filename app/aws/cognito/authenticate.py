import boto3
import hmac, hashlib, base64 
import os
from dotenv import load_dotenv

load_dotenv()

username= "user"
password= "MySuperSecret99!"
email= "n12342734@qut.edu.au"
client_id = os.environ["AWS_COGNITO_CLIENT_ID"]  
client_secret = os.environ["AWS_COGNITO_CLIENT_SECRET"] 

def secretHash(clientId, clientSecret, username):
    message = bytes(username + clientId,'utf-8') 
    key = bytes(clientSecret,'utf-8') 
    return base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode() 


def authenticate(username, password):
    client = boto3.client("cognito-idp", region_name="ap-southeast-2")
    try:
        response = client.initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
                "SECRET_HASH": secretHash(client_id, client_secret, username)
            },
            ClientId=client_id  # match signUp.py
        )
        tokens = response["AuthenticationResult"]
        # Optionally verify tokens here using jose or cognito public keys
        return tokens
    except Exception as e:
        print(f"Error during authentication: {e}")
        return None

if __name__ == "__main__":
    authenticate_response = authenticate()
    print("Authentication successful:", authenticate_response)
