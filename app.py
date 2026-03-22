import os
import uuid
import json
import base64
import threading
from datetime import datetime, timezone
from pathlib import Path
from collections import deque

from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PAGES_ROOT = os.environ.get("PAGES_ROOT", "/pages")
IMAGES_THUMBNAILS = os.path.join(PAGES_ROOT, "images", "thumbnails")
IMAGES_FULLSIZE = os.path.join(PAGES_ROOT, "images", "fullsize")
MASTER_LIST = os.path.join(PAGES_ROOT, "masterList.txt")

DELETE_PASSWORD = "noodle"

VALID_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_IMAGE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_IMAGE_ERRORS = 1000

# Thread-safe image error storage
_image_errors_lock = threading.Lock()
_image_errors = deque(maxlen=MAX_IMAGE_ERRORS)


def ensure_dirs():
    """Ensure all required directories and files exist."""
    os.makedirs(IMAGES_THUMBNAILS, exist_ok=True)
    os.makedirs(IMAGES_FULLSIZE, exist_ok=True)
    master_dir = os.path.dirname(MASTER_LIST)
    os.makedirs(master_dir, exist_ok=True)
    if not os.path.exists(MASTER_LIST):
        with open(MASTER_LIST, "w") as f:
            pass


ensure_dirs()


# ---------------------------------------------------------------------------
# Image error tracking
# ---------------------------------------------------------------------------

