# publish_social_python

Scripts de línea de comandos para publicar videos (reels) y posts de LinkedIn en YouTube, Instagram y LinkedIn, más un servidor MCP que expone el publicador de videos como herramienta para Claude Desktop / Cowork.

## Scripts

| Script | Qué hace |
|---|---|
| [`publish_social.py`](publish_social.py) | Sube un video a YouTube, Instagram Reels y/o LinkedIn en un solo comando. |
| [`linkedin_post.py`](linkedin_post.py) | Publica un post de texto (opcionalmente con una imagen) en LinkedIn, usando la API moderna de Posts. |
| [`linkedin_auth.py`](linkedin_auth.py) | Flujo OAuth (a correr cada ~60 días) que crea/renueva `linkedin_token.json`, usado por los dos scripts de LinkedIn de arriba. |
| [`publish_social_mcp.py`](publish_social_mcp.py) | Servidor MCP que envuelve `publish_social.py` como una única herramienta `publish_reel`. |

## Instalación

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## Credenciales

Cada plataforma necesita su propio archivo de credenciales en la raíz del proyecto. Ninguno está commiteado — todos figuran en [`.gitignore`](.gitignore) — así que tenés que crearlos vos.

### YouTube

1. En Google Cloud Console, creá un cliente OAuth de tipo "Desktop app" con la YouTube Data API v3 habilitada.
2. Copiá [`youtube_config.example.json`](youtube_config.example.json) a `youtube_config.json` y completá `client_id` / `client_secret`.
3. Generá `youtube-oauth2.yaml` con tu propio helper OAuth para la API de YouTube (`publish_social.py` solo lee este archivo, no hace el flujo de autorización). Debe tener una clave `default` con un JSON (como string) que incluya `client_id`, `access_token`, `refresh_token`, `scope` y `expiration_time_millis`; el access token se renueva automáticamente a partir del refresh token en cada corrida.

### Instagram

1. En Meta for Developers, conseguí un token de acceso de **Página** de larga duración para la Facebook Page vinculada a tu cuenta profesional de Instagram, con los scopes `instagram_basic` e `instagram_content_publish`.
2. Copiá [`instagram_token.example.json`](instagram_token.example.json) a `instagram_token.json` y completá `page_access_token` e `instagram_account_id` (el ID de la cuenta de Instagram Business detrás de esa página).
3. Este token no necesita renovación periódica.

La API de Instagram descarga el video ella misma, así que publicar en Instagram siempre requiere una URL **pública** (`--video-url`), no un archivo local.

### LinkedIn

1. En el LinkedIn Developer Portal, creá una app con el scope `w_member_social` (agregá también `openid` y `profile`) y `http://localhost:8080/callback` como redirect URL autorizada.
2. Copiá [`linkedin_config.example.json`](linkedin_config.example.json) a `linkedin_config.json` y completá `client_id` / `client_secret`.
3. Corré el flujo de autorización:
   ```bash
   venv/bin/python linkedin_auth.py
   ```
   Esto imprime una URL — abrila, iniciá sesión y autorizá la app. El script captura el redirect en `localhost:8080` y escribe `linkedin_token.json`.
4. Los access tokens de LinkedIn para esta app vencen a los ~60 días y LinkedIn no emite refresh token para este tipo de grant, así que volvé a correr el paso 3 cuando `publish_social.py` o `linkedin_post.py` fallen con un error de token vencido/inválido.

## Uso

### Publicar un video (reel)

```bash
venv/bin/python publish_social.py --instagram --linkedin --youtube \
  --file /ruta/al/video.mp4 \
  --video-url "https://tu-url-publica/video.mp4" \
  --title "Mi reel" \
  --description "Descripción" \
  --keywords "tag1,tag2" \
  --privacy-status public \
  --playlist "Mi playlist"
```

- `--youtube` / `--instagram` / `--linkedin`: a qué plataformas publicar (al menos una).
- `--file`: video local, requerido para YouTube y LinkedIn.
- `--video-url`: URL pública del video, requerida para Instagram.
- `--title`, `--description`, `--keywords` (separadas por coma): compartidos entre plataformas.
- `--privacy-status` (`public`/`private`/`unlisted`), `--category-id`, `--playlist`: solo YouTube.

### Publicar un post de texto/imagen en LinkedIn

```bash
venv/bin/python linkedin_post.py --text "Hola LinkedIn" \
  [--image foto.jpg] \
  [--visibility PUBLIC|CONNECTIONS] \
  [--dry-run]
```

- `--text` es el cuerpo del post (requerido). Los caracteres que el markup de LinkedIn reserva (`\ ( ) [ ] { } < > @ * _ ~ |`) se escapan automáticamente, así aparecen tal cual en vez de romper el renderizado del post.
- `--image` adjunta una única imagen local.
- `--dry-run` imprime el payload exacto del request —sin subir la imagen ni publicar nada— para poder revisarlo antes de que el post quede público.

### Servidor MCP

Registrá `publish_social_mcp.py` para que un cliente compatible con MCP (Claude Desktop, Cowork, etc.) pueda invocar `publish_reel` directamente, por ejemplo en `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "publish-social": {
      "command": "/ruta/absoluta/a/publish_social_python/venv/bin/python",
      "args": ["/ruta/absoluta/a/publish_social_python/publish_social_mcp.py"]
    }
  }
}
```

La herramienta toma los mismos parámetros que `publish_social.py` (`title`, `description`, `file`, `video_url`, `instagram`, `linkedin`, `youtube`, `keywords`, `privacy_status`, `playlist`) y devuelve el stdout/stderr y exit code del script que envuelve.

## Tests

```bash
venv/bin/python -m pytest
```

## Notas de seguridad

- Nunca commitees `*_token.json`, `*_config.json` ni `youtube-oauth2.yaml` — tienen credenciales reales y ya están excluidos vía `.gitignore`.
- Todos los requests a las APIs de YouTube, Instagram y LinkedIn van por HTTPS con verificación de certificados TLS habilitada (el comportamiento por defecto de `requests`).
