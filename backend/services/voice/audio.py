import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status


ALLOWED_MIME_PREFIXES = ("audio/", "video/webm")
ALLOWED_EXTENSIONS = {".wav", ".webm", ".ogg", ".mp3", ".m4a", ".mp4"}


def validate_upload(upload: UploadFile, max_size_mb: int) -> None:
    if not upload.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")

    extension = Path(upload.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{extension}'.",
        )

    content_type = upload.content_type or ""
    if not any(content_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type '{content_type}'.",
        )

    upload.file.seek(0, 2)
    size = upload.file.tell()
    upload.file.seek(0)
    if size > max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size is {max_size_mb} MB.",
        )


def save_upload(upload: UploadFile, temp_dir: Path) -> Path:
    temp_dir.mkdir(parents=True, exist_ok=True)
    extension = Path(upload.filename).suffix.lower()
    output_path = temp_dir / f"{uuid4().hex}{extension}"
    with output_path.open("wb") as file_obj:
        shutil.copyfileobj(upload.file, file_obj)
    return output_path


def convert_to_wav_16k_mono(input_path: Path, temp_dir: Path) -> Path:
    output_path = temp_dir / f"{uuid4().hex}.wav"
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ffmpeg is not installed. Install ffmpeg to convert browser audio to wav.",
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to convert audio with ffmpeg: {exc.stderr}",
        ) from exc
    return output_path
