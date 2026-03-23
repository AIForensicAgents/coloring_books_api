import os
import uuid
import json
import random
import base64
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PAGES_ROOT = os.environ.get("PAGES_ROOT", "/pages")
IMAGES_THUMBNAILS = os.path.join(PAGES_ROOT, "images", "thumbnails")
IMAGES_FULLSIZE = os.path.join(PAGES_ROOT, "images", "fullsize")

# Change from txt to json cache
MASTER_LIST = os.path.join(PAGES_ROOT, "master_index.json")


def ensure_dirs():
    os.makedirs(IMAGES_THUMBNAILS, exist_ok=True)
    os.makedirs(IMAGES_FULLSIZE, exist_ok=True)
    os.makedirs(PAGES_ROOT, exist_ok=True)
    if not os.path.exists(MASTER_LIST):
        atomic_write_json(MASTER_LIST, {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "entries": []
        })


def atomic_write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


ensure_dirs()


def get_page_dir(page_id):
    a = page_id[0] if len(page_id) > 0 else "_"
    b = page_id[1] if len(page_id) > 1 else "_"
    c = page_id[2] if len(page_id) > 2 else "_"
    return os.path.join(PAGES_ROOT, a, b, c)


def get_page_path(page_id):
    return os.path.join(get_page_dir(page_id), f"{page_id}.json")


def page_to_index_entry(metadata):
    tags = metadata.get("tags", [])
    if not isinstance(tags, list):
        tags = [str(tags)] if tags else []

    return {
        "page_id": metadata.get("page_id", ""),
        "title": metadata.get("title", ""),
        "location": metadata.get("location", ""),
        "age_range": metadata.get("age_range", ""),
        "genre": metadata.get("genre", ""),
        "tags": tags,
        "created_at": metadata.get("created_at", ""),
        "updated_at": metadata.get("updated_at", ""),
    }


def load_page(page_id):
    path = get_page_path(page_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_page(page_id, data):
    page_dir = get_page_dir(page_id)
    os.makedirs(page_dir, exist_ok=True)
    atomic_write_json(os.path.join(page_dir, f"{page_id}.json"), data)


def iter_page_files():
    for root, dirs, files in os.walk(PAGES_ROOT):
        # skip image dirs
        if root.startswith(IMAGES_THUMBNAILS) or root.startswith(IMAGES_FULLSIZE):
            continue
        for name in files:
            if not name.endswith(".json"):
                continue
            full_path = os.path.join(root, name)
            if os.path.abspath(full_path) == os.path.abspath(MASTER_LIST):
                continue
            yield full_path


def rebuild_master_index():
    entries = []

    for path in iter_page_files():
        try:
            with open(path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            page_id = metadata.get("page_id", "")
            if not page_id:
                continue

            entries.append(page_to_index_entry(metadata))
        except Exception:
            # skip bad file instead of killing whole index rebuild
            continue

    entries.sort(
        key=lambda x: (x.get("created_at") or "", x.get("page_id") or ""),
        reverse=False
    )

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries
    }
    atomic_write_json(MASTER_LIST, payload)
    return entries


def load_master_index():
    if not os.path.exists(MASTER_LIST):
        return rebuild_master_index()

    try:
        with open(MASTER_LIST, "r", encoding="utf-8") as f:
            payload = json.load(f)

        entries = payload.get("entries", [])
        if not isinstance(entries, list):
            return rebuild_master_index()

        return entries
    except Exception:
        # auto-heal corrupted index
        return rebuild_master_index()


def upsert_master_index_entry(metadata):
    entry = page_to_index_entry(metadata)
    entries = load_master_index()

    by_id = {e.get("page_id", ""): e for e in entries if e.get("page_id")}
    by_id[entry["page_id"]] = entry

    merged = list(by_id.values())
    merged.sort(
        key=lambda x: (x.get("created_at") or "", x.get("page_id") or ""),
        reverse=False
    )

    atomic_write_json(MASTER_LIST, {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "entries": merged
    })


def remove_from_master_index(page_ids):
    page_ids = {p.strip().lower() for p in page_ids if isinstance(p, str) and p.strip()}
    entries = load_master_index()
    kept = [e for e in entries if e.get("page_id", "").lower() not in page_ids]

    atomic_write_json(MASTER_LIST, {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "entries": kept
    })


def parse_master_list():
    return load_master_index()


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

    delete_file_if_exists(get_page_path(page_id))


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@app.route("/api/admin/rebuild-index", methods=["POST"])
def rebuild_index():
    try:
        data = request.get_json(silent=True) or {}
        password = data.get("password", "")
        if password != DELETE_PASSWORD:
            return error_response("Unauthorized", 401)

        entries = rebuild_master_index()
        return jsonify({
            "success": True,
            "total": len(entries)
        }), 200
    except Exception as e:
        return error_response(f"Failed to rebuild index: {str(e)}", 500)


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
        }

        save_page(page_id, metadata)
        upsert_master_index_entry(metadata)

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

        for field in ["title", "description", "location", "age_range", "genre", "tags", "creator"]:
            if field in data:
                if field == "tags" and isinstance(data[field], str):
                    metadata[field] = [t.strip() for t in data[field].split(",") if t.strip()]
                else:
                    metadata[field] = data[field]

        metadata["updated_at"] = now

        save_page(page_id, metadata)
        upsert_master_index_entry(metadata)

        return jsonify(metadata), 200

    except Exception as e:
        return error_response(f"Failed to update page: {str(e)}", 500)


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
            remove_from_master_index(deleted)

        return jsonify({
            "success": True,
            "deleted": deleted,
            "not_found": not_found,
            "requested": normalized_ids
        }), 200

    except Exception as e:
        return error_response(f"Failed to delete pages: {str(e)}", 500)


