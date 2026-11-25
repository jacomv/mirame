# Cambios

Todos los cambios relevantes de Mírame. El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa [versionado semántico](https://semver.org/lang/es/) (ver [CONTRIBUTING.md](CONTRIBUTING.md#versiones)).

## [Sin publicar]

### Agregado

- **Estructura del sermón** con IA (opcional): pestaña «Sermón» en el reporte con las partes y sus transiciones, si la estructura es clara, si se anunciaron los puntos y si la introducción va acorde con el argumento, el argumento y el clímax, la conexión con el evangelio, las aplicaciones y los pasajes citados. Cada cosa con su minuto, y un clic lleva el video ahí. Comando `mirame estructura`, botón «Analizar estructura» en la Biblioteca y casilla en «Nuevo análisis». Guarda `estructura.json` y `estructura.md`.
- «Anunció sus puntos» muestra cada anuncio con su minuto y sus palabras, y distingue los puntos del sermón de una lista dentro de un punto, que ya no cuenta como anunciar los puntos.
- **Clave de OpenAI** como alternativa o complemento a la de Groq: transcribe con `whisper-1` y analiza el texto con los modelos de OpenAI.
- **Qué API usar** (Ajustes, campo `api` de la configuración o `MIRAME_API`): «Solo OpenAI» o «Solo Groq» hacen la transcripción y el análisis con esa API aunque haya otras claves. Sin elegir, sigue lo automático: Groq transcribe y OpenAI analiza. Ajustes muestra quién hace cada paso.
- Documentación: costos de ejemplo de un sermón con OpenAI y con Groq (`docs/costos-openai.md`, `docs/costos-groq.md`).

### Cambiado

- Lecturas y oración: instrucciones más estrictas sobre qué es una oración, y un aviso en el reporte si más del 15 % del sermón quedó excluido por estar marcado como oración.

### Arreglado

- La transcripción detecta cuando Whisper se queda repitiendo una frase o unas palabras sobre silencio o música, vuelve a pedir solo esa parte en pedazos más cortos y descarta las frases inventadas.
- Con Groq, las consultas al modelo de lenguaje piden una respuesta más larga (hasta 16 000 tokens). Antes Groq la cortaba en unos 3000, razonamiento incluido, y la estructura del sermón fallaba con un error 400 (`json_validate_failed`).

## [0.5.1] — 2026-11-24

### Arreglado

- **Windows:** el instalador fallaba en PowerShell 7 (el de la Microsoft Store) con «No se pudo ejecutar el programa powershell.exe… UseShellExecute», y en equipos con la política de ejecución restringida. El comando pasa a ser `irm …/instalar.ps1 | iex`, y uv se descarga directamente sin su instalador ni otro PowerShell.

## [0.5.0] — 2026-11-24

Instalar Mírame pasa de cinco pasos técnicos a un comando. El método de medición no cambia (sigue en el 3): los análisis anteriores no necesitan recalcularse.

### Agregado

- **Guía de instalación paso a paso** ([docs/instalar.md](docs/instalar.md)) para quien nunca ha usado una terminal: cómo abrirla, qué se ve mientras se instala, cómo usar y actualizar la app, y qué hacer si algo falla.
- **Instalación con un solo comando** en macOS, Linux y Windows (`instalar.sh`, `instalar.ps1`). Instala uv y Python si faltan, Mírame y el navegador de las capturas, crea el acceso directo y abre la app. Volver a ejecutarlo actualiza. No pide permisos de administrador ni necesita git.
- **ffmpeg y Deno incluidos** como dependencias (`imageio-ffmpeg`, `yt-dlp[default,deno]`): ya no hay que instalar Homebrew, ffmpeg ni Deno. Si la computadora tiene su propio ffmpeg, se usa ese.
- `mirame acceso`: acceso directo en el escritorio (en Linux, en el menú de aplicaciones).
- Abrir Mírame cuando ya está abierta lleva a la app existente en vez de arrancar otra.

### Cambiado

- El instalador explica cada paso y, si falla, dice qué hacer.
- `mirame instalar-capturas` descarga solo el navegador sin interfaz (unos 200 MB en vez de casi 600 MB).

### Arreglado

- Los videos grabados en vertical con el celular (con rotación en los metadatos) leían el tamaño al revés.
- Sin Deno, YouTube podía negar la descarga de algunos videos.

### Documentación

- README: cómo actualizar, comprobar la versión, recalcular análisis anteriores e instalar una versión concreta.

## [0.4.0] — 2026-11-20

### Agregado

- **Elegir el tramo antes de procesar.** Al pegar el enlace aparece el video con su título y duración. Puedes analizar todo el video o solo un tramo: con una barra de dos manijas, escribiendo los tiempos o con «Marcar aquí» mientras lo reproduces. Así se dejan fuera la alabanza, los anuncios y la oración final.
- **Tiempo estimado y advertencias antes de empezar:** cuánto tardará en esta computadora (según los análisis anteriores), y avisos si el video es largo y no se recortó, si el tramo es muy corto o si va a tardar mucho.
- **Avance por etapas:** porcentaje general, tiempo transcurrido, cuánto falta y en qué etapa va (descarga, recorte, medición, transcripción, lecturas). El recorte y la subida de videos propios también muestran su avance.
- **Margen de error** del porcentaje mirando a la congregación (bootstrap por bloques de 30 s, 95 %) y **sensibilidad** al umbral de la cabeza (±3°), en el reporte y en `resumen.json`.
- **Transcripción con otros proveedores:** además de Groq, cualquier servicio de Whisper compatible con OpenAI (por ejemplo `whisper-1` de OpenAI). Ajustes separa los dos pasos (transcripción y análisis) y muestra si está todo listo.
- **Aviso de las claves** en la app y en el reporte: Mírame funciona sin ellas, y con una clave de Whisper el resultado es más fino.
- Integración continua en GitHub Actions (estilo, pruebas y paquete en Linux y macOS), plantillas de issues y pull requests, política de seguridad y código de conducta.

### Cambiado

- **Método 3 de clasificación** (los análisis anteriores se actualizan con `mirame recalcular`):
  - la postura habitual se calcula con los fotogramas de ojos claramente arriba, no con todo el sermón;
  - los ojos bajados deben sostenerse medio segundo (los parpadeos ya no cuentan) y no cuentan con la cabeza levantada;
  - cerca del umbral de la cabeza (±5°) deciden los ojos.

  En muestras revisadas a ojo, los aciertos en los casos difíciles pasaron de 19 a 32 de 49, y de 27 a 31 de 33 en una muestra de control. Las cifras de los sermones cambian entre −6 y +2 puntos; los vistazos bajan a menos de la mitad. Detalle en [docs/como-funciona.md](docs/como-funciona.md#7-validación-con-muestras).

### Arreglado

- `mirame recalcular` conservaba la calibración por tramo (`--calibrar`) solo en la primera corrida.

## [0.3.0] — 2026-11-20

### Agregado

- **App local** en el navegador (`mirame`): nuevo análisis desde un enlace de YouTube o un video de la computadora, biblioteca de análisis (abrir, separar lecturas, borrar) y ajustes para las claves de IA, con avance en vivo y cancelación.
- **Lectura bíblica y oración** con IA (opcional): transcripción con Whisper en Groq y marcas con cualquier modelo compatible con OpenAI. La lectura bíblica se separa de la lectura de notas y la oración se excluye del cálculo.
- **Miradas a la congregación:** duración media, mediana y la más larga.
- Comandos `lista`, `borrar`, `lecturas` e `instalar-capturas`. Las capturas pasan a ser una instalación opcional (`mirame[capturas]`).
- Pruebas automáticas, licencia MIT y documentación del método.

### Cambiado

- Reporte rediseñado: cabe en una pantalla sin scroll, con el video como protagonista.
- Los datos pasan a `~/Mirame` (configurable con `MIRAME_DATOS`), fuera del código.

## [0.2.0]

### Agregado

- Detecta la lectura con los ojos (blendshapes de MediaPipe), no solo con la inclinación de la cabeza.

## [0.1.0]

- Primera versión: análisis por línea de comandos, reporte HTML y capturas.

[Sin publicar]: https://github.com/jacomv/mirame/compare/v0.5.1...HEAD
[0.5.1]: https://github.com/jacomv/mirame/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/jacomv/mirame/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/jacomv/mirame/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/jacomv/mirame/releases/tag/v0.3.0
