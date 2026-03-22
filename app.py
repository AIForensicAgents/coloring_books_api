import os
import uuid
import json
import base64
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PAGES_ROOT = os.environ.get("PAGES_ROOT", "/pages")
IMAGES_THUMBNAILS = os.path.join(PAGES_ROOT, "images", "thumbnails")
IMAGES_FULLSIZE = os.path.join(PAGES_ROOT, "images", "fullsize")
MASTER_LIST = os.path.join(PAGES_ROOT, "masterList.txt")


def ensure_dirs():
    os.makedirs(IMAGES_THUMBNAILS, exist_ok=True)
    os.makedirs(IMAGES_FULLSIZE, exist_ok=True)
    master_dir = os.path.dirname(MASTER_LIST)
    os.makedirs(master_dir, exist_ok=True)
    if not os.path.exists(MASTER_LIST):
        with open(MASTER_LIST, "w") as f:
            pass


ensure_dirs()


def get_page_dir(page_id):
    if len(page_id) < 3:
        a = page_id[0] if len(page_id) > 0 else "_"
        b = page_id[1] if len(page_id) > 1 else "_"
        c = page_id[2] if len(page_id) > 2 else "_"
    else:
        a, b, c = page_id[0], page_id[1], page_id[2]
    return os.path.join(PAGES_ROOT, a, b, c)


def get_page_path(page_id):
    page_dir = get_page_dir(page_id)
    return os.path.join(page_dir, f"{page_id}.json")


def load_page(page_id):
    path = get_page_path(page_id)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        data = json.load(f)
    if "image_errors" not in data:
        data["image_errors"] = None
    return data


def save_page(page_id, data):
    page_dir = get_page_dir(page_id)
    os.makedirs(page_dir, exist_ok=True)
    path = os.path.join(page_dir, f"{page_id}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def append_master_list(page_id, metadata):
    tags = metadata.get("tags", [])
    if isinstance(tags, list):
        tags_str = ",".join(tags)
    else:
        tags_str = str(tags)
    line = "|".join([
        page_id,
        metadata.get("title", ""),
        metadata.get("location", ""),
        metadata.get("age_range", ""),
        metadata.get("genre", ""),
        tags_str,
        metadata.get("created_at", ""),
    ])
    with open(MASTER_LIST, "a") as f:
        f.write(line + "\n")


def parse_master_list():
    entries = []
    if not os.path.exists(MASTER_LIST):
        return entries
    with open(MASTER_LIST, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 7:
                parts.extend([""] * (7 - len(parts)))
            entry = {
                "page_id": parts[0],
                "title": parts[1],
                "location": parts[2],
                "age_range": parts[3],
                "genre": parts[4],
                "tags": parts[5],
                "created_at": parts[6],
            }
            entries.append(entry)
    return entries


def save_image(image_b64, directory, page_id, extension=".png"):
    os.makedirs(directory, exist_ok=True)
    filename = f"{page_id}{extension}"
    filepath = os.path.join(directory, filename)
    image_data = base64.b64decode(image_b64)
    with open(filepath, "wb") as f:
        f.write(image_data)
    return filepath


def error_response(message, status_code):
    return jsonify({"error": message}), status_code


DELETE_PASSWORD = "noodle"


def delete_file_if_exists(path):
    if path and os.path.exists(path) and os.path.isfile(path):
        os.remove(path)


def remove_from_master_list(page_ids):
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
                kept_lines.append(line)

    with open(MASTER_LIST, "w") as f:
        f.writelines(kept_lines)


def delete_page_assets(page_id, metadata=None):
    if metadata is None:
        metadata = load_page(page_id)

    if metadata:
        delete_file_if_exists(metadata.get("thumbnail_path", ""))
        delete_file_if_exists(metadata.get("fullsize_path", ""))

    for directory in [IMAGES_THUMBNAILS, IMAGES_FULLSIZE]:
        for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
            candidate = os.path.join(directory, f"{page_id}{ext}")
            delete_file_if_exists(candidate)

    page_path = get_page_path(page_id)
    delete_file_if_exists(page_path)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()})


@app.route("/api/pages", methods=["POST"])
def create_page():
    try:
        data = request.get_json()
        if not data:
            return error_response("Request body must be JSON", 400)

        page_id = uuid.uuid4().hex.lower()
        now = datetime.now(timezone.utc).isoformat()

        thumbnail_b64 = data.pop("thumbnail_base64", None)
        fullsize_b64 = data.pop("fullsize_base64", None)

        thumbnail_path = ""
        fullsize_path = ""

        if thumbnail_b64:
            ext = data.get("thumbnail_extension", ".png")
            thumbnail_path = save_image(thumbnail_b64, IMAGES_THUMBNAILS, page_id, ext)

        if fullsize_b64:
            ext = data.get("fullsize_extension", ".png")
            fullsize_path = save_image(fullsize_b64, IMAGES_FULLSIZE, page_id, ext)

        data.pop("thumbnail_extension", None)
        data.pop("fullsize_extension", None)

        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        metadata = {
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
            "image_errors": data.get("image_errors", None),
        }

        save_page(page_id, metadata)
        append_master_list(page_id, metadata)

        return jsonify({"page_id": page_id, "metadata": metadata}), 201

    except Exception as e:
        return error_response(f"Failed to create page: {str(e)}", 500)


