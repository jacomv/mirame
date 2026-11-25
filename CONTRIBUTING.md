# Contribuir a Mírame

Gracias por querer mejorarlo. Este documento explica cómo se trabaja en el proyecto: ramas, pull requests, versiones y publicaciones. Al participar aceptas el [código de conducta](CODE_OF_CONDUCT.md). Las vulnerabilidades se reportan en privado (ver [SECURITY.md](SECURITY.md)).

## Antes de empezar

- **Errores y mejoras pequeñas:** abre un *issue* con la plantilla que corresponda, o ve directo a un pull request.
- **Cambios grandes o del método de medición:** abre primero un *issue* y conversemos el enfoque. Un cambio en cómo se mide afecta los números de todos los que comparan sermones, así que necesita evidencia.

## Preparar el entorno

```bash
git clone https://github.com/jacomv/mirame && cd mirame
uv sync --extra capturas --group dev
uv run mirame instalar-capturas
```

Para no mezclar tus pruebas con tus análisis reales, usa otra carpeta de datos:

```bash
MIRAME_DATOS=/tmp/mirame-dev uv run mirame
```

## Flujo de trabajo

1. **`main` siempre está publicable.** Nadie trabaja directo sobre `main`.
2. **Una rama por cambio**, con un nombre que diga qué hace: `mejoras/<tema>`, `arreglo/<tema>` o `docs/<tema>`. Las mejoras que van juntas a una versión pueden compartir rama (`mejoras/0.4.0`).
3. **Pull request hacia `main`** con la plantilla completa. La integración continua (GitHub Actions) corre el estilo, las pruebas y la construcción del paquete en Linux y macOS, y todo debe pasar en verde.
4. **Revisión.** Quien mantiene el proyecto revisa y aprueba. Los cambios del método requieren las cifras antes y después en al menos un sermón real.
5. **Fusión** con *merge commit*, para conservar los commits de la rama. La rama se borra después.

### Antes de abrir el pull request

```bash
uv run pytest                  # todas las pruebas deben pasar
uv run ruff check src tests    # sin avisos
```

- Agrega pruebas para lo que cambies en `analisis.py`, `lecturas.py`, `config.py`, `biblioteca.py` o la API del servidor.
- Anota el cambio en la sección **Sin publicar** de [CHANGELOG.md](CHANGELOG.md).
- Si cambias el método de medición, sube `METODO` en `analisis.py` y actualiza [docs/como-funciona.md](docs/como-funciona.md).

### Mensajes de commit

En español, en imperativo y con un prefijo que diga el tipo: `mejora:`, `arreglo:`, `método:`, `docs:`, `pruebas:` o `mantenimiento:`. Ejemplo: `método: filtrar parpadeos de un solo fotograma`. La primera línea va en menos de 72 caracteres; el porqué va en el cuerpo.

## Versiones

Mírame sigue [versionado semántico](https://semver.org/lang/es/). Mientras esté en **0.x**, la API y los formatos de archivo todavía pueden cambiar:

| Cambio | Sube | Ejemplo |
|---|---|---|
| Funciones nuevas, cambios del método, cambios de formato | menor | 0.3.0 → 0.4.0 |
| Arreglos sin cambios de comportamiento esperado | parche | 0.4.0 → 0.4.1 |

La **1.0.0** llegará cuando el método esté validado contra etiquetado humano y los formatos de `resumen.json` y `fotogramas.csv` se consideren estables.

Dos números de versión conviven y no se deben confundir:

- **Versión del programa** (`__version__`, p. ej. 0.4.0): queda en cada `resumen.json`.
- **Versión del método** (`METODO` en `analisis.py`, p. ej. 3): identifica las reglas de clasificación. Dos análisis con métodos distintos no son comparables hasta recalcular el anterior con `mirame recalcular`.

## Publicar una versión

Lo hace quien mantiene el proyecto, desde `main` y con la integración continua en verde:

1. Mueve las notas de **Sin publicar** a una sección nueva `## [X.Y.Z] — AAAA-MM-DD` en `CHANGELOG.md`.
2. Sube la versión en `pyproject.toml` y `src/mirame/__init__.py`, y corre `uv lock`.
3. Commit `versión X.Y.Z`, etiqueta anotada y envío:
   ```bash
   git tag -a vX.Y.Z -m "Mírame X.Y.Z"
   git push origin main vX.Y.Z
   ```
4. Crea el *release* en GitHub con las notas de esa versión del CHANGELOG:
   ```bash
   gh release create vX.Y.Z --title "Mírame X.Y.Z" --notes-file <notas>
   ```

## Cómo está organizado el código

```
src/mirame/
├── cli.py          comandos de terminal (`mirame …`)
├── proceso.py      el flujo completo: video → mirada → reporte → lecturas; estimación de tiempo
├── video.py        datos del video, descarga (yt-dlp), recorte y fotogramas (ffmpeg)
├── pose.py         rostro, pose de la cabeza y ojos con MediaPipe
├── analisis.py     calibrar, clasificar, episodios, miradas, margen de error y resumen
├── lecturas.py     transcripción y marcas de lectura bíblica y oración
├── estructura.py   estructura y contenido del sermón sobre la transcripción
├── reporte.py      arma el reporte HTML autocontenido
├── capturar.py     capturas PNG con Playwright
├── muestras.py     fotogramas de muestra para revisar a ojo
├── biblioteca.py   listar y borrar análisis guardados
├── herramientas.py  ffmpeg incluido, lectura del video sin ffprobe y acceso directo
├── config.py       claves de IA (archivo y variables de entorno)
├── rutas.py        carpeta de datos (~/Mirame)
├── progreso.py     avance por etapas y cancelación de tareas largas
├── web/            la app local: servidor (stdlib), cola de trabajos y página
└── assets/
    ├── reporte/    plantilla, CSS y JS del reporte
    └── vendor/     Chart.js
```

Decisiones que conviene respetar:

- **Instalar es un comando.** Nada que el usuario tenga que instalar aparte: ffmpeg y Deno llegan como paquetes de Python. Si agregas una dependencia, que se instale con `uv` en macOS, Windows y Linux.
- **Sin dependencias para la web.** El servidor usa `http.server` y la página es HTML, CSS y JS sin compilación. Así la instalación sigue siendo un solo comando.
- **El reporte es un solo archivo.** `reporte.py` incrusta CSS, JS, Chart.js y los datos, para que se abra sin conexión y se pueda enviar tal cual.
- **Todo se recalcula desde `fotogramas.csv`.** Lo caro (la pose) se guarda; la clasificación se puede repetir con otras reglas.
- **Repetible.** Nada de azar sin semilla fija: el mismo video con los mismos parámetros da los mismos números.
- **Funciona sin claves de IA.** La IA mejora el resultado, pero ninguna función básica puede depender de ella.
- **Las claves nunca se escriben fuera de `configuracion.json`**, y ese archivo tiene permisos 0600.
- **Código y textos en español.** Nombres de funciones y variables incluidos.

## Atribución

Mírame se publica con licencia MIT. Si distribuyes una versión modificada, conserva el aviso de copyright de Jacobis Aldana y el archivo `LICENSE`.
