# Mírame

**¿Hacia dónde mira el predicador, y hacia dónde apunta su sermón?** Mírame toma el video de un sermón y responde las dos preguntas:

- **Hacia dónde mira el predicador.** Segundo a segundo, cuánto tiempo mira a la congregación y cuánto baja la vista a sus notas. Corre en tu computadora, sin cuentas ni suscripciones.
- **Hacia dónde apunta el sermón** (opcional, con una clave de IA). La estructura y sus transiciones, el argumento y el clímax, cómo se conectó el pasaje con el evangelio de Cristo, las aplicaciones a la congregación y los pasajes bíblicos citados. Cada cosa con su minuto y segundo, para ir a ese momento del video con un clic.

<p>
  <img src="docs/img/mirando-notas.jpg" width="49%" alt="Reporte de Mírame: el predicador mira sus notas, con la cabeza inclinada">
  <img src="docs/img/mirando-congregacion.jpg" width="49%" alt="Reporte de Mírame: el predicador mira a la congregación">
</p>

*A la izquierda, el predicador baja la vista a sus notas (recuadro naranja). A la derecha, mira a la congregación (recuadro verde).*

<p>
  <img src="docs/img/sermon-estructura.jpg" width="100%" alt="Pestaña «Sermón» del reporte de Mírame: al lado del video, las partes del sermón con el minuto y las palabras de cada transición; sobre la línea de tiempo, una franja con los puntos del sermón">
</p>

*La pestaña «Sermón»: las partes del sermón con el minuto y las palabras de cada transición, y cuánto miró el predicador a la congregación en cada una. Sobre la línea de tiempo, la franja de los puntos y una estrella en el clímax.*

Lo hice porque quería mejorar como predicador y me di cuenta de que, si no medía, solo iba a seguir suponiendo. No encontré una herramienta que contara cuántas veces uno baja la mirada al predicar, así que la construí con ayuda de un modelo de IA. Es de código abierto: úsala, compártela y mejórala.

— Jacobis Aldana

**Sobre el análisis del sermón.** Es un añadido de Arturo Ferreiro al proyecto de Jacobis Aldana.

Al predicar no solo importa el contacto visual con la congregación. Importa también el contenido del mensaje: si tiene una buena estructura, si apunta a conocer y entender más al Señor Jesucristo y si lleva a una buena aplicación para la iglesia. Por eso me pareció bueno reunir los dos análisis en una sola herramienta. El nombre sigue diciendo lo que hace, ahora en dos sentidos: hacia dónde mira el predicador y hacia dónde apunta su sermón.

Este añadido nace de un grupo de predicación expositiva en la Iglesia Evangélica Cuajimalpa, donde los varones de la iglesia nos preparamos para predicar la Palabra con fidelidad y expositivamente. La idea es ir afinando el análisis, quizá con un método claro como el de Simeon Trust.

— Arturo Ferreiro

---

## Qué te dice

### Sobre la mirada

- **Qué porcentaje del sermón** miraste a la congregación, cuánto a tus notas y cuánto a la Biblia.
- **Cuánto dura cada mirada** a la gente en promedio, y cuál fue la más larga.
- **Cuántas veces bajaste a las notas** y cuál fue la lectura más larga.
- **Cuánto puede variar el resultado:** el margen de error del porcentaje, para saber si la diferencia entre dos sermones es real.
- **Un reporte** con el video del sermón y, al lado, una línea de tiempo que se pinta de verde (congregación), naranja (notas) o azul (Biblia). Un clic en cualquier punto lleva el video a ese momento.
- **Capturas PNG** de 1920×1080 listas para un artículo o una presentación.

### Sobre el sermón (opcional, con IA)

- **La estructura:** las partes del sermón, el minuto y las palabras de cada transición, si la estructura es clara y si el predicador anunció sus puntos, con el minuto de cada anuncio.
- **La introducción:** si prepara el argumento principal o habla de otra cosa.
- **El argumento y el clímax:** la tesis, los pasos con que se desarrolla y dónde está el clímax.
- **El evangelio:** cómo se conectó el pasaje con el evangelio de Cristo y qué aspecto se mencionó (su vida, su muerte, su resurrección, su obra, su segunda venida, su reinado).
- **Las aplicaciones** a la congregación: a quién van dirigidas y en qué se apoyan.
- **Los pasajes bíblicos** leídos, citados o aludidos.
- **Las dos cosas juntas:** cuánto miró a la congregación en cada parte del sermón.

