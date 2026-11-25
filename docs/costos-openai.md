# Costos de ejemplo con OpenAI

Medir la mirada no cuesta nada: ese análisis corre en tu computadora. Lo que cuesta es la parte opcional de IA cuando se usa una clave de OpenAI.

Este documento muestra, como ejemplo, lo que costó analizar un sermón completo. No es una tarifa: los precios de OpenAI cambian, y el modelo no gasta lo mismo en cada corrida ni en cada sermón.

## El ejemplo

| | |
|---|---|
| Sermón | 35:36 (2136 segundos); la transcripción tuvo 367 frases y unas 4100 palabras |
| Qué se pidió | «Nuevo análisis» en la app, con «Separar la lectura bíblica y la oración» y «Analizar la estructura del sermón» activados |
| Configuración | Mírame 0.3.0 con solo la clave de OpenAI y los modelos por defecto |
| Fecha | 24 de noviembre de 2026 |
| **Costo total** | **0,98 USD** |

## Por etapa

| Etapa | Modelo | Consultas | Entrada | Salida (de ella, razonamiento) | Costo (USD) |
|---|---|---|---|---|---|
| Transcripción | `whisper-1` | 2 | 35,6 min de audio | — | 0,2136 |
| Lecturas y oración | `gpt-5.4` | 5 | 11 492 tokens | 423 (0) | 0,0351 |
| Estructura, argumento y clímax | `gpt-5.5` | 1 | 9869 | 3147 (512) | 0,1438 |
| Evangelio y aplicaciones | `gpt-5.5` | 1 | 9464 | 3484 (1981) | 0,1518 |
| Pasajes citados | `gpt-5.5` | 5 | 11 847 | 12 541 (10 452) | 0,4355 |
| **Total** | | **14** | | | **0,9797** |

Las tres últimas filas son el análisis de la estructura del sermón: 0,73 USD entre las tres.

## Por modelo

| Modelo | Precio usado | Costo (USD) | Parte del total |
|---|---|---|---|
| `whisper-1` | 0,006 USD por minuto de audio | 0,2136 | 22 % |
| `gpt-5.4` | 2,50 USD por millón de tokens de entrada y 15 USD por millón de salida | 0,0351 | 4 % |
| `gpt-5.5` | 5 USD por millón de tokens de entrada y 30 USD por millón de salida | 0,7311 | 75 % |

Son los precios de la tarifa estándar de la [página de precios de OpenAI](https://developers.openai.com/api/docs/pricing), consultados el 24 de noviembre de 2026. Los tokens de razonamiento se cobran como salida.

## Qué muestra el ejemplo

- **La estructura del sermón es casi todo el costo.** `gpt-5.5` se llevó tres cuartas partes del total.
- **Buscar los pasajes citados fue lo más caro:** el 44 % del total. Las respuestas son cortas, pero el modelo razona mucho antes de darlas: 10 452 de los 12 541 tokens de salida fueron razonamiento.
- **El razonamiento pesa.** Sumando las tres consultas de estructura fueron 12 945 tokens, unos 0,39 USD: el 40 % del total. Es además la parte que más cambia de una corrida a otra.
- **Marcar las lecturas y la oración es barato:** 4 centavos de dólar.
- **No hubo descuento por caché:** todas las consultas se cobraron al precio completo de entrada.
- **Los rechazos no se cobran.** `gpt-5.5` no acepta fijar la temperatura, así que cada consulta falla una vez con un error 400 y Mírame la repite sin ese parámetro. Fueron 7 rechazos, sin costo.

## Para estimar otro sermón

Casi todo crece con los minutos del recorte:

- **Transcripción:** 0,006 USD por minuto de audio.
- **Lecturas y oración:** una consulta por cada 8 minutos. En el ejemplo, menos de 1 centavo por consulta.
- **Pasajes citados:** una consulta por cada 8 minutos. En el ejemplo, entre 7 y 11 centavos por consulta.
- **Estructura** y **evangelio y aplicaciones:** una consulta cada una, con el sermón completo. En el ejemplo, unos 15 centavos cada una; la entrada crece con la duración.

En el ejemplo salieron unos 2,75 centavos de dólar por minuto de sermón. En esa proporción, una hora costaría alrededor de 1,65 USD. Es una extrapolación, no una medición.

## Para gastar menos

- **Recorta solo la predicación.** Cada minuto de alabanza o anuncios que quede dentro se transcribe y se analiza.
- **Agrega una clave de Groq.** Con las dos claves, Groq transcribe y OpenAI solo analiza el texto: en el ejemplo se habría ahorrado la transcripción, el 22 % del total. Con solo la clave de Groq no se usa OpenAI: este mismo sermón costó unos 4,5 centavos de dólar con el plan de pago de Groq, y en su capa gratuita la estructura no llegó a analizarse. Pero la pestaña «Sermón» salió mejor con los modelos de OpenAI: ver [costos-groq.md](costos-groq.md).
- **No repitas lo que ya está.** La transcripción se guarda en `transcripcion.json` y se reutiliza. `mirame estructura <análisis> --mostrar` y `mirame lecturas <análisis> --solo-recalcular` no consultan a la IA. Volver a correr `mirame estructura <análisis>` sí repite sus consultas: en el ejemplo, regenerarla después costó 0,65 USD.
- **Otro modelo.** `MIRAME_OPENAI_MODELO` cambia el modelo de las lecturas y de la estructura a la vez. Uno más barato baja el costo, pero el resultado puede empeorar: al marcar oraciones, un modelo «mini» confundió predicación con oración.

## Cómo se midió

Mírame no guarda el consumo. Para este ejemplo se anotó el campo `usage` que devuelve cada respuesta de la API (tokens de entrada, de salida y de razonamiento, y segundos de audio) y se multiplicó por los precios de lista.

La cifra que vale es la del [panel de uso de OpenAI](https://platform.openai.com/usage): ahí puedes ver lo que costó tu propio sermón.
