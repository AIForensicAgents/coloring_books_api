curl -X POST https://your-app.fly.dev/api/v1/pages \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Enchanted Forest",
    "description": "A magical woodland scene with fairies and mushrooms.",
    "location": "fantasy",
    "age_range": "6-12",
    "genre": "fantasy",
    "tags": ["forest", "fairies", "nature", "magical"],
    "creator": "ArtistJane"
  }'