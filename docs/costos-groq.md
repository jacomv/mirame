# Costos de ejemplo con Groq

Este documento repite el ejemplo de [costos-openai.md](costos-openai.md) con el mismo sermón, desde cero, como si la única clave fuera una de Groq. Se hizo dos veces: con la capa gratuita y con el plan de pago.

Es un ejemplo, no una tarifa: los precios y los límites de Groq cambian, y el modelo no gasta lo mismo en cada corrida.

## En corto

- **Con el plan de pago, el análisis completo costó unos 4,5 centavos de dólar** (0,045 USD). Con OpenAI el mismo sermón costó 0,98 USD.
- **Con la capa gratuita no se cobra nada**, pero la estructura del sermón no sale: el sermón completo no cabe en su límite de 8000 tokens por minuto. La transcripción y las lecturas sí.
- **Es más rápido:** toda la parte de IA tardó 52 segundos, contra casi 4 minutos con OpenAI.
- **La pestaña «Sermón» sale mejor con los modelos de OpenAI.** Con el modelo de Groq el análisis del sermón salió más corto y sin aplicaciones, y se marcaron menos lecturas bíblicas.

## El ejemplo

| | |
|---|---|
| Sermón | El mismo: 35:36 (2136 segundos); la transcripción tuvo 427 frases y unas 3900 palabras |
| Qué se pidió | «Nuevo análisis» en la app, con «Separar la lectura bíblica y la oración» y «Analizar la estructura del sermón» activados |
| Configuración | Mírame con solo una clave de Groq y los modelos por defecto |
| Fecha | 24 de noviembre de 2026 |
| **Costo con el plan de pago** | **0,045 USD** |
| Costo con la capa gratuita | 0 USD, sin estructura |

## Con el plan de pago, por etapa

| Etapa | Modelo | Consultas | Entrada | Salida (de ella, razonamiento) | Costo (USD) |
|---|---|---|---|---|---|
| Transcripción | `whisper-large-v3-turbo` | 2 | 35,6 min de audio | — | 0,0237 |
| Lecturas y oración | `openai/gpt-oss-120b` | 5 | 12 183 tokens | 6012 (5780) | 0,0054 |
| Estructura, argumento y clímax | `openai/gpt-oss-120b` | 1 | 10 219 | 2315 (1085) | 0,0029 |
| Evangelio y aplicaciones | `openai/gpt-oss-120b` | 1 | 9814 | 4260 (2893) | 0,0040 |
| Pasajes citados | `openai/gpt-oss-120b` | 5 | 12 538 | 11 414 (9705) | 0,0087 |
| **Total** | | **14** | | | **0,0448** |

Las 14 consultas respondieron a la primera, sin esperas.

