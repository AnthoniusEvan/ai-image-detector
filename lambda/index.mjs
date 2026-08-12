import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { DynamoDBClient, GetItemCommand, ScanCommand, UpdateItemCommand } from "@aws-sdk/client-dynamodb";
import { EC2Client, StartInstancesCommand } from "@aws-sdk/client-ec2";
import crypto from "crypto";

// Helper to convert S3 stream to buffer
function streamToBuffer(stream) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    stream.on("data", (chunk) => chunks.push(chunk));
    stream.on("error", reject);
    stream.on("end", () => resolve(Buffer.concat(chunks)));
  });
}

// AWS and environment setup
const REGION = process.env.REGION || "ap-southeast-2";
const S3_BUCKET = process.env.S3_BUCKET;
const DDB_TABLE = process.env.DDB_TABLE;
const DDB_TABLE_BATCH = process.env.DDB_TABLE_BATCH; // small table to store ready batch
const EC2_INSTANCE = process.env.EC2_INSTANCE || 'i-0666dbfa74835f919';
const BATCH_THRESHOLD = Number(process.env.BATCH_THRESHOLD) || 5;

const s3 = new S3Client({ region: REGION });
const ddb = new DynamoDBClient({ region: REGION });

// Helper: hash image bytes
function getImageHash(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

// Concurrency-safe batch update
async function updateBatchWithRetry(newImages) {
  const MAX_RETRIES = 3;

  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    // Read current batch
    const batchResp = await ddb.send(new GetItemCommand({
      TableName: DDB_TABLE_BATCH,
      Key: { "batch_id": { S: "current" } }
    }));

    let currentBatch = [];

    if (batchResp.Item?.hashes?.SS) {
      const hashes = batchResp.Item.hashes.SS;
      currentBatch = (hashes.length === 1 && hashes[0] === "empty") ? [] : hashes;
    }

    let currentS3Keys = batchResp.Item?.s3_keys?.S || '';

    // Merge unique hashes
    const updatedBatch = [...currentBatch];
    const imagesToAdd = [];
    for (const img of newImages) {
      if (!currentBatch.includes(img.hash)) {
        updatedBatch.push(img.hash);
        currentS3Keys += currentS3Keys ? (',' + img.s3Key) : img.s3Key;
        imagesToAdd.push(img.s3Key);
      }
    }

    if (imagesToAdd.length === 0) return []; // nothing new

    try {
      // Conditional update
      const uniqueBatch = Array.from(new Set(updatedBatch.filter(h => h && h.trim() !== "")));

      await ddb.send(new UpdateItemCommand({
        TableName: DDB_TABLE_BATCH,
        Key: { "batch_id": { S: "current" } },
        UpdateExpression: "SET hashes = :updatedBatch, s3_keys = :updatedS3Keys",
        ConditionExpression: "attribute_not_exists(hashes) OR size(hashes) = :currentSize",
        ExpressionAttributeValues: {
          ":updatedBatch": { SS: uniqueBatch },
          ":currentSize": { N: currentBatch.length.toString() },
          ":updatedS3Keys": { S: currentS3Keys }
        }
      }));      

      return imagesToAdd; // success
    } catch (err) {
      if (err.name === "ConditionalCheckFailedException") {
        console.log("Conditional update failed due to concurrency, retrying...");
        await new Promise(res => setTimeout(res, 200));
        
        continue;
      } else {
        throw err;
      }
    }
  }

  throw new Error("Failed to update batch after multiple retries due to concurrency");
}

// Lambda handler
export const handler = async (event) => {
  console.log("S3 event received:", JSON.stringify(event, null, 2));

  const newImages = [];

  // Process each uploaded object
  for (const record of event.Records) {
    const s3Key = record.s3.object.key;

    // Fetch metadata from DynamoDB to check user feedback
    const response = await ddb.send(new ScanCommand({
      TableName: DDB_TABLE,
      FilterExpression: "s3_key = :k",
      ExpressionAttributeValues: { ":k": { S: s3Key } },
    }));
    
    const item = response.Items?.[0];

    if (!item || !item.user_prediction || !item.user_prediction.S || item.user_prediction.S.trim() === "") {
      console.log(`Skipping ${s3Key}, feedback not present yet`);
      continue;
    }

   
    if (item.user_prediction.S == item.prediction.S && Number(item.confidence.N) > 0.7) {
      console.log(`Skipping ${s3Key}, model already predicted correctly with high confidence`);
      continue;
    }

    // Fetch S3 object and compute hash
    const s3Object = await s3.send(new GetObjectCommand({ Bucket: S3_BUCKET, Key: s3Key }));
    const buffer = await streamToBuffer(s3Object.Body);
    const hash = getImageHash(buffer);

    newImages.push({ s3Key, hash });
  }

  if (newImages.length === 0) {
    console.log("No images ready for training this batch.");
    return { statusCode: 200 };
  }

  // Update batch with concurrency-safe helper
  const imagesToAdd = await updateBatchWithRetry(newImages);
  if (imagesToAdd.length === 0) {
    console.log("All images already counted in batch.");
    return { statusCode: 200 };
  }

  // Fetch updated batch to check if threshold reached
  const batchResp = await ddb.send(new GetItemCommand({
    TableName: DDB_TABLE_BATCH,
    Key: { "batch_id": { S: "current" } }
  }));
  const updatedBatch = batchResp.Item?.hashes?.SS || [];
  const updatedS3Keys = batchResp.Item?.s3_keys?.S || '';

  if (updatedBatch.length >= BATCH_THRESHOLD) {
    console.log("Threshold reached. Triggering training...");

    const ec2 = new EC2Client({ region: "ap-southeast-2" });
    await ec2.send(
      new StartInstancesCommand({
        InstanceIds: [EC2_INSTANCE]
      })
    );
    console.log("EC2 instance started");

    // Reset batch
    await ddb.send(new UpdateItemCommand({
      TableName: DDB_TABLE_BATCH,
      Key: { "batch_id": { S: "current" } },
      UpdateExpression: "SET hashes = :empty, s3_keys = :emptyKeys",
      ExpressionAttributeValues: { ":empty": { SS: ['empty'] }, ":emptyKeys": { S: "" } }
    }));

    // Store as old batch
    await ddb.send(new UpdateItemCommand({
      TableName: DDB_TABLE_BATCH,
      Key: { "batch_id": { S: "old" } },
      UpdateExpression: "SET hashes = :oldHashes, s3_keys = :oldKeys",
      ExpressionAttributeValues: { ":oldHashes": { SS: updatedBatch }, ":oldKeys": { S: updatedS3Keys } }
    }));

    console.log("Batch reset after triggering training.");
  } else {
    console.log("Batch updated but threshold not yet reached.");
  }

  return { statusCode: 200 };
};
