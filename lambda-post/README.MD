# Presigned POST URL API

API Gateway endpoint that returns presigned POST URLs for direct S3 uploads.

## API Request

**Method:** `GET`  
**Path:** `/presigned`  
**Query parameter:** `key` (required) — S3 object key for the upload

**Base URL:** `https://t9zrvsrj5f.execute-api.ap-south-1.amazonaws.com/prod`

**Full URL format:**
```
https://t9zrvsrj5f.execute-api.ap-south-1.amazonaws.com/prod/presigned?key=YOUR_OBJECT_KEY
```

### Examples

**cURL:**
```bash
curl "https://t9zrvsrj5f.execute-api.ap-south-1.amazonaws.com/prod/presigned?key=uploads/my-video.mp4"
```

**JavaScript (fetch):**
```javascript
const key = encodeURIComponent('uploads/my-video.mp4');
const response = await fetch(
  `https://t9zrvsrj5f.execute-api.ap-south-1.amazonaws.com/prod/presigned?key=${key}`
);
const { url, fields } = await response.json();
```

### Response

**200 OK:**
```json
{
  "url": "https://your-bucket.s3.ap-south-1.amazonaws.com/",
  "fields": {
    "key": "uploads/my-video.mp4",
    "x-amz-algorithm": "AWS4-HMAC-SHA256",
    "x-amz-credential": "...",
    "x-amz-date": "...",
    "policy": "...",
    "x-amz-signature": "..."
  }
}
```

**400 Bad Request** (missing `key`):
```json
{"error": "Missing required query parameter: key"}
```

---

## Integration with Static Websites (S3 + JavaScript only)

Works with static sites hosted on S3 (or any static host) using only JavaScript — no backend or build tools.

### 1. HTML

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Upload to S3</title>
</head>
<body>
  <input type="file" id="fileInput" accept="video/*">
  <button id="uploadBtn">Upload</button>
  <p id="status"></p>

  <script src="upload.js"></script>
</body>
</html>
```

### 2. JavaScript (`upload.js`)

```javascript
const API_BASE = 'https://t9zrvsrj5f.execute-api.ap-south-1.amazonaws.com/prod';

async function getPresignedUrl(objectKey) {
  const url = `${API_BASE}/presigned?key=${encodeURIComponent(objectKey)}`;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

async function uploadFile(file) {
  const objectKey = `uploads/${Date.now()}-${file.name}`;

  const { url, fields } = await getPresignedUrl(objectKey);

  const formData = new FormData();
  Object.entries(fields).forEach(([k, v]) => formData.append(k, v));
  formData.append('file', file);

  const uploadRes = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!uploadRes.ok) {
    throw new Error(`Upload failed: ${uploadRes.status}`);
  }

  return objectKey;
}

document.getElementById('uploadBtn').addEventListener('click', async () => {
  const input = document.getElementById('fileInput');
  const status = document.getElementById('status');

  if (!input.files.length) {
    status.textContent = 'Select a file first.';
    return;
  }

  status.textContent = 'Uploading...';
  try {
    const key = await uploadFile(input.files[0]);
    status.textContent = `Uploaded: ${key}`;
    input.value = '';
  } catch (e) {
    status.textContent = `Error: ${e.message}`;
  }
});
```

### 3. CORS

The S3 bucket must allow CORS for your site's origin. Example bucket CORS config:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["POST", "PUT"],
    "AllowedOrigins": ["https://your-site.com", "http://localhost:5500"],
    "ExposeHeaders": []
  }
]
```

For local testing, add `http://localhost:PORT` to `AllowedOrigins`.

### 4. Deploy to S3 static website

1. Enable static website hosting on the bucket.
2. Upload `index.html` and `upload.js`.
3. Use the website endpoint (e.g. `http://bucket.s3-website-region.amazonaws.com`).

The API Gateway endpoint is public; no auth is required for the presigned URL request.
