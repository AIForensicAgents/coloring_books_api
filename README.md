<!--
  Open Graph Meta Tags for Social Preview
  GitHub parses these for link previews
-->
<!-- og:title = Coloring Books API -->
<!-- og:description = A delightful API for creating, managing, and serving AI-generated coloring book pages. Search by age, genre, location & tags. -->
<!-- og:image = https://drive.google.com/uc?export=view&id=1KCIYgWRp52SI3e5qplooTvixXQHyMjw3 -->
<!-- og:url = https://github.com/AIForensicAgents/coloring_books_api -->
<!-- og:type = website -->

<div align="center">

# 🎨 Coloring Books API

**A delightful API for creating, managing, and serving AI-generated coloring book pages**

*Search by age, genre, location & tags* ✨

[![API Status](https://img.shields.io/badge/API-Live-brightgreen?style=for-the-badge)](https://coloring-books-api.fly.dev/health)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)
[![Built with Love](https://img.shields.io/badge/Built%20with-💜-ff69b4?style=for-the-badge)](https://github.com/AIForensicAgents)

<img src="https://drive.google.com/uc?export=view&id=1KCIYgWRp52SI3e5qplooTvixXQHyMjw3" alt="Coloring Books API Banner" width="600"/>

*Built with 💜 by Papersaurus 🦕*

</div>

---

## ✨ Features

- 🖼️ **Create** coloring book pages with base64 thumbnail + fullsize images
- 🔍 **Search & Filter** by tags, location, genre, age range, and free text
- 📄 **Full CRUD** — create, read, update, and delete pages
- 🎯 **Serve** rendered coloring pages directly
- 🏷️ **Rich Metadata** — title, description, creator, tags, genre, age range, location
- 🔐 **Password-protected** bulk delete operations
- ⚡ **Fast** — deployed on Fly.io for low-latency responses worldwide

---

## 🚀 Quick Start

### Health Check

```bash
curl https://coloring-books-api.fly.dev/health
```

### Create a Page

```bash
curl -X POST https://coloring-books-api.fly.dev/api/pages \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Dinosaur Adventure",
    "description": "Fun dinosaurs at the beach",
    "tags": ["dinosaur", "beach", "summer"],
    "age_range": "4-7",
    "genre": "adventure",
    "location": "Beach",
    "creator": "artist@example.com"
  }'
```

### Search Pages

```bash
curl "https://coloring-books-api.fly.dev/api/search?genre=animals&tags=cat,dog&limit=10"
```

### List Recent Pages

```bash
curl "https://coloring-books-api.fly.dev/api/pages?n=20"
```

---

## 📚 API Reference

### Base URL

```
https://coloring-books-api.fly.dev
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check — returns API status and timestamp |
| `POST` | `/api/pages` | Create a new coloring book page |
| `GET` | `/api/pages` | List most recent pages (query: `?n=10`) |
| `GET` | `/api/pages/:id` | Get page metadata by ID |
| `GET` | `/api/pages/:id/thumbnail` | Get thumbnail image binary |
| `GET` | `/api/pages/:id/fullsize` | Get fullsize image binary |
| `PUT` | `/api/pages/:id` | Update page metadata and/or images |
| `POST` | `/api/pages/delete` | Delete pages (requires password) |
| `GET` | `/api/search` | Search and filter pages |
| `GET` | `/pages/:id` | Serve the rendered coloring page |

---

### 🔍 Search Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `location` | string | Filter by location |
| `age` | string | Filter by age range |
| `genre` | string | Filter by genre |
| `tags` | string | Comma-separated tag list |
| `q` | string | Free text search query |
| `limit` | number | Max results to return |
| `offset` | number | Pagination offset |

---

### 📝 Create/Update Page Body

```json
{
  "title": "Page Title",
  "description": "A description of the page",
  "location": "City or region",
  "age_range": "4-7",
  "genre": "animals",
  "tags": ["cat", "dog", "pets"],
  "creator": "creator@example.com",
  "thumbnail_base64": "iVBORw0KGgo...",
  "fullsize_base64": "iVBORw0KGgo...",
  "thumbnail_extension": ".png",
  "fullsize_extension": ".png"
}
```

---

### 🗑️ Delete Pages

Single delete:
```bash
curl -X POST https://coloring-books-api.fly.dev/api/pages/delete \
  -H "Content-Type: application/json" \
  -d '{"password": "noodle", "id": "page_id_here"}'
```

Bulk delete:
```bash
curl -X POST https://coloring-books-api.fly.dev/api/pages/delete \
  -H "Content-Type: application/json" \
  -d '{"password": "noodle", "ids": ["id1", "id2", "id3"]}'
```

---

## 🛠️ Tech Stack

- **Runtime:** Node.js
- **Hosting:** [Fly.io](https://fly.io)
- **Images:** Base64 encoded PNG/JPEG
- **AI Generation:** Powered by Gemini image generation
- **Search:** Full-text + metadata filtering

---

## 🤝 Contributing

Contributions are welcome! Feel free to:

1. Fork the repo
2. Create a feature branch
3. Submit a PR

---

## 📄 License

MIT License — use it, remix it, share the joy! 🎉

---

<div align="center">

**Built with 💜 by Papersaurus 🦕**

*Making the world more colorful, one page at a time* 🌈

</div>