@app.route("/api/pages", methods=["GET"])
def list_pages():
    try:
        n = request.args.get("n", 20, type=int)
        random_mode = request.args.get("random", "false").lower() == "true"

        if n < 1:
            n = 1
        if n > 1000:
            n = 1000

        entries = parse_master_list()

        if random_mode:
            if len(entries) <= n:
                selected = entries[:]
                random.shuffle(selected)
            else:
                selected = random.sample(entries, n)
        else:
            selected = entries[-n:] if len(entries) >= n else entries
            selected = list(reversed(selected))

        return jsonify({
            "total": len(entries),
            "count": len(selected),
            "pages": selected,
            "mode": "random" if random_mode else "recent"
        }), 200

    except Exception as e:
        return error_response(f"Failed to list pages: {str(e)}", 500)


@app.route("/api/entries", methods=["GET"])
def list_entries():
    try:
        entries = parse_master_list()
        return jsonify({
            "total": len(entries),
            "entries": entries
        }), 200
    except Exception as e:
        return error_response(f"Failed to list entries: {str(e)}", 500)


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
        random_mode = request.args.get("random", "false").lower() == "true"

        if limit < 1:
            limit = 1
        if limit > 1000:
            limit = 1000
        if offset < 0:
            offset = 0

        entries = parse_master_list()
        results = []

        tag_filter_set = set()
        if tags_filter:
            tag_filter_set = {t.strip().lower() for t in tags_filter.split(",") if t.strip()}

        for entry in entries:
            if location_filter and location_filter not in entry.get("location", "").lower():
                continue
            if age_filter and age_filter not in entry.get("age_range", "").lower():
                continue
            if genre_filter and genre_filter not in entry.get("genre", "").lower():
                continue
            if tag_filter_set:
                entry_tags = {t.strip().lower() for t in entry.get("tags", []) if str(t).strip()}
                if not tag_filter_set.intersection(entry_tags):
                    continue
            if q_filter and q_filter not in entry.get("title", "").lower():
                continue
            results.append(entry)

        total = len(results)

        if random_mode:
            pool = results[offset:] if offset > 0 else results
            if len(pool) <= limit:
                selected = pool[:]
                random.shuffle(selected)
            else:
                selected = random.sample(pool, limit)
        else:
            selected = results[offset:offset + limit]

        return jsonify({
            "total": total,
            "offset": offset,
            "limit": limit,
            "mode": "random" if random_mode else "paged",
            "results": selected,
        }), 200

    except Exception as e:
        return error_response(f"Search failed: {str(e)}", 500)


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
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    )
