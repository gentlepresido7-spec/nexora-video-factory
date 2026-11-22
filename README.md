# NEXORA Video Factory

Approval-first, free-tier-oriented video draft builder for NEXORA.

## What this first deployment does
- Creates a three-scene creative brief, voiceover, caption and hashtag set.
- Requires explicit brief approval before assembly.
- Accepts three user-supplied scene videos or still images.
- Converts them into a vertical H.264 MP4 using FFmpeg.
- Optionally mixes user-supplied voiceover and licensed background music.
- Does not publish or schedule content and does not call paid media-generation APIs.

## Free-tier limitation
This version does **not** generate three genuine AI video scenes. No unlimited free cloud text-to-video service has been verified. It uses footage/images supplied by the operator; still images receive a simple pan/zoom treatment.

## Deploy on Render
1. Create a Blueprint from this repository.
2. Select branch `main` and `render.yaml`.
3. Review the proposed service and free plan before approving the sync.
4. After deployment, open the service URL and check `/health`.

Render free services may sleep and have resource, request-duration and ephemeral-storage limits. Large or long videos may fail. Files are processed temporarily and removed after the response.

## Local run
Requires Python 3.11+ and FFmpeg.
```bash
pip install -r requirements.txt
python app.py
```

## Production hardening still required
- Authentication and per-user isolation
- Durable object storage and background job queue
- Upload size limits and malware scanning
- Subtitle rendering and approval records
- TTS and stock-media integrations with confirmed free licensing/quotas
- OAuth and explicit approval for social publishing
