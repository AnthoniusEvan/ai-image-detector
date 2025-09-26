Assignment 2 - Cloud Services Exercises - Response to Criteria
================================================

Instructions
------------------------------------------------
- Keep this file named A2_response_to_criteria.md, do not change the name
- Upload this file along with your code in the root directory of your project
- Upload this file in the current Markdown format (.md extension)
- Do not delete or rearrange sections.  If you did not attempt a criterion, leave it blank
- Text inside [ ] like [eg. S3 ] are examples and should be removed


Overview
------------------------------------------------

- **Name:** Anthonius Evan
- **Student number:** n12342734
- **Partner name (if applicable):** Alexander Steven - n11671025@qut.edu.au
- **Application name:** AI Image Detector
- **Two line description:** This app detects if an image is real or AI-generated. Users can then see the website's prediction as well as the confidence level for the prediction.
- **EC2 instance name or ID:** i-06a8765dc92716a31

------------------------------------------------

### Core - First data persistence service

- **AWS service name:**  S3
- **What data is being stored?:** Image files uploaded by users
- **Why is this service suited to this data?:** Lets the app store and retrieve images easily
- **Why is are the other services used not suitable for this data?:** DynamoDB cant store binary files (images)
- **Bucket/instance/table name:** ai-detector-image-uploads
- **Video timestamp:** 0:00 - 0:33
- **Relevant files:**
    - aws_related/s3.py

### Core - Second data persistence service

- **AWS service name:**  DynamoDB
- **What data is being stored?:** Users account and image metadata 
- **Why is this service suited to this data?:**  DynamoDB is specifically used to store key-value data, unlike S3
- **Why is are the other services used not suitable for this data?:** S3 does not support structured fields
- **Bucket/instance/table name:** n11671025-images2
- **Video timestamp:** 0:35 - 1:10
- **Relevant files:**
    - aws_related/dynamo.py

### Third data service

- **AWS service name:** 
- **What data is being stored?:** 
- **Why is this service suited to this data?:** 
- **Why is are the other services used not suitable for this data?:**
- **Bucket/instance/table name:**
- **Video timestamp:**
- **Relevant files:**
    -

### S3 Pre-signed URLs

- **S3 Bucket names:** ai-detector-image-uploads
- **Video timestamp:** 1:18 - 1:57
- **Relevant files:**
    - aws_related/s3.py

### In-memory cache

- **ElastiCache instance name:** ai-image-detector-memcache
- **What data is being cached?:** The results obtained from the prediction
- **Why is this data likely to be accessed frequently?:** There might be some controversial images that is hard to distinguish between real or AI, and the same images are being uploaded by multiple users
- **Video timestamp:** 2:00 - 3:16
- **Relevant files:**
    - aws_related/memcached.py

### Core - Statelessness

- **What data is stored within your application that is not stored in cloud data services?:** The app doesn’t store any data locally. It only keeps short-lived variables while handling a request, which are cleared once the request finishes.
- **Why is this data not considered persistent state?:** These values are temporary and not saved anywhere. All important data (like users, images, and cache) is stored in cloud services such as Cognito, S3, DynamoDB and ElastiCache.
- **How does your application ensure data consistency if the app suddenly stops?:** The app is stateless. If it stops or restarts, it just reconnects to the cloud services and continues working normally. No data is lost because everything is stored outside the app.
- **Relevant files:**
    - main.py
    - aws/cognito/*
    - aws_related/dynamo.py
    - aws_related/s3.py
    - aws_related/memcached.py

### Graceful handling of persistent connections

- **Type of persistent connection and use:**
- **Method for handling lost connections:** 
- **Relevant files:**
    -


### Core - Authentication with Cognito

- **User pool name:** ai-image-detector-user-pool
- **How are authentication tokens handled by the client?:** Response to login request sets a key-value pair in the session middleware containing the user info token on the key 'user'.
- **Video timestamp:** 3:17 - 4:15
- **Relevant files:**
    - app/main.py -> authorize()

### Cognito multi-factor authentication

- **What factors are used for authentication:** Email verification code
- **Video timestamp:** 4:23 - 5:05
- **Relevant files:**
    - aws/cognito/signUp.py

### Cognito federated identities

- **Identity providers used:** Google
- **Video timestamp:** 5:06 - 5:28
- **Relevant files:**
    - 

### Cognito groups

- **How are groups used to set permissions?:** 'Admin' users can view uploaded images
- **Video timestamp:** 5:29 - 6:50
- **Relevant files:**
    - app/main.py -> is_user_admin(user)

### Core - DNS with Route53

- **Subdomain**: https://ai-image-detector.cab432.com/
- **Video timestamp:** 6:54 - 7:06

### Parameter store

- **Parameter names:** /n11671025/imagedetector
- **Video timestamp:** 7:11 -7:38
- **Relevant files:**
    - model.py
    - s3.py(load_model)

### Secrets manager

- **Secrets names:** n11671025-Assignment2
- **Video timestamp:** 7:38 - 7:57
- **Relevant files:**
    - secret.py
    - main.py

### Infrastructure as code

- **Technology used:** 
- **Services deployed:** 
- **Video timestamp:**
- **Relevant files:**
    - 

### Other (with prior approval only)

- **Description:**
- **Video timestamp:**
- **Relevant files:**
    -

### Other (with prior permission only)

- **Description:**
- **Video timestamp:**
- **Relevant files:**
    -