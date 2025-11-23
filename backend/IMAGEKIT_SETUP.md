# ImageKit Integration Setup

This project uses ImageKit for image storage and delivery. ImageKit provides optimized image delivery via CDN.

## Setup Instructions

### 1. Create an ImageKit Account

1. Go to [ImageKit.io](https://imagekit.io) and sign up for a free account
2. After signing up, you'll get access to your dashboard

### 2. Get Your ImageKit Credentials

From your ImageKit dashboard, you'll need:

1. **Public Key** - Found in Settings → Developer Options → Public Key
2. **Private Key** - Found in Settings → Developer Options → Private Key
3. **URL Endpoint** - Found in Settings → URL Endpoint (e.g., `https://ik.imagekit.io/your_imagekit_id`)

### 3. Configure Environment Variables

Add these to your `.env` file in the `backend` directory:

```env
IMAGEKIT_PUBLIC_KEY=your_public_key_here
IMAGEKIT_PRIVATE_KEY=your_private_key_here
IMAGEKIT_URL_ENDPOINT=https://ik.imagekit.io/your_imagekit_id
```

**Important**: Never commit your `.env` file to version control!

### 4. Install Dependencies

The ImageKit SDK is already added to `pyproject.toml`. Install it:

```bash
cd backend
uv sync
# or
pip install imagekitio python-multipart
```

### 5. Restart Your Server

After setting up the environment variables, restart your FastAPI server.

## How It Works

1. **Frontend**: When a user selects an image, it's uploaded to `/images/upload` endpoint
2. **Backend**: The image is uploaded to ImageKit and returns an ImageKit URL
3. **Storage**: The ImageKit URL is stored in the database (not the image itself)
4. **Delivery**: Images are served via ImageKit's CDN with automatic optimization

## API Endpoint

### Upload Image

```http
POST /images/upload
Content-Type: multipart/form-data

file: <image file>
```

**OR**

```http
POST /images/upload
Content-Type: application/x-www-form-urlencoded

base64_image: <base64 encoded image>
```

**Response:**
```json
{
  "url": "https://ik.imagekit.io/your_id/cocktails/image_abc123.jpg",
  "file_id": "file_id_from_imagekit",
  "name": "image_abc123.jpg"
}
```

## Benefits

- **CDN Delivery**: Images are served from ImageKit's global CDN
- **Automatic Optimization**: Images are automatically optimized for web
- **Transformations**: Can add URL parameters for resizing, cropping, etc.
- **No Database Bloat**: Only URLs stored, not image data
- **Better Performance**: Faster page loads with optimized images

## Image Transformations

You can add ImageKit transformations to URLs. For example:

- Resize: `https://ik.imagekit.io/.../image.jpg?tr=w-300,h-300`
- Crop: `https://ik.imagekit.io/.../image.jpg?tr=c-at_max,w-300,h-300`
- Quality: `https://ik.imagekit.io/.../image.jpg?tr=q-80`

See [ImageKit Transformations Documentation](https://docs.imagekit.io/features/image-transformations) for more options.

