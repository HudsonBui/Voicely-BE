# Google Cloud Storage Setup Guide for Long Audio Transcription

This guide explains how to set up Google Cloud Storage (GCS) integration to enable transcription of large audio files (> 1MB or > 60 seconds).

## Overview

Google Cloud Speech-to-Text API has different limits based on the recognition method:

- **Synchronous Recognition**: ≤ 60 seconds, ≤ 10MB (direct upload)
- **Asynchronous Recognition (Direct)**: > 60 seconds, ≤ 1MB (direct upload)  
- **Asynchronous Recognition (GCS)**: Any size, up to 480 minutes (requires Cloud Storage)

## Prerequisites

1. Google Cloud Platform account
2. Google Cloud Speech-to-Text API enabled
3. Google Cloud Storage API enabled
4. Service account with appropriate permissions

## Step 1: Create a Google Cloud Storage Bucket

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **Cloud Storage** > **Buckets**
3. Click **CREATE BUCKET**
4. Choose a unique bucket name (e.g., `your-project-audio-transcription`)
5. Select a region close to your application
6. Choose **Standard** storage class
7. Set **Uniform** access control
8. Click **CREATE**

## Step 2: Set Up Service Account Permissions

Your service account needs these IAM roles:

```bash
# Grant Speech API permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/speech.client"

# Grant Storage permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

Or assign these roles via the Console:
- **Cloud Speech Client** - for Speech-to-Text API access
- **Storage Object Admin** - for uploading/deleting files in your bucket

## Step 3: Configure Environment Variables

Update your `.env` file:

```bash
# Google Cloud Authentication
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json

# Google Cloud Storage Configuration
GCS_BUCKET_NAME=your-bucket-name-here
```

## Step 4: Install Dependencies

The required dependencies are already in `requirements.txt`:

```bash
pip install google-cloud-speech google-cloud-storage
```

## Step 5: Test the Configuration

1. Restart your application:
```bash
docker compose restart app
```

2. Check if GCS is available:
```bash
curl -X GET "http://localhost:8000/transcript/check/AUDIO_ID" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

The response should show `"gcs_available": true` for large files.

## How It Works

### File Size Decision Matrix

| File Size | Duration | Method | GCS Required |
|-----------|----------|---------|--------------|
| ≤ 10MB    | ≤ 60s    | Synchronous | No |
| ≤ 1MB     | > 60s    | Asynchronous Direct | No |
| > 1MB     | Any      | Asynchronous GCS | **Yes** |
| Any       | > 60s AND > 1MB | Asynchronous GCS | **Yes** |

### Transcription Process for Large Files

1. **Upload Phase**: File is temporarily uploaded to your GCS bucket
2. **Transcription Phase**: Google Speech API processes the file from GCS
3. **Cleanup Phase**: File is automatically deleted from GCS after transcription

## Security Considerations

1. **Bucket Access**: Use uniform bucket-level access control
2. **Service Account**: Follow the principle of least privilege
3. **Cleanup**: Files are automatically deleted after processing
4. **Retention**: Consider setting bucket lifecycle policies for additional cleanup

## Troubleshooting

### Common Issues

**"GCS not configured"**: 
- Check `GCS_BUCKET_NAME` environment variable
- Verify bucket exists and is accessible

**"Permission denied"**:
- Verify service account has `Storage Object Admin` role
- Check bucket permissions

**"Bucket not found"**:
- Verify bucket name is correct
- Ensure bucket is in the same project as your service account

### Debug Steps

1. Check environment variables:
```bash
docker exec voicely_app env | grep GCS
```

2. Test bucket access:
```bash
# From inside the container
gsutil ls gs://your-bucket-name
```

3. Check application logs:
```bash
docker logs voicely_app
```

## Cost Considerations

- **Storage**: Minimal cost for temporary file storage (files are deleted after processing)
- **Operations**: Small cost for upload/delete operations
- **Speech API**: Standard Speech-to-Text pricing applies

For detailed pricing, see:
- [Google Cloud Storage Pricing](https://cloud.google.com/storage/pricing)
- [Google Cloud Speech-to-Text Pricing](https://cloud.google.com/speech-to-text/pricing)

## Example Usage

Once configured, large audio files will automatically use GCS:

```bash
# This will now work for files > 1MB or > 60s
curl -X POST "http://localhost:8000/transcript/transcribe" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"audio_id": 123, "language_code": "en-US"}'
```

The system will automatically:
1. Detect the file is too large for direct upload
2. Upload it to your GCS bucket
3. Use GCS-based asynchronous transcription
4. Clean up the temporary file
5. Return the transcription results