def record_image_error(error_type, error_message, page_id=None):
    """Record an image processing error with timestamp and optional page_id.

    Args:
        error_type: Category of the error (e.g. 'decode_failure', 'invalid_format', 'size_exceeded').
        error_message: Human-readable description of the error.
        page_id: Optional page identifier associated with the error.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "page_id": page_id,
        "error_type": error_type,
        "error_message": error_message,
    }
    with _image_errors_lock:
        _image_errors.append(entry)


def get_image_errors(page_id=None, limit=100):
    """Return recent image errors, optionally filtered by page_id.

    Args:
        page_id: If provided, only errors for this page are returned.
        limit: Maximum number of errors to return.

    Returns:
        A list of error dicts, most recent first.
    """
    with _image_errors_lock:
        errors = list(_image_errors)
    if page_id is not None:
        errors = [e for e in errors if e.get("page_id") == page_id]
    errors.reverse()
    return errors[:limit]


# ---------------------------------------------------------------------------
# Helpers – filesystem
# ---------------------------------------------------------------------------

def get_page_dir(page_id):
    """Return the directory path for a given page_id based on its first three characters."""
    if len(page_id) < 3:
        a = page_id[0] if len(page_id) > 0 else "_"
        b = page_id[1] if len(page_id) > 1 else "_"
        c = page_id[2] if len(page_id) > 2 else "_"
    else:
        a, b, c = page_id[0], page_id[1], page_id[2]
    return os.path.join(PAGES_ROOT, a, b, c)


def get_page_path(page_id):
    """Return the full JSON file path for a page."""
    page_dir = get_page_dir(page_id)
    return os.path.join(page_dir, f"{page_id}.json")


def load_page(page_id):
    """Load and return a page's data from disk, or None if not found."""
    path = get_page_path(page_id)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def save_page(page_id, data):
    """Persist page data to disk as JSON."""
    page_dir = get_page_dir(page_id)
    os.makedirs(page_dir, exist_ok=True)
    path = os.path.join(page_dir, f"{page_id}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def delete_file_if_exists(path):
    """Remove a file if it exists and is a regular file."""
    if path and os.path.exists(path) and os.path.isfile(path):
        os.remove(path)


# ---------------------------------------------------------------------------
# Helpers – master list
# ---------------------------------------------------------------------------

def _metadata_to_master_line(page_id, meta):
    """Convert page metadata dict to a pipe-delimited master-list line."""
    tags = meta.get("tags", [])
    if isinstance(tags, list):
        tags_str = ",".join(tags)
    else:
        tags_str = str(tags)

    # Serialize the custom metadata object so it survives round-trip
    custom_metadata = meta.get("metadata")
    metadata_str = json.dumps(custom_metadata) if custom_metadata else ""

    line = "|".join([
        page_id,
        meta.get("title", ""),
        meta.get("location", ""),
        meta.get("age_range", ""),
        meta.get("genre", ""),
        tags_str,
        meta.get("created_at", ""),
        metadata_str,
    ])
    return line


def append_master_list(page_id, metadata):
    """Append a page entry to the master list file."""
    line = _metadata_to_master_line(page_id, metadata)
    with open(MASTER_LIST, "a") as f:
        f.write(line + "\n")


def parse_master_list():
    """Parse the master list file and return a list of entry dicts."""
    entries = []
    if not os.path.exists(MASTER_LIST):
        return entries
    with open(MASTER_LIST, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            # Ensure at least 8 parts (added metadata column)
            while len(parts) < 8:
                parts.append("")
            custom_metadata = None
            if parts[7]:
                try:
                    custom_metadata = json.loads(parts[7])
                except (json.JSONDecodeError, ValueError):
                    custom_metadata = None
            entry = {
                "page_id": parts[0],
                "title": parts[1],
                "location": parts[2],
                "age_range": parts[3],
                "genre": parts[4],
                "tags": parts[5],
                "created_at": parts[6],
                "metadata": custom_metadata,
            }
            entries.append(entry)
    return entries


def rewrite_master_list_entry(page_id, metadata):
    """Update an existing entry in the master list (rewrite the whole file)."""
    if not os.path.exists(MASTER_LIST):
        append_master_list(page_id, metadata)
        return

    new_line = _metadata_to_master_line(page_id, metadata) + "\n"
    lines = []
    found = False
    with open(MASTER_LIST, "r") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if not stripped:
                continue
            parts = stripped.split("|")
            if parts and parts[0] == page_id:
                lines.append(new_line)
                found = True
            else:
                lines.append(line if line.endswith("\n") else line + "\n")

    if not found:
        lines.append(new_line)

    with open(MASTER_LIST, "w") as f:
        f.writelines(lines)


def remove_from_master_list(page_ids):
    """Remove entries for the given page_ids from the master list."""
    if not os.path.exists(MASTER_LIST):
        return

    page_ids = set(page_ids)
    kept_lines = []

    with open(MASTER_LIST, "r") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if not stripped:
                continue
            parts = stripped.split("|")
            if parts and parts[0] not in page_ids:
                kept_lines.append(line if line.endswith("\n") else line + "\n")

    with open(MASTER_LIST, "w") as f:
        f.writelines(kept_lines)


# ---------------------------------------------------------------------------
# Helpers – images
# ---------------------------------------------------------------------------

def validate_image_extension(extension, page_id=None):
    """Validate that the image extension is allowed.

    Returns the normalised extension string or raises ValueError.
    """
    if not extension.startswith("."):
        extension = "." + extension
    extension = extension.lower()
    if extension not in VALID_IMAGE_EXTENSIONS:
        msg = f"Invalid image extension '{extension}'. Allowed: {', '.join(sorted(VALID_IMAGE_EXTENSIONS))}"
        record_image_error("invalid_format", msg, page_id=page_id)
        raise ValueError(msg)
    return extension


def save_image(image_b64, directory, page_id, extension=".png"):
    """Decode a base64-encoded image and save it to *directory*.

    Validates the extension, decodes the payload and checks size limits.
    Records image errors on failure and re-raises.

    Returns:
        The file path of the saved image.
    """
    extension = validate_image_extension(extension, page_id=page_id)

    os.makedirs(directory, exist_ok=True)
    filename = f"{page_id}{extension}"
    filepath = os.path.join(directory, filename)

    try:
        image_data = base64.b64decode(image_b64)
    except Exception as exc:
        msg = f"Failed to decode base64 image data: {exc}"
        record_image_error("decode_failure", msg, page_id=page_id)
        raise ValueError(msg) from exc

    if len(image_data) > MAX_IMAGE_SIZE_BYTES:
        msg = (
            f"Image size {len(image_data)} bytes exceeds maximum "
            f"allowed size of {MAX_IMAGE_SIZE_BYTES} bytes"
        )
        record_image_error("size_exceeded", msg, page_id=page_id)
        raise ValueError(msg)

    if len(image_data) == 0:
        msg = "Decoded image data is empty"
        record_image_error("decode_failure", msg, page_id=page_id)
        raise ValueError(msg)

    with open(filepath, "wb") as f:
        f.write(image_data)
    return filepath


def delete_page_assets(page_id, metadata=None):
    """Delete all files associated with a page (images + JSON)."""
    if metadata is None:
        metadata = load_page(page_id)

    if metadata:
        delete_file_if_exists(metadata.get("thumbnail_path", ""))
        delete_file_if_exists(metadata.get("fullsize_path", ""))

    for directory in [IMAGES_THUMBNAILS, IMAGES_FULLSIZE]:
        for ext in VALID_IMAGE_EXTENSIONS:
            candidate = os.path.join(directory, f"{page_id}{ext}")
            delete_file_if_exists(candidate)

    page_path = get_page_path(page_id)
    delete_file_if_exists(page_path)


# ---------------------------------------------------------------------------
# Helpers – responses & validation
# ---------------------------------------------------------------------------

def success_response(data, status_code=200):
    """Return a consistent success JSON response."""
    return jsonify(data), status_code


def error_response(message, status_code):
    """Return a consistent error JSON response."""
    return jsonify({"error": message, "status": status_code}), status_code


def normalize_tags(tags):
    """Normalise a tags value to a list of non-empty stripped strings."""
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]
    if isinstance(tags, list):
        return [str(t).strip() for t in tags if str(t).strip()]
    return []


def validate_metadata_field(value):
    """Validate the optional custom metadata field.

    Must be a JSON-serialisable dict (or None).  Returns the validated dict
    or raises ValueError.
    """
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("metadata must be a JSON object (dict)")
    # Ensure it round-trips through JSON (catches non-serialisable values)
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"metadata contains non-serialisable values: {exc}") from exc
    return value