Todo va con su minuto y segundo en la pestaña «Sermón» del reporte: un clic lleva el video a ese momento, y el análisis completo se copia como texto.

## Cómo lo mide

1. Revisa el video **cuatro veces por segundo**. En cada cuadro ubica el rostro del predicador con [MediaPipe](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker) y mide dos cosas: cuánto inclina la cabeza y hacia dónde apuntan los ojos. Se puede leer con la cabeza recta, moviendo solo la mirada, y eso también cuenta.
2. Aprende la **postura habitual** del predicador cuando mira a la gente, a partir de los momentos en que tiene los ojos arriba. Marca como «abajo» lo que pasa de unos 15° por debajo de esa postura, o cuando los ojos se bajan al menos medio segundo aunque la cabeza no se mueva. Cerca del límite deciden los ojos, y los parpadeos no cuentan.
3. Agrupa por segundo y calcula los porcentajes, las miradas, los episodios de lectura y el margen de error.
4. **Opcional, con IA:** transcribe el audio y un modelo de lenguaje marca dónde se lee la Biblia y dónde se ora. Así, leer el texto bíblico no cuenta igual que leer el manuscrito, y cerrar los ojos al orar no se confunde con mirar abajo.
5. **Opcional, con IA:** sobre esa misma transcripción, un modelo de lenguaje analiza la estructura y el contenido del sermón (ver abajo).

## Cómo analiza el sermón

Es opcional y necesita una clave de IA. Trabaja sobre la transcripción, no sobre el video:

1. **Transcribe el audio** con Whisper. Cada frase queda numerada, con su segundo de inicio y de fin.
2. **Hace tres consultas a un modelo de lenguaje**, con las frases numeradas:
   - *Estructura, argumento y clímax*, con el sermón completo.
   - *Evangelio y aplicaciones*, con el sermón completo.
   - *Pasajes citados*, en ventanas de 8 minutos para no dejar ninguno. La misma referencia repetida en menos de 45 segundos cuenta una vez.
3. **El modelo no da minutos.** Señala el número de la frase, y el tiempo sale de la transcripción. Así cada minuto del reporte corresponde a algo que se dijo. Lo que apunta a una frase que no existe se descarta.
4. **Describe, no completa.** Se le pide registrar solo lo que el predicador dijo, con citas literales, y no lo que un buen sermón debería tener. Un punto figura como «anunciado» solo si se dijo en voz alta, y las menciones de paso a Cristo («en el nombre de Jesús» al orar) no cuentan como evangelio.
5. **Cruza el resultado con la mirada.** En cada parte del sermón dice qué porcentaje del tiempo el predicador miró a la congregación. Las cifras de la mirada no cambian.

