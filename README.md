# M1 — Aplicación de soporte con IA

Proyecto de Maxi Fabbri para el módulo 1 de AI Engineer de Henry.

## Objetivo

Construir una herramienta para los agentes de soporte de Nubbix, un servicio
de gestión para pymes de LATAM. La aplicación recibirá una consulta en texto,
la clasificará, propondrá una respuesta y sugerirá acciones para el agente humano.

La consigna completa está en [Consigna_Modulo_M1.md](Consigna_Modulo_M1.md).

## Cómo deberá funcionar

La aplicación se usará desde una CLI: una interfaz de línea de comandos,
es decir, desde la terminal.

La salida final será JSON validado con estos cuatro campos:

| Campo | Significado |
| --- | --- |
| `answer` | Respuesta propuesta para la consulta. |
| `confidence` | Nivel de confianza informado por el modelo; por sí solo no garantiza que la respuesta sea correcta. |
| `category` | Una de estas categorías: `billing`, `technical`, `account`, `other`. |
| `actions` | Lista de acciones sugeridas para el agente humano. |

Las categorías representan facturación, problemas técnicos, gestión de cuenta
y otros temas, respectivamente.

## Estado actual

`src/main.py` recibe un prompt, rechaza entradas vacías, carga la configuración
y pasa el texto al router. El router delega la llamada a `GeminiProvider` o
`OpenAIProvider`, según `LLM_PROVIDER`, y
`main.py` imprime su respuesta.
Los reportes de consumo, el contrato JSON y
las demás funcionalidades del recorrido se incorporarán en pasos posteriores.

## Primer paso implementado

El programa inicial:

1. Recibe la consulta como argumento desde la terminal.
2. Rechaza una consulta vacía con un mensaje claro.
3. Carga `config.toml` y crea el router.
4. Envía el prompt al proveedor configurado e imprime la respuesta del modelo.

Este paso necesita Python 3.11 o posterior por el lector de TOML incorporado.
Con el entorno virtual activo, instalá las dependencias desde la carpeta del proyecto:

```powershell
python -m pip install -r requirements.txt
```

Para un proyecto nuevo, copiá `.env.example` a `.env` y completá tus claves.
Si ya tenés `.env`, conservá el existente: contiene solo las claves de API.
Las opciones que se editan habitualmente están en `config.toml`, en la raíz del
proyecto: `LLM_PROVIDER`, `LLM_MAX_OUTPUT_TOKENS`,
`LLM_TEMPERATURE` y `LLM_TOP_P`.
El proveedor inicial es `gemini`. Este archivo puede versionarse porque no
contiene credenciales. El router registra `gemini-3.5-flash-lite` para Gemini y
`gpt-4.1-mini` para OpenAI. Otros proveedores y modelos podrán incorporarse sin
agregar parámetros específicos a `AppConfig`.