@app.route("/api/pages/<page_id>", methods=["GET"])
def get_page(page_id):
    try:
        metadata = load_page(page_id)
        if metadata is None:
            return error_response("Page not found", 404)
        return jsonify(metadata), 200
    except Exception as e:
        return error_response(f"Failed to retrieve page: {str(e)}", 500)


@app.route("/api/pages/<page_id>/thumbnail", methods=["GET"])
def get_thumbnail(page_id):
    try:
        metadata = load_page(page_id)
        if metadata is None:
            return error_response("Page not found", 404)

        thumbnail_path = metadata.get("thumbnail_path", "")
        if not thumbnail_path or not os.path.exists(thumbnail_path):
            found = False
            for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                candidate = os.path.join(IMAGES_THUMBNAILS, f"{page_id}{ext}")
                if os.path.exists(candidate):
                    thumbnail_path = candidate
                    found = True
                    break
            if not found:
                return error_response("Thumbnail not found", 404)

        return send_file(thumbnail_path)
    except Exception as e:
        return error_response(f"Failed to serve thumbnail: {str(e)}", 500)


@app.route("/api/pages/<page_id>/fullsize", methods=["GET"])
def get_fullsize(page_id):
    try:
        metadata = load_page(page_id)
        if metadata is None:
            return error_response("Page not found", 404)

        fullsize_path = metadata.get("fullsize_path", "")
        if not fullsize_path or not os.path.exists(fullsize_path):
            found = False
            for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
                candidate = os.path.join(IMAGES_FULLSIZE, f"{page_id}{ext}")
                if os.path.exists(candidate):
                    fullsize_path = candidate
                    found = True
                    break
            if not found:
                return error_response("Full-size image not found", 404)

        return send_file(fullsize_path)
    except Exception as e:
        return error_response(f"Failed to serve full-size image: {str(e)}", 500)


@app.route("/api/pages/<page_id>", methods=["PUT"])
def update_page(page_id):
    try:
        metadata = load_page(page_id)
        if metadata is None:
            return error_response("Page not found", 404)

        data = request.get_json()
        if not data:
            return error_response("Request body must be JSON", 400)

        now = datetime.now(timezone.utc).isoformat()

        thumbnail_b64 = data.pop("thumbnail_base64", None)
        fullsize_b64 = data.pop("fullsize_base64", None)

        if thumbnail_b64:
            ext = data.pop("thumbnail_extension", ".png")
            metadata["thumbnail_path"] = save_image(thumbnail_b64, IMAGES_THUMBNAILS, page_id, ext)

        if fullsize_b64:
            ext = data.pop("fullsize_extension", ".png")
            metadata["fullsize_path"] = save_image(fullsize_b64, IMAGES_FULLSIZE, page_id, ext)

        data.pop("thumbnail_extension", None)
        data.pop("fullsize_extension", None)

        updatable_fields = ["title", "description", "location", "age_range", "genre", "tags", "creator", "image_errors"]
        for field in updatable_fields:
            if field in data:
                if field == "tags" and isinstance(data[field], str):
                    metadata[field] = [t.strip() for t in data[field].split(",") if t.strip()]
                else:
                    metadata[field] = data[field]

        metadata["updated_at"] = now

        save_page(page_id, metadata)

        return jsonify(metadata), 200

    except Exception as e:
        return error_response(f"Failed to update page: {str(e)}", 500)


@app.route("/api/search", methods=["GET"])
def search_pages():
    try:
        location_filter = request.args.get("location", "").lower().strip()
        age_filter = request.args.get("age", "").lower().strip()
        genre_filter = request.args.get("genre", "").lower().strip()
        tags_filter = request.args.get("tags", "").lower().strip()
        q_filter = request.args.get("q", "").lower().strip()
        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)

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
            results.append(entry)

        total = len(results)
        results = results[offset:offset + limit]

        return jsonify({
            "total": total,
            "offset": offset,
            "limit": limit,
            "results": results,
        }), 200

    except Exception as e:
        return error_response(f"Search failed: {str(e)}", 500)


@app.route("/api/pages", methods=["GET"])
def list_pages():
    try:
        n = request.args.get("n", 20, type=int)
        if n < 1:
            n = 1
        if n > 1000:
            n = 1000

        entries = parse_master_list()
        recent = entries[-n:] if len(entries) >= n else entries
        recent.reverse()

        return jsonify({
            "total": len(entries),
            "count": len(recent),
            "pages": recent,
        }), 200

    except Exception as e:
        return error_response(f"Failed to list pages: {str(e)}", 500)


@app.route("/api/pages/delete", methods=["POST"])
def delete_pages():
    try:
        data = request.get_json()
        if not data:
            return error_response("Request body must be JSON", 400)

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
            metadata = load_page(page_id)
            if metadata is None:
                not_found.append(page_id)
                continue

            delete_page_assets(page_id, metadata)
            deleted.append(page_id)

        if deleted:
            remove_from_master_list(deleted)

        return jsonify({
            "success": True,
            "deleted": deleted,
            "not_found": not_found,
            "requested": normalized_ids,
        }), 200

    except Exception as e:
        return error_response(f"Failed to delete pages: {str(e)}", 500)


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")