El resultado queda en `estructura.json` (lo que muestra la pestaña «Sermón»; se puede corregir a mano) y en `estructura.md` (lo mismo, como texto). Los modelos que se usan están en [Claves de IA](#claves-de-ia-opcional).

Conviene leerlo como la opinión de un oyente atento, no como un veredicto. Es el juicio de un modelo de lenguaje sobre una transcripción automática: no oye el tono ni las pausas, puede dividir el sermón distinto a como lo pensó el predicador, y dos corridas pueden mover una transición una o dos frases.

El detalle del método, sus límites y cómo validarlo están en [docs/como-funciona.md](docs/como-funciona.md). Un ejemplo de lo que cuesta la IA con OpenAI está en [docs/costos-openai.md](docs/costos-openai.md).

**Tu video no sale de tu computadora.** Todo el análisis de imagen es local. Si activas la IA, lo único que se envía es el audio (al servicio de transcripción) y el texto transcrito (al modelo que marca las lecturas y analiza la estructura).

---

## Instalación

Un solo comando. Copia el de tu sistema, pégalo y pulsa Enter. No pide contraseña de administrador.

> **¿Nunca has usado una terminal?** La [guía de instalación paso a paso](docs/instalar.md) explica cómo abrirla, qué verás mientras se instala y qué hacer si algo falla.

### macOS y Linux

Abre la app **Terminal** y pega:

```bash
curl -LsSf https://raw.githubusercontent.com/jacomv/mirame/main/instalar.sh | sh
```

### Windows

Abre **PowerShell** (búscalo en el menú Inicio; sirve la versión 5 o la 7) y pega:

```powershell
irm https://raw.githubusercontent.com/jacomv/mirame/main/instalar.ps1 | iex
```

La primera vez tarda unos minutos y ocupa cerca de 1 GB. Al terminar abre la app y deja en el escritorio un acceso directo **Mírame** para abrirla con doble clic. Mientras la usas queda abierta una ventana de terminal con la app funcionando; para cerrar Mírame, cierra esa ventana.

El instalador ([instalar.sh](instalar.sh), [instalar.ps1](instalar.ps1)) se puede leer antes de ejecutarlo. Instala [uv](https://docs.astral.sh/uv/), que trae su propio Python, y con él Mírame. ffmpeg (para leer el video) y Deno (que necesita YouTube) vienen incluidos: no hay que instalar nada más.

<details>
<summary>Instalación manual (si ya usas uv)</summary>

```bash
uv tool install "mirame[capturas] @ https://github.com/jacomv/mirame/archive/refs/heads/main.zip"
mirame instalar-capturas     # navegador para el botón Capturar (unos 200 MB); opcional
mirame acceso                # acceso directo en el escritorio; opcional
```

Sin `[capturas]` y sin `mirame instalar-capturas` todo funciona igual, salvo el botón **Capturar**. La primera vez que analices un sermón, Mírame descarga el modelo de MediaPipe (3,6 MB).

</details>

### Actualizar

Cierra Mírame y vuelve a ejecutar **el mismo comando de instalación**. Instala la última versión encima de la anterior.

Comprueba la versión instalada con `mirame --version`; también aparece en el pie de la app. Las versiones publicadas y sus cambios están en [Releases](https://github.com/jacomv/mirame/releases) y en el [CHANGELOG](CHANGELOG.md).

Tus análisis, videos y claves viven en `~/Mirame` y no se tocan al actualizar. Si una versión cambia el **método de medición** (el CHANGELOG lo indica), los análisis anteriores conservan sus cifras viejas hasta que los recalcules. Recalcular no vuelve a procesar el video y tarda unos segundos:

```bash
mirame lista                       # ver los análisis guardados y su id
mirame recalcular <análisis>       # aplicar el método nuevo a uno
```

Para instalar una versión concreta, por ejemplo para repetir un análisis con el método de entonces:

```bash
uv tool install --force "mirame[capturas] @ https://github.com/jacomv/mirame/archive/refs/tags/v0.4.0.zip"
```

Si trabajas desde el código fuente:

```bash
git pull
uv sync --extra capturas --group dev
```

### Desinstalar

```bash
uv tool uninstall mirame      # tus análisis quedan en ~/Mirame; bórrala a mano si ya no la quieres
```

Borra también el acceso directo **Mírame** del escritorio.

---

## Uso

### La app

```bash
mirame
```

Se abre en tu navegador, en `http://127.0.0.1:8710`. Solo tu computadora puede verla. Para cerrarla, vuelve a la terminal y presiona `Ctrl+C`.

![Pantalla de inicio de Mírame](docs/img/app.jpg)

**Nuevo análisis.** Pega el enlace de YouTube o elige un video de tu computadora. Aparece el video con su título y duración, y eliges qué analizar:

- **Todo el video**, si es solo la predicación.
- **Solo un tramo**, si incluye alabanza, anuncios u oración final. Reproduce el video, páusalo donde empieza la predicación y pulsa **Marcar aquí**; haz lo mismo con el final. También puedes mover las manijas de la barra o escribir los tiempos (`mm:ss` o `h:mm:ss`).

Antes de empezar, Mírame te dice cuánto tardará en tu computadora y te avisa si conviene recortar o si el tramo es demasiado corto. Mientras procesa, en **Biblioteca** ves el avance por etapas y cuánto falta. Como referencia, en un Mac mini con chip de Apple un sermón de una hora tarda unos 3 minutos.

Con una clave de IA puedes marcar además «Separar la lectura bíblica y la oración» y «Analizar la estructura del sermón».

**Biblioteca.** Los análisis guardados, con sus cifras principales. Desde aquí abres el reporte, separas la lectura bíblica o analizas la estructura de un análisis que ya tienes, o lo borras. Abajo puedes vaciar la caché de videos descargados para liberar espacio; tus análisis no se tocan.

**Ajustes.** Las claves de IA. Son opcionales (ver abajo).

**En el reporte:** espacio reproduce y pausa, ← y → saltan 5 segundos, `R` cambia a la vista de resumen sin video. **Capturar** guarda un PNG del momento actual en la carpeta `capturas/` del análisis.

**La pestaña «Sermón»** aparece junto a «Mirada» cuando el sermón tiene su estructura analizada (tecla `S`). Muestra, al lado del video:

- **Estructura:** el tema, si la estructura es clara, si anunció sus puntos, si la introducción va acorde con el argumento principal, y cada parte con el minuto de su transición, las palabras con que la hizo y cuánto miró a la congregación en esa parte.
- **Argumento y clímax:** la tesis, los pasos del argumento en orden y el momento más alto del sermón.
- **Evangelio:** cómo se conectó el pasaje con Cristo y qué aspectos se mencionaron (su vida, su muerte, su resurrección, su reinado, su segunda venida…).
- **Aplicaciones:** cada llamado a los oyentes, a quién va dirigido y en qué parte del pasaje se apoya.
- **Pasajes citados:** cada referencia bíblica, leída, citada de memoria, mencionada o aludida.

Un clic en cualquier minuto lleva el video a ese momento y lo reproduce. Sobre la línea de tiempo aparece una franja con las partes del sermón y una estrella en el clímax. **Copiar** deja el análisis completo en el portapapeles como texto.

<p>
  <img src="docs/img/sermon-resumen.jpg" width="49%" alt="Pestaña «Sermón», sección Estructura: el tema, el pasaje, el resumen y si la estructura es clara, si anunció sus puntos y si tiene introducción">
  <img src="docs/img/sermon-argumento.jpg" width="49%" alt="Pestaña «Sermón», sección Argumento y clímax: la tesis y los pasos del argumento, cada uno con su minuto">
</p>
<p>
  <img src="docs/img/sermon-evangelio.jpg" width="49%" alt="Pestaña «Sermón», sección Evangelio: cómo se conectó el pasaje con Cristo y cada mención con su minuto y su cita">
  <img src="docs/img/sermon-aplicaciones.jpg" width="49%" alt="Pestaña «Sermón», sección Aplicaciones: cada llamado a los oyentes, a quién va dirigido y en qué se apoya">
</p>
<p>
  <img src="docs/img/sermon-pasajes.jpg" width="49%" alt="Pestaña «Sermón», sección Pasajes citados: cada referencia bíblica con su minuto y si fue leída, citada, mencionada o aludida">
</p>

*De izquierda a derecha y de arriba abajo: el resumen de la estructura, el argumento, el evangelio, las aplicaciones y los pasajes citados.*

### Claves de IA (opcional)

> **Mírame funciona sin claves de IA.** Si agregas una clave de transcripción (Whisper), el resultado es más fino.

Con una clave, Mírame transcribe el sermón y, sobre la transcripción, hace dos cosas:

- **Separa la lectura bíblica y la oración.** El resultado es más preciso porque leer la Biblia en voz alta deja de contar como leer notas, y orar con los ojos cerrados deja de contar como mirar abajo.
- **Analiza la estructura del sermón** (la pestaña «Sermón» del reporte). No cambia las cifras de la mirada.

Son dos pasos, y cada uno puede usar un proveedor distinto:

| Paso | Recomendado | Alternativas |
|---|---|---|
| **1. Transcripción** (Whisper: audio a texto con tiempos) | [Groq](https://console.groq.com/keys), gratis: `whisper-large-v3-turbo` | OpenAI (`whisper-1`) o cualquier servicio de Whisper compatible con OpenAI |
| **2. Análisis de la transcripción** (marcar lecturas y oraciones, y analizar la estructura) | Groq con la misma clave: `openai/gpt-oss-120b` | OpenAI (`gpt-5.4` para las lecturas y `gpt-5.5` para la estructura), OpenRouter, Azure, DeepSeek, un LiteLLM propio u Ollama en tu máquina |

La forma más simple es una sola clave de **Groq**: créala en [console.groq.com/keys](https://console.groq.com/keys) y pégala en **Ajustes**, y cubre los dos pasos. Para marcar las lecturas conviene un modelo rápido y sin razonamiento; para la estructura, uno capaz, que lea el sermón completo de una vez. La capa gratuita tiene un límite de 8000 tokens por minuto: en un sermón de 35 minutos alcanzó para transcribir y marcar las lecturas, pero no para analizar la estructura. Con el plan de pago de Groq, el análisis completo de ese sermón costó unos 4,5 centavos de dólar (ver [docs/costos-groq.md](docs/costos-groq.md)).

Con una clave de **OpenAI**, que es de pago ([platform.openai.com/api-keys](https://platform.openai.com/api-keys)), Mírame marca las lecturas con `gpt-5.4` y analiza la estructura con `gpt-5.5`; si no hay otra forma de transcribir, también transcribe con `whisper-1`. Si pones las dos claves, Groq transcribe y OpenAI analiza el texto. La pestaña «Sermón» sale mejor con los modelos de OpenAI: al comparar el mismo sermón, el modelo de Groq lo dividió en menos partes y no registró aplicaciones (ver [docs/costos-groq.md](docs/costos-groq.md)). Para que una sola haga todo, elige **Solo OpenAI** o **Solo Groq** en Ajustes, en «Qué API usar». Es el campo `api` de `configuracion.json`: `"openai"`, `"groq"` o vacío para lo automático.

**Cuánto cuesta con OpenAI.** Como ejemplo, un sermón de 35 minutos con todo activado costó 0,98 USD en noviembre de 2026: 0,21 la transcripción, 0,04 marcar las lecturas y la oración, y 0,73 la estructura del sermón. Casi todo crece con los minutos, así que recortar solo la predicación también ahorra. El desglose y cómo gastar menos están en [docs/costos-openai.md](docs/costos-openai.md), y la comparación con Groq en [docs/costos-groq.md](docs/costos-groq.md).

Las claves se guardan en `~/Mirame/configuracion.json`, con permisos de lectura solo para tu usuario. También puedes darlas como variables de entorno, que tienen prioridad sobre el archivo:

| Variable | Para qué |
|---|---|
| `GROQ_API_KEY` | Transcripción y, si no hay otro, el modelo de lenguaje |
| `OPENAI_API_KEY` | Modelo de lenguaje y, si no hay clave de Groq, la transcripción |
| `MIRAME_OPENAI_MODELO` | Otro modelo de OpenAI para las lecturas y la estructura |
| `MIRAME_API` | `groq` u `openai`: usar solo esa API para transcribir y analizar, aunque haya otras claves. Vacío = automático |
| `MIRAME_WHISPER_URL`, `MIRAME_WHISPER_KEY`, `MIRAME_WHISPER_MODELO` | Otro servicio de Whisper compatible con OpenAI (p. ej. `https://api.openai.com/v1`, `whisper-1`) |
| `MIRAME_LLM_URL`, `MIRAME_LLM_KEY`, `MIRAME_LLM_MODELO` | Otro modelo compatible con OpenAI para las lecturas y la estructura (URL terminada en `/v1`) |
| `MIRAME_DATOS` | Otra carpeta de datos en lugar de `~/Mirame` |

### Desde la terminal

Todo lo que hace la app también se puede hacer con comandos. Donde dice `<análisis>` va el id que muestra `mirame lista` o la ruta de su carpeta.

```bash
# Analizar solo la predicación (de 32:10 a 1:18:40)
mirame analizar "https://www.youtube.com/watch?v=XXXX" --inicio 32:10 --fin 1:18:40

# Ver los análisis guardados y abrir uno
mirame lista
mirame ver <análisis>

# Separar la lectura bíblica y la oración (requiere clave de IA)
mirame lecturas <análisis>

# Estructura del sermón: partes, argumento, evangelio, aplicaciones y pasajes (requiere clave de IA)
mirame estructura <análisis>
mirame estructura <análisis> --mostrar               # verla otra vez sin consultar a la IA

# Capturas PNG: cuatro momentos elegidos solos, o los que digas
mirame capturar <análisis>
mirame capturar <análisis> --en 19:32 --en 41:45 --resumen

# Ajustar sin volver a procesar el video
mirame recalcular <análisis> --umbral 18             # más o menos estricto con la cabeza
mirame recalcular <análisis> --calibrar 0:00-3:00    # postura habitual tomada de esos minutos
mirame recalcular <análisis> --excluir 5:10-6:40     # dejar fuera un tramo

# Revisar a ojo: 20 fotogramas al azar de cada clase, con el ángulo dibujado
mirame muestras <análisis>

# Comparar con un etiquetado tuyo, segundo a segundo
mirame validar <análisis> etiquetas.csv

mirame borrar <análisis>
mirame --help                                         # todas las opciones
```

---

## Dónde quedan tus datos

Todo vive en `~/Mirame` (en Windows, `C:\Users\<tu usuario>\Mirame`):

```
~/Mirame/
├── analisis/<fecha>_<id>/
│   ├── reporte.html          el reporte; se abre sin conexión y se puede compartir
│   ├── video.mp4             el sermón recortado
│   ├── resumen.json          las cifras del análisis
│   ├── segundos.csv          una fila por segundo: clase, inclinación, ojos
│   ├── fotogramas.csv        una fila por fotograma (4 por segundo)
│   ├── transcripcion.json    si usaste IA: frases con su tiempo
│   ├── lecturas.json         si usaste IA: tramos de lectura bíblica y oración (editable)
│   ├── estructura.json       si usaste IA: la estructura y el contenido del sermón (editable)
│   ├── estructura.md         lo mismo, como texto para leer o compartir
│   └── capturas/             los PNG
├── descargas/                caché de videos completos de YouTube
├── modelos/                  modelo de MediaPipe
└── configuracion.json        claves de IA
```

Si la IA marcó mal una lectura, puedes corregir `lecturas.json` a mano y aplicar el cambio con `mirame lecturas <análisis> --solo-recalcular`. Lo mismo con `estructura.json`: corrígelo y regenera el reporte con `mirame reporte <análisis>`.

---

## Problemas comunes

**YouTube no deja descargar** («Sign in to confirm you're not a bot» o un error 403). YouTube cambia seguido. Actualiza Mírame (vuelve a ejecutar el comando de instalación), que trae la versión más reciente de yt-dlp. Si sigue fallando, descarga el video por tu cuenta y elígelo como archivo en la app.

**«Sin dato» en buena parte del sermón.** La cámara no muestra la cara del predicador (planos lejanos, la congregación, diapositivas). Esos segundos no cuentan en los porcentajes. Si pasan del 30 %, el reporte avisa que el resultado es poco confiable.

**Las capturas no funcionan.** Corre `mirame instalar-capturas`. Si instalaste a mano sin `[capturas]`, usa el comando de instalación.

**`mirame` no se reconoce como comando.** Cierra la terminal y abre una nueva, o usa el acceso directo del escritorio.

**El puerto 8710 está ocupado.** Mírame prueba solo los siguientes, o usa `mirame app --puerto 9000`.

---

## Contribuir

Las contribuciones son bienvenidas: errores, mejoras de la app y, sobre todo, mejoras del método con evidencia. El flujo de trabajo (ramas, pull requests, versiones y publicaciones) está en [CONTRIBUTING.md](CONTRIBUTING.md). Participar implica aceptar el [código de conducta](CODE_OF_CONDUCT.md). Las vulnerabilidades se reportan en privado (ver [SECURITY.md](SECURITY.md)).

```bash
git clone https://github.com/jacomv/mirame && cd mirame
uv sync --extra capturas --group dev
uv run mirame instalar-capturas
uv run mirame                 # la app con tu código
uv run pytest                 # pruebas
uv run ruff check src tests   # estilo
```

Los cambios de cada versión están en el [CHANGELOG](CHANGELOG.md).

## Licencia

[MIT](LICENSE) © 2026 Jacobis Aldana. Puedes usarlo, modificarlo y distribuirlo, también con fines comerciales, siempre que conserves el aviso de copyright y la licencia en las copias.

Incluye [Chart.js](https://www.chartjs.org) (MIT) para las gráficas del reporte.
