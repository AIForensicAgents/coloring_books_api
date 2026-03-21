<!-- Open Graph Meta Tags for social sharing -->
<!-- <meta property="og:title" content="Coloring Books API - A RESTful API for Managing Coloring Book Pages" /> -->
<!-- <meta property="og:description" content="A high-performance Flask-based REST API for creating, managing, searching, and serving coloring book pages with image support. Built by AIForensicAgents." /> -->
<!-- <meta property="og:type" content="website" /> -->
<!-- <meta property="og:url" content="https://github.com/AIForensicAgents/coloring_books_api" /> -->
<!-- <meta property="og:image" content="https://raw.githubusercontent.com/AIForensicAgents/coloring_books_api/main/assets/og-banner.png" /> -->
<!-- <meta name="twitter:card" content="summary_large_image" /> -->
<!-- <meta name="twitter:title" content="Coloring Books API" /> -->
<!-- <meta name="twitter:description" content="RESTful API for managing coloring book pages with image storage, search, and metadata management." /> -->

<div align="center">

# 🎨 Coloring Books API

**A RESTful API for creating, managing, searching, and serving coloring book pages**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![API](https://img.shields.io/badge/API-REST-FF6C37?style=for-the-badge&logo=postman&logoColor=white)](/)
[![CORS](https://img.shields.io/badge/CORS-Enabled-blue?style=for-the-badge)](#)
[![Made by](https://img.shields.io/badge/Made%20by-AIForensicAgents-purple?style=for-the-badge)](#)

---

*Store coloring book page metadata, upload thumbnails & full-size images, search by location/age/genre/tags, and manage your entire coloring book library through a clean JSON API.*

[Getting Started](#-getting-started) •
[API Docs](#-api-endpoints) •
[Examples](#-usage-examples) •
[Contributing](#-contributing)

</div>

---

## 📖 Overview

The **Coloring Books API** is a lightweight, file-system-backed REST API built with Flask. It provides a complete CRUD interface for managing coloring book pages — including metadata storage, base64 image upload (thumbnails & full-size), full-text search with filtering, and bulk deletion with password protection.

Pages are stored as individual JSON files in a sharded directory structure for efficient file-system access, while a flat `masterList.txt` file serves as a fast searchable index.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🆕 **Create Pages** | Upload coloring book pages with metadata and base64-encoded images |
| 📄 **Retrieve Pages** | Fetch full metadata for any page by ID |
| 🖼️ **Serve Images** | Serve thumbnail and full-size images directly over HTTP |
| ✏️ **Update Pages** | Modify metadata and replace images for existing pages |
| 🔍 **Advanced Search** | Filter by location, age range, genre, tags, and free-text query |
| 📋 **List Recent Pages** | Retrieve the most recently created pages with pagination |
| 🗑️ **Bulk Delete** | Password-protected batch deletion of pages and all associated assets |
| 🏥 **Health Check** | Built-in health endpoint for monitoring and load balancers |
| 🌐 **CORS Enabled** | Cross-Origin Resource Sharing enabled out of the box |
| 📁 **Sharded Storage** | Efficient file-system storage with 3-level directory sharding |
| 📇 **Master Index** | Flat-file index for fast search without a database |

---

## 🛠️ Tech Stack

- **Runtime:** Python 3.10+
- **Framework:** [Flask](https://flask.palletsprojects.com/)
- **CORS:** [Flask-CORS](https://flask-cors.readthedocs.io/)
- **Storage:** File-system based (JSON metadata + binary images)
- **Index:** Pipe-delimited flat file (`masterList.txt`)
- **Image Format:** Base64 encoded upload, binary file storage

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- `pip` package manager

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
# Using default settings
python app.py

# With custom configuration
PAGES_ROOT=/data/coloring_books FLASK_DEBUG=true python app.py
```

The API will start on `http://0.0.0.0:8080` by default.

### Running with Docker (Optional)

```bash
docker build -t coloring-books-api .
docker run -p 8080:8080 -v /your/data/path:/pages coloring-books-api
```

---

## 🔧 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PAGES_ROOT` | Root directory for all page data, images, and the master index | `/pages` |
| `FLASK_DEBUG` | Enable Flask debug mode (`true` / `false`) | `false` |

### Directory Structure Created

```
$PAGES_ROOT/
├── masterList.txt              # Flat-file search index
├── images/
│   ├── thumbnails/             # Thumbnail images
│   │   └── {page_id}.png
│   └── fullsize/               # Full-size images
│       └── {page_id}.png
├── {char1}/
│   └── {char2}/
│       └── {char3}/
│           └── {page_id}.json  # Page metadata (sharded)
```

---

## 📡 API Endpoints

### Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/pages` | Create a new page |
| `GET` | `/api/pages` | List recent pages |
| `GET` | `/api/pages/<page_id>` | Get page metadata |
| `PUT` | `/api/pages/<page_id>` | Update a page |
| `GET` | `/api/pages/<page_id>/thumbnail` | Get thumbnail image |
| `GET` | `/api/pages/<page_id>/fullsize` | Get full-size image |
| `GET` | `/api/search` | Search pages with filters |
| `POST` | `/api/pages/delete` | Bulk delete pages |

---

### 🏥 Health Check

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

### 🆕 Create Page

Create a new coloring book page with metadata and optional images.

**`POST /api/pages`**

#### Request Body (JSON)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | No | Title of the coloring page |
| `description` | string | No | Description of the page |
| `location` | string | No | Geographic location/theme |
| `age_range` | string | No | Target age range (e.g., `"3-5"`, `"6-12"`) |
| `genre` | string | No | Genre/category (e.g., `"animals"`, `"fantasy"`) |
| `tags` | array or string | No | Tags — array of strings or comma-separated string |
| `creator` | string | No | Creator/artist name |
| `thumbnail_base64` | string | No | Base64-encoded thumbnail image data |
| `thumbnail_extension` | string | No | File extension for thumbnail (default: `".png"`) |
| `fullsize_base64` | string | No | Base64-encoded full-size image data |
| `fullsize_extension` | string | No | File extension for full-size image (default: `".png"`) |

#### Response — `201 Created`

```json
{
  "page_id": "a1b2c3d4e5f6...",
  "metadata": {
    "page_id": "a1b2c3d4e5f6...",
    "title": "Friendly Dragon",
    "description": "A cute dragon in a meadow",
    "location": "fantasy-land",
    "age_range": "3-8",
    "genre": "fantasy",
    "tags": ["dragon", "cute", "meadow"],
    "creator": "ArtistBot",
    "created_at": "2025-01-15T10:30:00.000000+00:00",
    "updated_at": "2025-01-15T10:30:00.000000+00:00",
    "thumbnail_path": "/pages/images/thumbnails/a1b2c3d4e5f6.png",
    "fullsize_path": "/pages/images/fullsize/a1b2c3d4e5f6.png"
  }
}
```

#### Example

```bash
curl -X POST http://localhost:8080/api/pages \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Friendly Dragon",
    "description": "A cute dragon in a meadow",
    "location": "fantasy-land",
    "age_range": "3-8",
    "genre": "fantasy",
    "tags": ["dragon", "cute", "meadow"],
    "creator": "ArtistBot"
  }'
```

#### Example with Image Upload

```bash
# Encode an image to base64 and include it
THUMB_B64=$(base64 -w 0 thumbnail.png)
FULL_B64=$(base64 -w 0 fullsize.png)

curl -X POST http://localhost:8080/api/pages \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Ocean Scene\",
    \"genre\": \"nature\",
    \"tags\": [\"ocean\", \"fish\"],
    \"thumbnail_base64\": \"${THUMB_B64}\",
    \"thumbnail_extension\": \".png\",
    \"fullsize_base64\": \"${FULL_B64}\",
    \"fullsize_extension\": \".png\"
  }"
```

---

### 📄 Get Page

Retrieve complete metadata for a specific page.

**`GET /api/pages/<page_id>`**

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page_id` | string | The unique page identifier |

#### Response — `200 OK`

```json
{
  "page_id": "a1b2c3d4e5f6...",
  "title": "Friendly Dragon",
  "description": "A cute dragon in a meadow",
  "location": "fantasy-land",
  "age_range": "3-8",
  "genre": "fantasy",
  "tags": ["dragon", "cute", "meadow"],
  "creator": "ArtistBot",
  "created_at": "2025-01-15T10:30:00.000000+00:00",
  "updated_at": "2025-01-15T10:30:00.000000+00:00",
  "thumbnail_path": "/pages/images/thumbnails/a1b2c3d4e5f6.png",
  "fullsize_path": "/pages/images/fullsize/a1b2c3d4e5f6.png"
}
```

#### Error Response — `404 Not Found`

```json
{
  "error": "Page not found"
}
```

#### Example

```bash
curl http://localhost:8080/api/pages/a1b2c3d4e5f6789012345678abcdef01
```

---

### 🖼️ Get Thumbnail Image

Serve the thumbnail image file for a specific page.

**`GET /api/pages/<page_id>/thumbnail`**

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page_id` | string | The unique page identifier |

#### Response — `200 OK`

Returns the binary image file with appropriate content type. The API will automatically detect the file extension if the stored path is unavailable, checking for `.png`, `.jpg`, `.jpeg`, `.webp`, and `.gif`.

#### Error Response — `404 Not Found`

```json
{
  "error": "Thumbnail not found"
}
```

#### Example

```bash
# Download thumbnail to file
curl -o thumbnail.png http://localhost:8080/api/pages/a1b2c3d4e5f6789012345678abcdef01/thumbnail

# Use in an HTML img tag
# <img src="http://localhost:8080/api/pages/{page_id}/thumbnail" alt="Coloring page thumbnail" />
```

---

### 🖼️ Get Full-Size Image

Serve the full-size image file for a specific page.

**`GET /api/pages/<page_id>/fullsize`**

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page_id` | string | The unique page identifier |

#### Response — `200 OK`

Returns the binary image file with appropriate content type. Falls back to scanning common extensions (`.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`) if the stored path is missing.

#### Error Response — `404 Not Found`

```json
{
  "error": "Full-size image not found"
}
```

#### Example

```bash
# Download full-size image
curl -o fullsize.png http://localhost:8080/api/pages/a1b2c3d4e5f6789012345678abcdef01/fullsize

# Open directly in browser
# http://localhost:8080/api/pages/{page_id}/fullsize
```

---

### ✏️ Update Page

Update metadata and/or replace images for an existing page.

**`PUT /api/pages/<page_id>`**

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page_id` | string | The unique page identifier |

#### Request Body (JSON)

All fields are optional. Only provided fields will be updated.

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Updated title |
| `description` | string | Updated description |
| `location` | string | Updated location |
| `age_range` | string | Updated age range |
| `genre` | string | Updated genre |
| `tags` | array or string | Updated tags |
| `creator` | string | Updated creator name |
| `thumbnail_base64` | string | New base64-encoded thumbnail (replaces existing) |
| `thumbnail_extension` | string | File extension for new thumbnail |
| `fullsize_base64` | string | New base64-encoded full-size image (replaces existing) |
| `fullsize_extension` | string | File extension for new full-size image |

#### Response — `200 OK`

Returns the full updated metadata object.

```json
{
  "page