Para usar OpenAI, cambiá `LLM_PROVIDER` a `"openai"` y configurá `OPENAI_API_KEY`
en `.env`. La clave se lee solo cuando se consulta ese proveedor. El comando de
ejecución es el mismo. Gemini sigue seleccionado inicialmente.
GPT-4.1 mini requiere acceso y saldo o facturación en la API de OpenAI;
no tiene nivel gratuito según la [ficha oficial](https://developers.openai.com/api/docs/models/gpt-4.1-mini).

Según los [precios oficiales de Google](https://aistudio.google.com/docs/pricing#gemini-3.5-flash-lite),
este modelo ofrece entrada y salida de texto gratuitas en el nivel Free Tier.
La gratuidad depende de que el proyecto de la clave use ese nivel y de sus cuotas;
el nombre del modelo por sí solo no garantiza costo cero en un proyecto de pago.

`main.py` crea la configuración con `AppConfig(project_dir / "config.toml")`.
Su constructor lee el archivo usando `tomllib` y guarda las opciones generales.
No hay parámetros ni atributos separados para cada proveedor o modelo.
`GeminiProvider` carga `GEMINI_API_KEY` desde `.env` al recibir una consulta.
Si todavía no tenés una clave,
podés crearla en [Google AI Studio](https://aistudio.google.com/api-keys).

El archivo es `src/main.py`. Ejemplos ejecutados desde la carpeta del proyecto:

```powershell
python src/main.py "No puedo iniciar sesión."
```

El comando ya devuelve una respuesta real de IA en texto libre. El contrato
JSON se incorporará en pasos posteriores. Se verificó la conexión con una
consulta breve que devolvió `Hola, Gemini funciona.`.

`src/cli.py` conserva una CLI con selección mediante `--provider`, pero todavía
no se utiliza desde `main.py`.

`src/router.py` recibe la configuración y el prompt. Guarda los proveedores
en `self.adapters` y el proveedor seleccionado en `self.primary`. Su método
`ask` delega la consulta mediante `self.adapters[self.primary].ask(prompt)` y
la ejecuta dentro de `call_with_backoff`, definido en `src/backoff.py`.

`src/providers.py` contiene la clase base `Provider` con el método `ask` y las
implementaciones `GeminiProvider` y `OpenAIProvider`. Cada una utiliza el SDK
de su proveedor, pasa el límite de tokens, la temperatura y top-p desde
`config.toml` y devuelve texto. El modelo se elige en el router y se entrega
al crear el adaptador. `OpenAIProvider` usa Chat Completions, como el ejemplo
del curso, con `messages=[{"role": "user", "content": prompt}]`. El límite
de tokens se envía como `max_completion_tokens`, según la
[referencia oficial](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create).
Para incorporar otro proveedor, se agregará una clase que implemente `ask`
y una entrada en `self.adapters`. El fallback por cuota queda para una etapa posterior.
Los reintentos internos de los SDK están desactivados para controlarlos desde
el router. La conexión, el razonamiento y las continuaciones conservan las
opciones predeterminadas de cada SDK. Otros controles se incorporarán a medida
que se estudien.
Si falta la clave, la CLI muestra un mensaje.

## Reintentos con backoff

`src/backoff.py` implementa el patrón del curso: ejecutar una función y, si
falla por un límite temporal de solicitudes HTTP 429, esperar y volver a intentar.
Como en el ejemplo, `max_retries=5` significa hasta cinco llamadas totales.
Se esperan aproximadamente 1, 2, 4 y 8 segundos, más un valor aleatorio entre
0 y 1 segundo (jitter). Después del último fallo se informa el error sin esperar.

Cuando el proveedor indica cuánto esperar, esa demora tiene prioridad: se lee
`Retry-After` del header HTTP (segundos o fecha), el atributo `retry_after`
si existe, o `google.rpc.RetryInfo.retryDelay` del JSON de Gemini.
Los valores inválidos se reemplazan por el backoff calculado. Los avisos de
espera salen por stderr y la respuesta del modelo se imprime por stdout.

No se reintentan errores 400, 401, 403 ni otros códigos distintos de 429 en
esta etapa. El error `insufficient_quota` de OpenAI se informa sin reintentar,
porque requiere revisar saldo o facturación. El fallback entre proveedores
todavía está pendiente. Ver las [indicaciones oficiales sobre rate limits](https://developers.openai.com/api/docs/guides/rate-limits).

## Parámetros de generación y rol

`config.toml` define `LLM_TEMPERATURE = 0.2` y `LLM_TOP_P = 0.85` como valores
actuales. `AppConfig` los lee como `config.temperature` y `config.top_p`;
`GeminiProvider` los pasa a `GenerateContentConfig` mediante `temperature` y `top_p`;
`OpenAIProvider` los pasa directamente a `chat.completions.create`.
La temperatura modifica el muestreo de las posibles continuaciones; top-p limita
los candidatos por su probabilidad acumulada. Son opciones para experimentar,
no garantías de exactitud ni de respuestas idénticas.

La consulta recibida desde la terminal se envía explícitamente con `role="user"`.
Ese rol identifica el mensaje como una consulta del usuario, como en los ejemplos
del curso. En Gemini se representa con `types.Content(role="user", parts=[...])`.
Esta etapa no agrega una identidad ni instrucciones del sistema al asistente.
Los prompts versionados en YAML se incorporarán más adelante.

## Orientación a objetos y SOLID

Los componentes preparados para las próximas etapas separan responsabilidades:

| Archivo | Responsabilidad |
| --- | --- |
| `src/config.py` | `AppConfig` lee `config.toml` al crear el objeto. |
| `src/cli.py` | `SupportCLI` recibe una instancia de configuración y gestiona la interacción con la terminal. |
| `src/router.py` | `Router` registra los adaptadores con sus modelos y delega la consulta al proveedor seleccionado. |
| `src/backoff.py` | Ejecuta la consulta con espera creciente ante un límite temporal de solicitudes. |
| `src/providers.py` | `Provider` define el método común; `GeminiProvider` y `OpenAIProvider` cargan sus claves y llaman a sus APIs. |
| `src/main.py` | Recibe el prompt, crea la configuración y el router e imprime el resultado. |

La configuración se entrega al constructor del router mediante `Router(config)`.
Esto permite que el router reciba las opciones sin encargarse de leer el archivo.
El constructor de `AppConfig` recibe solamente la ruta del archivo; agregar
modelos más adelante no requerirá sumar parámetros por proveedor a esa clase.

`Provider.ask(prompt)` define un contrato común que devuelve texto. El router
crea los adaptadores en su constructor y utiliza su método `ask` para delegar
la consulta. Hay dos implementaciones: `GeminiProvider` y `OpenAIProvider`.
La creación externa de adaptadores y el fallback quedan para etapas posteriores.

## Recorrido del proyecto

Cada etapa puede requerir varios pasos; trabajaremos un archivo por vez.

1. Recibir una consulta por CLI.
2. Definir y validar el contrato de salida con Pydantic.
3. Configurar credenciales y dependencias, y conectar un primer proveedor con un prompt en YAML.
4. Agregar reintentos y manejo de errores de API y de respuestas inválidas.
5. Incorporar un segundo proveedor configurable.
6. Registrar tokens, latencia y costo estimado por consulta en `data/metrics.jsonl`.
7. Aplicar controles de entrada y salida para moderación y mitigación de prompt injection.
8. Construir un dataset de al menos 30 casos etiquetados y un evaluador ejecutable por comando.
9. Comparar al menos dos versiones de prompts YAML y justificar la técnica de context engineering con resultados globales y por categoría.
10. Completar la documentación de instalación, uso, decisiones y resultados reales.

La suite de 10 ataques adversariales figura como bonus. Los extra credits se
considerarán después del flujo principal; la rúbrica también menciona al menos
uno entre FastAPI, caché, LLM-as-judge o comparativa de modelos.

## Forma de trabajo

- Avanzar con un solo archivo por paso.
- Mantener cada cambio pequeño y explicar los conceptos nuevos.
- Revisar y ejecutar el código antes de pasar al siguiente paso.
- Esperar las consultas del estudiante antes de continuar.

## Decisiones pendientes

- Comparar los proveedores configurados: Gemini 3.5 Flash-Lite y GPT-4.1 mini.
- Precisar los tipos y restricciones de cada campo del contrato.
- Definir qué información y políticas de soporte tendrá disponible el modelo.
- Documentar el uso de IA como apoyo al desarrollo, como solicita la guía.