def find_image_file(directory, page_id):
    """Try to locate an image file for page_id in directory.

    Returns the path if found, else None.
    """
    for ext in VALID_IMAGE_EXTENSIONS:
        candidate = os.path.join(directory, f"{page_id}{ext}")
        if os.path.exists(candidate):
            return candidate
    return None


# ---------------------------------------------------------------------------
# Routes – health
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """Health-check endpoint."""
    return success_response({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ---------------------------------------------------------------------------
# Routes – image errors
# ---------------------------------------------------------------------------

@app.route("/api/image_errors", methods=["GET"])
def list_image_errors():
    """Return recent image processing errors.

    Query params:
        limit (int): Max number of errors to return (default 100, max 1000).
    """
    try:
        limit = request.args.get("limit", 100, type=int)
        limit = max(1, min(limit, MAX_IMAGE_ERRORS))
        errors = get_image_errors(limit=limit)
        return success_response({
            "total": len(errors),
            "errors": errors,
        })
    except Exception as e:
        return error_response(f"Failed to retrieve image errors: {e}", 500)


@app.route("/api/pages/<page_id>/image_errors", methods=["GET"])
def list_page_image_errors(page_id):
    """Return image processing errors for a specific page.

    Query params:
        limit (int): Max number of errors to return (default 100, max 1000).
    """
    try:
        page_id = page_id.strip().lower()
        if not page_id:
            return error_response("page_id is required", 400)

        limit = request.args.get("limit", 100, type=int)
        limit = max(1, min(limit, MAX_IMAGE_ERRORS))
        errors = get_image_errors(page_id=page_id, limit=limit)
        return success_response({
            "page_id": page_id,
            "total": len(errors),
            "errors": errors,
        })
    except Exception as e:
        return error_response(f"Failed to retrieve image errors: {e}", 500)


# ---------------------------------------------------------------------------
# Routes – CRUD
# ---------------------------------------------------------------------------

@app.route("/api/pages", methods=["POST"])
def create_page():
    """Create a new page with optional images and metadata.

    Expects a JSON body.  Recognised top-level fields:
        title, description, location, age_range, genre, tags, creator,
        thumbnail_base64, fullsize_base64, thumbnail_extension,
        fullsize_extension, metadata (arbitrary JSON object).
    """
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return error_response("Request body must be a JSON object", 400)

        page_id = uuid.uuid4().hex.lower()
        now = datetime.now(timezone.utc).isoformat()

        # --- images ---
        thumbnail_b64 = data.pop("thumbnail_base64", None)
        fullsize_b64 = data.pop("fullsize_base64", None)

        thumbnail_path = ""
        fullsize_path = ""

        if thumbnail_b64:
            ext = data.pop("thumbnail_extension", ".png")
            try:
                thumbnail_path = save_image(thumbnail_b64, IMAGES_THUMBNAILS, page_id, ext)
            except ValueError as ve:
                return error_response(f"Thumbnail image error: {ve}", 400)

        if fullsize_b64:
            ext = data.pop("fullsize_extension", ".png")
            try:
                fullsize_path = save_image(fullsize_b64, IMAGES_FULLSIZE, page_id, ext)
            except ValueError as ve:
                return error_response(f"Full-size image error: {ve}", 400)

        data.pop("thumbnail_extension", None)
        data.pop("fullsize_extension", None)

        # --- custom metadata ---
        custom_metadata = data.pop("metadata", None)
        try:
            custom_metadata = validate_metadata_field(custom_metadata)
        except ValueError as ve:
            return error_response(str(ve), 400)

        tags = normalize_tags(data.get("tags", []))

        page_data = {
            "page_id": page_id,
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "location": data.get("location", ""),
            "age_range": data.get("age_range", ""),
            "genre": data.get("genre", ""),
            "tags": tags,
            "creator": data.get("creator", ""),
            "created_at": now,
            "updated_at": now,
            "thumbnail_path": thumbnail_path,
            "fullsize_path": fullsize_path,
            "metadata": custom_metadata,
        }

        save_page(page_id, page_data)
        append_master_list(page_id, page_data)

        return success_response({"page_id": page_id, "metadata": page_data}, 201)

    except Exception as e:
        return error_response(f"Failed to create page: {e}", 500)


@app.route("/api/pages/<page_id>", methods=["GET"])
def get_page(page_id):
    """Retrieve a single page by its id."""
    try:
        page_id = page_id.strip().lower()
        if not page_id:
            return error_response("page_id is required", 400)

        page_data = load_page(page_id)
        if page_data is None:
            return error_response("Page not found", 404)

        return success_response(page_data)
    except Exception as e:
        return error_response(f"Failed to retrieve page: {e}", 500)


@app.route("/api/pages/<page_id>/thumbnail", methods=["GET"])
def get_thumbnail(page_id):
    """Serve the thumbnail image for a page."""
    try:
        page_id = page_id.strip().lower()
        page_data = load_page(page_id)
        if page_data is None:
            return error_response("Page not found", 404)

        thumbnail_path = page_data.get("thumbnail_path", "")
        if not thumbnail_path or not os.path.exists(thumbnail_path):
            thumbnail_path = find_image_file(IMAGES_THUMBNAILS, page_id)
            if not thumbnail_path:
                return error_response("Thumbnail not found", 404)

        return send_file(thumbnail_path)
    except Exception as e:
        return error_response(f"Failed to serve thumbnail: {e}", 500)


@app.route("/api/pages/<page_id>/fullsize", methods=["GET"])
def get_fullsize(page_id):
    """Serve the full-size image for a page."""
    try:
        page_id = page_id.strip().lower()
        page_data = load_page(page_id)
        if page_data is None:
            return error_response("Page not found", 404)

        fullsize_path = page_data.get("fullsize_path", "")
        if not fullsize_path or not os.path.exists(fullsize_path):
            fullsize_path = find_image_file(IMAGES_FULLSIZE, page_id)
            if not fullsize_path:
                return error_response("Full-size image not found", 404)

        return send_file(fullsize_path)
    except Exception as e:
        return error_response(f"Failed to serve full-size image: {e}", 500)


@app.route("/api/pages/<page_id>", methods=["PUT"])
def update_page(page_id):
    """Update an existing page.

    Supports updating any standard field as well as images and the custom
    metadata object.  The metadata field is *merged* – keys present in the
    request overwrite existing keys; keys not present are retained.  To
    remove a key from metadata set it to null.
    """
    try:
        page_id = page_id.strip().lower()
        page_data = load_page(page_id)
        if page_data is None:
            return error_response("Page not found", 404)

        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return error_response("Request body must be a JSON object", 400)

        now = datetime.now(timezone.utc).isoformat()

        # --- images ---
        thumbnail_b64 = data.pop("thumbnail_base64", None)
        fullsize_b64 = data.pop("fullsize_base64", None)

        if thumbnail_b64:
            ext = data.pop("thumbnail_extension", ".png")
            try:
                page_data["thumbnail_path"] = save_image(thumbnail_b64, IMAGES_THUMBNAILS, page_id, ext)
            except ValueError as ve:
                return error_response(f"Thumbnail image error: {ve}", 400)

        if fullsize_b64:
            ext = data.pop("fullsize_extension", ".png")
            try:
                page_data["fullsize_path"] = save_image(fullsize_b64, IMAGES_FULLSIZE, page_id, ext)
            except ValueError as ve:
                return error_response(f"Full-size image error: {ve}", 400)

        data.pop("thumbnail_extension", None)
        data.pop("fullsize_extension", None)

        # --- custom metadata (merge) ---
        if "metadata" in data:
            incoming_meta = data.pop("metadata")
            try:
                incoming_meta = validate_metadata_field(incoming_meta)
            except ValueError as ve:
                return error_response(str(ve), 400)

            if incoming_meta is not None:
                existing_meta = page_data.get("metadata") or {}
                # Merge: new keys overwrite, null values remove keys
                for k, v in incoming_meta.items():
                    if v is None:
                        existing_meta.pop(k, None)
                    else:
                        existing_meta[k] = v
                page_data["metadata"] = existing_meta if existing_meta else None
            else:
                # Explicitly set to null → clear metadata
                page_data["metadata"] = None

        # --- standard fields ---
        updatable_fields = ["title", "description", "location", "age_range", "genre", "tags", "creator"]
        for field in updatable_fields:
            if field in data:
                if field == "tags":
                    page_data[field] = normalize_tags(data[field])
                else:
                    page_data[field] = data[field]

        page_data["updated_at"] = now

        save_page(page_id, page_data)
        rewrite_master_list_entry(page_id, page_data)

        return success_response(page_data)

    except Exception as e:
        return error_response(f"Failed to update page: {e}", 500)


# ---------------------------------------------------------------------------
# Routes – search & list
# ---------------------------------------------------------------------------

@app.route("/api/search", methods=["GET"])
def search_pages():
    """Search pages via the master list.

    Query params:
        location, age, genre, tags, q (title), metadata_key, metadata_value,
        limit (default 50), offset (default 0).

    The ``metadata_key`` / ``metadata_value`` pair allows filtering by a
    key inside the custom metadata object.  If only ``metadata_key`` is
    supplied the filter matches pages that have that key (any value).
    """
    try:
        location_filter = request.args.get("location", "").lower().strip()
        age_filter = request.args.get("age", "").lower().strip()
        genre_filter = request.args.get("genre", "").lower().strip()
        tags_filter = request.args.get("tags", "").lower().strip()
        q_filter = request.args.get("q", "").lower().strip()
        metadata_key = request.args.get("metadata_key", "").strip()
        metadata_value = request.args.get("metadata_value", "").strip()
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)

        limit = max(1, min(limit, 1000))
        offset = max(0, offset)

        entries = parse_master_list()
        results = []

        tag_filter_set = set()
        if tags_filter:
            tag_filter_set = {t.strip() for t in tags_filter.split(",") if t.strip()}

        for entry in entries:
            if location_filter and location_filter not in entry["location"].lower():
                continue
            if age_filter and age_filter not in entry["age_range"].lower():
                continue
            if genre_filter and genre_filter not in entry["genre"].lower():
                continue
            if tag_filter_set:
                entry_tags = {t.strip().lower() for t in entry["tags"].split(",") if t.strip()}
                if not tag_filter_set.intersection(entry_tags):
                    continue
            if q_filter and q_filter not in entry["title"].lower():
                continue

            # Custom metadata filtering
            if metadata_key:
                entry_meta = entry.get("metadata")
                if not entry_meta or not isinstance(entry_meta, dict):
                    continue
                if metadata_key not in entry_meta:
                    continue
                if metadata_value:
                    val = str(entry_meta[metadata_key]).lower()
                    if metadata_value.lower() not in val:
                        continue

            results.append(entry)

        total = len(results)
        results = results[offset:offset + limit]

        return success_response({
            "total": total,
            "offset": offset,
            "limit": limit,
            "results": results,
        })

    except Exception as e:
        return error_response(f"Search failed: {e}", 500)


@app.route("/api/pages", methods=["GET"])
def list_pages():
    """List recent pages.

    Query params:
        n (int): Number of pages to return (default 20, max 1000).
    """
    try:
        n = request.args.get("n", 20, type=int)
        n = max(1, min(n, 1000))

        entries = parse_master_list()
        recent = entries[-n:] if len(entries) >= n else list(entries)
        recent.reverse()

        return success_response({
            "total": len(entries),
            "count": len(recent),
            "pages": recent,
        })

    except Exception as e:
        return error_response(f"Failed to list pages: {e}", 500)


# ---------------------------------------------------------------------------
# Routes – delete
# ---------------------------------------------------------------------------

@app.route("/api/pages/delete", methods=["POST"])
def delete_pages():
    """Delete one or more pages.

    Expects JSON body with ``password``, and either ``id`` (string) or
    ``ids`` (list of strings).
    """
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return error_response("Request body must be a JSON object", 400)

        password = data.get("password", "")
        if password != DELETE_PASSWORD:
            return error_response("Unauthorized", 401)

        ids = data.get("ids")
        if ids is None:
            single_id = data.get("id")
            if single_id:
                ids = [single_id]

        if not ids or not isinstance(ids, list):
            return error_response('Provide "id" or "ids" as a non-empty list', 400)

        normalized_ids = []
        for page_id in ids:
            if isinstance(page_id, str):
                page_id = page_id.strip().lower()
                if page_id:
                    normalized_ids.append(page_id)

        if not normalized_ids:
            return error_response("No valid ids provided", 400)

        deleted = []
        not_found = []

        for page_id in normalized_ids:
            page_data = load_page(page_id)
            if page_data is None:
                not_found.append(page_id)
                continue

            delete_page_assets(page_id, page_data)
            deleted.append(page_id)

        if deleted:
            remove_from_master_list(deleted)

        return success_response({
            "success": True,
            "deleted": deleted,
            "not_found": not_found,
            "requested": normalized_ids,
        })

    except Exception as e:
        return error_response(f"Failed to delete pages: {e}", 500)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(400)
def bad_request(e):
    """Handle 400 Bad Request."""
    return jsonify({"error": "Bad request", "status": 400}), 400


@app.errorhandler(404)
def not_found(e):
    """Handle 404 Not Found."""
    return jsonify({"error": "Not found", "status": 404}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    """Handle 405 Method Not Allowed."""
    return jsonify({"error": "Method not allowed", "status": 405}), 405


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 Internal Server Error."""
    return jsonify({"error": "Internal server error", "status": 500}), 500


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
    )