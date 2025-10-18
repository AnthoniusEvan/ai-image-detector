import os
import boto3
import torch
from torchvision import datasets, transforms, models
from torch import nn, optim
from boto3.dynamodb.conditions import Attr
import shutil, json

label_map = {
    "AI-generated": "ai",
    "Real": "real"
}

# --- ENV VARS ---
S3_BUCKET = os.getenv("S3_BUCKET", "ai-detector-image-uploads")
TABLE_NAME = os.getenv("DDB_TABLE", "n11671025-images2")
DDB_TABLE_BATCH = os.getenv("DDB_TABLE_BATCH", "ai-image-detector-new-batch")
REGION = os.getenv("REGION", 'ap-southeast-2')

# --- AWS CLIENTS ---
s3 = boto3.client("s3", region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)

t = dynamodb.Table(DDB_TABLE_BATCH)
response = t.scan(
    FilterExpression=Attr("batch_id").eq('current'),
    Limit=1
)
items = response.get("Items", [])

S3_IMAGES = items[0]['s3_keys'] if items and items[0] else None

if not S3_IMAGES:
    raise ValueError("Missing required environment variable S3_IMAGES")

s3_keys = [key.strip() for key in S3_IMAGES.split(",") if key.strip()]

# --- LOCAL DIR SETUP ---
base_dir = "/tmp/data"
train_dir = os.path.join(base_dir, "train")
os.makedirs(os.path.join(train_dir, "ai"), exist_ok=True)
os.makedirs(os.path.join(train_dir, "real"), exist_ok=True)

# --- FETCH IMAGES + LABELS ---
for key in s3_keys:
    # get user feedback from DynamoDB

    t = dynamodb.Table(TABLE_NAME)

    response = t.scan(
        FilterExpression=Attr("s3_key").eq(key.strip())
    )

    items = response.get("Items", [])

    item = items[0] if items else None

    if not item:
        print(f"No record found in DynamoDB for {key}, skipping.")
        continue

    user_feedback = item["user_prediction"] if "user_prediction" in item else None

    if user_feedback not in ["AI-generated", "Real"]:
        print(f"No valid feedback for {key}, skipping.")
        continue

    # download image from S3
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        image_bytes = response["Body"].read()

        label = label_map.get(user_feedback)
        if not label:
            print(f"Invalid feedback for {key}, skipping.")
            continue
        target_dir = os.path.join(train_dir, label)
        filename = os.path.basename(key)
        file_path = os.path.join(target_dir, filename)

        with open(file_path, "wb") as f:
            f.write(image_bytes)

        print(f"Added {filename} to {user_feedback} folder")

    except Exception as e:
        print(f"Failed to download {key}: {e}")

# --- MODEL SETUP ---
local_model_path = "/tmp/model.pth"
try:
    s3.download_file(S3_BUCKET, "model/model.pth", local_model_path)
    print("Loaded existing model for fine-tuning.")
except:
    print("No existing model found, training from scratch.")
    local_model_path = None

# --- TRAINING PIPELINE ---
transform = transforms.Compose([
    transforms.Resize((224,224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225])
])

for cls in ["ai", "real"]:
    folder = os.path.join(train_dir, cls)
    if not os.listdir(folder):
        shutil.rmtree(folder)

train_ds = datasets.ImageFolder(train_dir, transform=transform)
train_loader = torch.utils.data.DataLoader(train_ds, batch_size=8, shuffle=True)

model = models.resnet50(pretrained=True)
model.fc = nn.Linear(model.fc.in_features, 2)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)


if local_model_path and os.path.exists(local_model_path):
    model.load_state_dict(torch.load(local_model_path, map_location="cpu"))

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=1e-4)

# --- TRAIN LOOP ---
print(f"Starting fine-tuning on {len(train_ds)} images...")
for epoch in range(3):
    break

    total_loss = 0
    for imgs, labels in train_loader:
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(imgs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    print(f"Epoch {epoch+1} - Loss: {total_loss / len(train_loader):.4f}")

# --- SAVE & UPLOAD MODEL ---
torch.save(model.state_dict(), local_model_path)

if os.path.exists(local_model_path):
    s3.upload_file(local_model_path, S3_BUCKET, "model/model.pth")
    print("Model retrained and uploaded to S3.")
else:
    print("Model file missing after training — skipping upload.")
