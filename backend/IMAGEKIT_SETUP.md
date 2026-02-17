# Image Storage

Cocktail images are stored as binary data in the database (table `images`: `id`, `data`, `content_type`).

- **Upload**: `POST /images/upload` accepts either a `file` (multipart) or `base64_image` (form). The image is saved to the `images` table and the response returns `{ "url": "/images/serve/{id}", "id", "name" }`. The frontend stores this URL in `cocktail_recipes.picture_url`.
- **Serve**: `GET /images/serve/{image_id}` returns the image binary with the appropriate `Content-Type`. No auth required so `<img src="...">` works.
- **Legacy**: Existing rows with `picture_url` pointing to external URLs (e.g. ImageKit) continue to work; the frontend uses those URLs as-is when they start with `http`.