Precios usados, de la [documentación de modelos de Groq](https://console.groq.com/docs/models), consultados el 24 de noviembre de 2026:

| Modelo | Precio | Costo (USD) | Parte del total |
|---|---|---|---|
| `whisper-large-v3-turbo` | 0,04 USD por hora de audio | 0,0237 | 53 % |
| `openai/gpt-oss-120b` | 0,15 USD por millón de tokens de entrada y 0,60 USD por millón de salida | 0,0211 | 47 % |

El razonamiento se contó como salida. La tabla usa el precio completo de entrada. En esta corrida Groq sirvió 16 896 tokens de entrada desde su caché, a mitad de precio, porque el mismo sermón se había enviado minutos antes: con ese descuento fueron 0,0436 USD. Un sermón que se analiza por primera vez no lo tiene.

## Qué muestra el ejemplo

- **La transcripción es más de la mitad del costo.** Con OpenAI era el 22 %; aquí el texto cuesta tan poco que el audio pesa más.
- **El modelo razona mucho:** 19 463 de los 24 001 tokens de salida fueron razonamiento.
- **Los límites del plan de pago sobran:** 250 000 tokens por minuto, contra los 8000 de la capa gratuita.

## Con la capa gratuita

La misma corrida, antes de pagar, no cobró nada y terminó sin estructura:

| Etapa | Resultado |
|---|---|
| Transcripción | Completa, en 15 segundos |
| Lecturas y oración | Completa, en 74 segundos: Groq respondió tres veces «429» por el límite y Mírame esperó y reintentó |
| Estructura, argumento y clímax | Rechazada con un error 413: pedía 10 567 tokens |
| Evangelio y aplicaciones | Rechazada con un error 413: pedía 10 059 tokens |
| Pasajes citados | No llegó a usarse |

La capa gratuita limita `openai/gpt-oss-120b` a **8000 tokens por minuto**. Las dos consultas que leen el sermón completo piden más que eso ellas solas, así que esperar no ayuda.

La app termina el trabajo como «Listo», con la mirada y las lecturas, y deja este aviso en el avance: «No se analizó la estructura del sermón».

Para que la estructura quepa, las instrucciones y la transcripción juntas tienen que bajar de 8000 tokens. Con el ritmo de este predicador eso sería un sermón de menos de unos 25 minutos. Es una estimación: no se probó.

Los límites que devolvió Groq en cada respuesta:

| Modelo | Capa gratuita | Plan de pago |
|---|---|---|
| `openai/gpt-oss-120b` | 8000 tokens por minuto y 1000 peticiones por día | 250 000 tokens por minuto y 500 000 peticiones por día |
| `whisper-large-v3-turbo` | 2000 peticiones por día | 200 000 peticiones por día |

## La pestaña «Sermón» sale mejor con OpenAI

Con el mismo sermón, el análisis de los modelos de OpenAI fue más completo que el del modelo de Groq:

| | Groq (`openai/gpt-oss-120b`) | OpenAI (`gpt-5.4` y `gpt-5.5`) |
|---|---|---|
| Partes del sermón | 5 | 11 |
| Aplicaciones | 0 | 7 en una corrida y 9 en otra |
| Pasajes citados | 37 | 45 |
| ¿Estructura clara? | Poco clara | Clara, en las dos corridas |
| Tramos de lectura bíblica | 5 (161 segundos) | 11 (399 segundos) |
| Oración final (34:21 a 35:17) | Marcó solo los últimos 10 segundos | La marcó entera |
| Congregación / notas / Biblia | 65,5 % / 28,7 % / 5,9 % | 66,6 % / 22,3 % / 11,1 % |
| Tiempo de la parte de IA | 52 segundos | 3 minutos 48 segundos |

- **El sermón:** el modelo de Groq lo dividió en menos partes, no registró ninguna aplicación y encontró menos pasajes.
- **Las lecturas:** marcó menos de la mitad del tiempo de lectura bíblica y casi nada de la oración final, que está completa en las dos transcripciones. Por eso con Groq sube el porcentaje de «notas» y baja el de «Biblia».
- **Lo que también cambia con OpenAI:** entre dos corridas de `gpt-5.5`, una dijo que el predicador anunció sus puntos y la otra que no. El modelo no responde siempre igual.

Por eso, para la pestaña «Sermón» conviene usar los modelos de OpenAI. Es una comparación con un solo sermón: no se revisó contra el video cada diferencia.

## Un error que apareció al medir

Con el plan de pago, las primeras dos corridas tampoco dieron la estructura. Groq respondía un error 400, `json_validate_failed`.

La causa: si no se le pide más, Groq corta cada respuesta en 3072 tokens, y el razonamiento del modelo cuenta. Cuando el razonamiento se comía todo, el JSON llegaba vacío. En seis pruebas directas, dos fallaron así y tres se cortaron.

Mírame ahora le pide a Groq hasta 16 000 tokens por respuesta. Con ese cambio, seis pruebas de seis respondieron completas, y la corrida de arriba salió entera.

## Qué conviene

- **Solo quieres la mirada con las lecturas separadas:** la capa gratuita de Groq alcanza.
- **Quieres la estructura por centavos:** el plan de pago de Groq.
- **Quieres la mejor pestaña «Sermón»:** OpenAI. Con las dos claves, Groq transcribe y OpenAI analiza el texto; en el [ejemplo de OpenAI](costos-openai.md) eso habría costado 0,77 USD en lugar de 0,98.

Cuál se usa se elige en Ajustes, en «Qué API usar»: lo automático (Groq transcribe y OpenAI analiza), «Solo OpenAI» o «Solo Groq».

## Cómo se midió

Igual que en el ejemplo de OpenAI: se anotó el campo `usage` de cada respuesta de la API y se multiplicó por los precios de lista. Aquí se anotaron además el código de cada intento y las cabeceras `x-ratelimit-*` y `retry-after`.

Lo que Groq cobra de verdad se ve en su [consola](https://console.groq.com).
