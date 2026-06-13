# Jellyrecordarr

- radarr api for compatibility with tools like seer
- sonarr api & series support is planned
- automatically schedule tv recordings in jellyfin
- prevent concurrent scheduled recordings

## Example docker-compose.yml
``` yaml
services:
  jellyrecordarr:
    build: .
    restart: unless-stopped
    volumes:
      - data:/data
    environment:
      - JELLYFIN_HOST="http://your-host:8096"
      - JELLYFIN_API_KEY="your-api-key"
      - TMDB_API_KEY="your-api-key"
      - TMDB_LANGUAGE=de
      - TMDB_COUNTRY=de
    healthcheck:
      test: wget --no-verbose --tries=1 --spider http://localhost:5000/api/v3/system/status || exit 1
      start_period: 20s
      timeout: 3s
      interval: 15s
      retries: 3

  seerr:
    image: ghcr.io/seerr-team/seerr:latest
    environment:
      - LOG_LEVEL=info
      - TZ=Europe/Berlin
      - PORT=5055
    ports:
      - 5055:5055
    volumes:
      - seerr_config:/app/config
    healthcheck:
      test: wget --no-verbose --tries=1 --spider http://localhost:5055/api/v1/settings/public || exit 1
      start_period: 20s
      timeout: 3s
      interval: 15s
      retries: 3
    restart: unless-stopped
    depends_on:
      - jellyrecordarr
volumes:
  data:
  seer_config:

```