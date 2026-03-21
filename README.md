<!-- OG Meta Tags -->
<!-- <meta property="og:title" content="Coloring Books API - AI-Powered Coloring Page Management API"> -->
<!-- <meta property="og:description" content="A RESTful API for creating, managing, searching, and serving coloring book pages with image storage, metadata management, and powerful search capabilities."> -->
<!-- <meta property="og:type" content="website"> -->
<!-- <meta property="og:url" content="https://github.com/AIForensicAgents/coloring_books_api"> -->
<!-- <meta property="og:image" content="https://raw.githubusercontent.com/AIForensicAgents/coloring_books_api/main/og-image.png"> -->
<!-- <meta name="twitter:card" content="summary_large_image"> -->
<!-- <meta name="twitter:title" content="Coloring Books API"> -->
<!-- <meta name="twitter:description" content="RESTful API for managing coloring book pages with image storage, metadata, and search."> -->

<div align="center">

# 🎨 Coloring Books API

### *A RESTful API for Creating, Managing & Serving Coloring Book Pages*

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![API](https://img.shields.io/badge/API-REST-blue?style=for-the-badge&logo=fastapi&logoColor=white)](/)
[![CORS](https://img.shields.io/badge/CORS-Enabled-orange?style=for-the-badge)](/)

---

*Built with ❤️ by [AIForensicAgents](https://github.com/AIForensicAgents)*

Upload coloring book pages with thumbnails & full-size images, enrich them with metadata like age range, genre, location & tags — then search, browse, and serve them through a clean JSON API.

[Getting Started](#-getting-started) •
[API Docs](#-api-endpoints) •
[Examples](#-usage-examples) •
[Contributing](#-contributing)

</div>

---

## 📖 Overview

**Coloring Books API** is a lightweight, file-based REST API designed to manage a library of coloring book pages. It handles everything from image storage (thumbnails & full-size) to rich metadata management and full-text search — all without requiring a traditional database.

Pages are stored as JSON files in a sharded directory structure for scalability, images are stored separately in organized directories, and a master list file enables fast searching and browsing.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🖼️ **Dual Image Storage** | Upload both thumbnail and full-size images as base64 — served as binary files |
| 📝 **Rich Metadata** | Title, description, location, age range, genre, tags, and creator fields |
| 🔍 **Powerful Search** | Filter by location, age, genre, tags, or free-text query with pagination |
| 📂 **Sharded File Storage** | Pages stored in a 3-level directory tree for filesystem scalability |
| 📋 **Master List Index** | Flat-file index for fast listing and search without scanning directories |
| 🗑️ **Secure Deletion** | Password-protected bulk delete with full asset cleanup |
| 🌐 **CORS Enabled** | Ready for cross-origin frontend consumption out of the box |
| 💚 **Health Check** | Built-in health endpoint for monitoring and load balancers |
| 🐳 **Container Ready** | Configurable via environment variables, runs on `0.0.0.0:8080` |

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.9+** | Runtime |
| **Flask** | Web framework |
| **Flask-CORS** | Cross-Origin Resource Sharing |
| **UUID4** | Unique page ID generation |
| **Base64** | Image encoding/decoding for upload |
| **File System** | Persistence layer (JSON + image files) |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/AIForensicAgents/coloring_books_api.git
cd coloring_books_api

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install flask flask-cors
```

### Running the Server

```bash
# Default run
python app.py

# With custom pages directory
PAGES_ROOT=/path/to/storage python app.py

# With debug mode
FLASK_DEBUG=true python app.py
```

The API will be available at `http://localhost:8080`.

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PAGES_ROOT` | `/pages` | Root directory for all file storage (pages, images, master list) |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode (`true` / `false`) |

### Directory Structure Created Automatically

```
$PAGES_ROOT/
├── masterList.txt                    # Flat-file search index
├── images/
│   ├── thumbnails/                   # Thumbnail images
│   │   └── <page_id>.png
│   └── fullsize/                     # Full-size images
│       └── <page_id>.png
├── a/                                # Sharded page directories
│   └── b/
│       └── c/
│           └── abc123...json
```

---

## 📡 API Endpoints

### Quick Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/pages` | Create a new coloring page |
| `GET` | `/api/pages` | List recent pages |
| `GET` | `/api/pages/<page_id>` | Get page metadata |
| `PUT` | `/api/pages/<page_id>` | Update page metadata/images |
| `GET` | `/api/pages/<page_id>/thumbnail` | Serve thumbnail image |
| `GET` | `/api/pages/<page_id>/fullsize` | Serve full-size image |
| `GET` | `/api/search` | Search pages with filters |
| `POST` | `/api/pages/delete` | Delete pages (password-protected) |

---

### 💚 Health Check

Check if the API is running and responsive.

**`GET /health`**

#### Response

```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00.000000+00:00"
}
```

#### Example

```bash
curl http://localhost:8080/health
```

---

### 📄 Create Page

Create a new coloring book page with metadata and optional images.

**`POST /api/pages`**

#### Request Body (JSON)

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | No | Page title |
| `description` | string | No | Page description |
| `location` | string | No | Geographic location or theme location |
| `age_range` | string | No | Target age range (e.g., `"3-5"`, `"6-8"`) |
| `genre` | string | No | Genre/category (e.g., `"animals"`, `"fantasy"`) |
| `tags` | array or string | No | Tags as an array or comma-separated string |
| `creator` | string | No | Creator/artist name |
| `thumbnail_base64` | string | No | Base64-encoded thumbnail image |
| `thumbnail_extension` | string | No | Thumbnail file extension (default: `".png"`) |
| `fullsize_base64` | string | No | Base64-encoded full-size image |
| `fullsize_extension` | string | No | Full-size file extension (default: `".png"`) |

#### Response — `201 Created`

```json
{
  "page_id": "a1b2c3d4e5f6...",
  "metadata": {
    "page_id": "a1b2c3d4e5f6...",
    "title": "Friendly Dragon",
    "description": "A cute dragon in a meadow",
    "location": "fantasy-land",
    "age_range": "3-5",
    "genre": "fantasy",
    "tags": ["dragon", "cute", "meadow"],
    "creator": "ArtistBot",
    "created_at": "2025-01-15T10:30:00.000000+00:00",
    "updated_at": "2025-01-15T10:30:00.000000+00:00",
    "thumbnail_path": "/pages/images/thumbnails/a1b2c3d4e5f6....png",
    "fullsize_path": "/pages/images/fullsize/a1b2c3d4e5f6....png"
  }
}
```

#### Example

```bash
# Create a page with metadata only
curl -X POST http://localhost:8080/api/pages \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Friendly Dragon",
    "description": "A cute dragon in a meadow",
    "location": "fantasy-land",
    "age_range": "3-5",
    "genre": "fantasy",
    "tags": ["dragon", "cute", "meadow"],
    "creator": "ArtistBot"
  }'

# Create a page with a thumbnail image (base64)
curl -X POST http://localhost:8080/api/pages \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Ocean Friends",
    "genre": "animals",
    "tags": "fish,ocean,underwater",
    "thumbnail_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
    "thumbnail_extension": ".png",
    "fullsize_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
    "fullsize_extension": ".png"
  }'
```

---

### 📋 List Pages

Retrieve the most recently created pages.

**`GET /api/pages`**

#### Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `n` | integer | `20` | Number of recent pages to return (1–1000) |

#### Response — `200 OK`

```json
{
  "total": 150,
  "count": 20,
  "pages": [
    {
      "page_id": "a1b2c3d4e5f6...",
      "title": "Friendly Dragon",
      "location": "fantasy-land",
      "age_range": "3-5",
      "genre": "fantasy",
      "tags": "dragon,cute,meadow",
      "created_at": "2025-01-15T10:30:00.000000+00:00"
    }
  ]
}
```

> **Note:** Pages are returned in reverse chronological order (newest first). The `total` field reflects the total number of pages in the master list.

#### Example

```bash
# Get the 20 most recent pages (default)
curl http://localhost:8080/api/pages

# Get the 50 most recent pages
curl "http://localhost:8080/api/pages?n=50"
```

---

### 🔎 Get Page Details

Retrieve the full metadata for a specific page.

**`GET /api/pages/<page_id>`**

#### Path Parameters

| Parameter | Type | Description |
|---|---|---|
| `page_id` | string | The unique page identifier |

#### Response — `200 OK`

```json
{
  "page_id": "a1b2c3d4e5f6...",
  "title": "Friendly Dragon",
  "description": "A cute dragon in a meadow",
  "location": "fantasy-land",
  "age_range": "3-5",
  "genre": "fantasy",
  "tags": ["dragon", "cute", "meadow"],
  "creator": "ArtistBot",
  "created_at": "2025-01-15T10:30:00.000000+00:00",
  "updated_at": "2025-01-15T10:30:00.000000+00:00",
  "thumbnail_path": "/pages/images/thumbnails/a1b2c3d4e5f6....png",
  "fullsize_path": "/pages/images/fullsize/a1b2c3d4e5f6....png"
}
```

#### Error — `404 Not Found`

```json
{
  "error": "Page not found"
}
```

#### Example

```bash
curl http://localhost:8080/api/pages/a1b2c3d4e5f67890abcdef1234567890
```

---

### ✏️ Update Page

Update metadata and/or replace images for an existing page.

**`PUT /api/pages/<page_id>`**

#### Path Parameters

| Parameter | Type | Description |
|---|---|---|
| `page_id` | string | The unique page identifier |

#### Request Body (JSON)

All fields are optional — only provided fields will be updated.

| Field | Type | Description |
|---|---|---|
| `title` | string | Page title |
| `description` | string | Page description |
| `location` | string | Geographic/theme location |
| `age_range` | string | Target age range |
| `genre` | string | Genre/category |
| `tags` | array or string | Tags (array or comma-separated string) |
| `creator` | string | Creator name |
| `thumbnail_base64` | string | New base64-encoded thumbnail image |
| `thumbnail_extension` | string | Thumbnail file extension (default: `".png"`) |
| `fullsize_base64` | string | New base64-encoded full-size image |
| `fullsize_extension` | string | Full-size file extension (default: `".png"`) |

#### Response — `200 OK`

Returns the full updated metadata object (same format as [Get Page Details](#-get-page-details)).

#### Example

```bash
# Update the title and tags
curl -X PUT http://localhost:8080/api/pages/a1b2c3d4e5f67890abcdef1234567890 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Super Friendly Dragon",
    "tags": ["dragon", "cute", "meadow", "updated"]
  }'

# Replace the thumbnail image
curl -X PUT http://localhost:8080/api/pages/a1b2c3d4e5f67890abcdef1234567890 \
  -H "Content-Type: application/json" \
  -d '{
    "thumbnail_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
    "thumbnail_extension": ".webp"
  }'
```

---

### 🖼️ Get Thumbnail Image

Serve the thumbnail image file for a page.

**`GET /api/pages/<page_id>/thumbnail`**

#### Path Parameters

| Parameter | Type | Description |
|---|---|---|
| `page_id` | string | The unique page identifier |

#### Response — `200 OK`

Returns the **binary image file** with the appropriate content type.

#### Error — `404 Not Found`

```json
{
  "error": "Thumbnail not found"
}
```