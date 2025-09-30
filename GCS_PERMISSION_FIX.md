# Quick Fix Guide for GCS Permission Issue

## Problem
Your service account `voicely-473515-gserviceaccount@voicely-473515.iam.gserviceaccount.com` doesn't have permission to create objects in the GCS bucket `voicely-bucket-cloud`.

## Solution Options

### Option 1: Fix via Google Cloud Console (Easiest)

1. **Go to Google Cloud Console**
   - Open https://console.cloud.google.com/
   - Select project: `voicely-473515`

2. **Fix Service Account Permissions**
   ```
   Navigation: IAM & Admin → IAM
   
   Steps:
   1. Find service account: voicely-473515-gserviceaccount@voicely-473515.iam.gserviceaccount.com
   2. Click the "Edit" button (pencil icon)
   3. Click "ADD ANOTHER ROLE"
   4. Search for and select: "Storage Object Admin"
   5. Click "SAVE"
   ```

3. **Alternative: Bucket-level permissions**
   ```
   Navigation: Cloud Storage → Buckets → voicely-bucket-cloud
   
   Steps:
   1. Click on bucket name "voicely-bucket-cloud"
   2. Go to "PERMISSIONS" tab
   3. Click "GRANT ACCESS"
   4. Principal: voicely-473515-gserviceaccount@voicely-473515.iam.gserviceaccount.com
   5. Role: Storage Object Admin
   6. Click "SAVE"
   ```

### Option 2: Fix via gcloud CLI

If you have gcloud CLI installed:

```bash
# Grant Storage Object Admin role to service account
gcloud projects add-iam-policy-binding voicely-473515 \
    --member="serviceAccount:voicely-473515-gserviceaccount@voicely-473515.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Verify the permissions
gcloud projects get-iam-policy voicely-473515 \
    --flatten="bindings[].members" \
    --format='table(bindings.role)' \
    --filter="bindings.members:voicely-473515-gserviceaccount@voicely-473515.iam.gserviceaccount.com"
```

### Option 3: Alternative Bucket-level Permission (More restrictive)

```bash
# Grant bucket-specific permissions
gsutil iam ch serviceAccount:voicely-473515-gserviceaccount@voicely-473515.iam.gserviceaccount.com:objectAdmin gs://voicely-bucket-cloud
```

## Required Permissions

Your service account needs these specific permissions for the transcription system:

- ✅ **speech.client** (already working)
- ❌ **storage.objects.create** (missing - causes the error)
- ❌ **storage.objects.delete** (needed for cleanup)
- ❌ **storage.objects.get** (needed for reading)

The **Storage Object Admin** role includes all these permissions.

## Test After Fix

After applying the permissions, test with:

```bash
# Get auth token
curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email":"your-email","password":"your-password"}'

# Test transcription (use the token from above)
curl -X POST "http://localhost:8000/transcript/transcribe" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"audio_id": 2, "language_code": "vi-VN"}'
```

## Current Fallback

The system now includes fallback logic:
- If GCS fails and file is ≤ 2MB and ≤ 5 minutes, it will try direct transcription
- Otherwise, it will show the GCS permission error with instructions

## Next Steps

1. Fix the GCS permissions using Option 1 above
2. Test the transcription endpoint
3. If still having issues, check the application logs: `docker logs voicely_app`