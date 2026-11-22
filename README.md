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
y pasa el texto al router. El router delega la llamada a `GeminiProvider`,
`OpenAIProvider` o `NvidiaProvider`, según `LLM_PROVIDER`, y
`main.py` imprime su respuesta.
El consumo se muestra con los campos originales de cada SDK mediante `src/usage.py`.
El contrato JSON validado y las demás funcionalidades del recorrido se incorporarán
en pasos posteriores.

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
Si ya tenés `.env`, conservá el existente: contiene las claves de API, los modelos
y la URL del endpoint de NVIDIA.
Las opciones que se editan habitualmente están en `config.toml`, en la raíz del
proyecto: `LLM_PROVIDER` y `PROMPT_FILE`. Los parámetros de generación están en
el YAML seleccionado por `PROMPT_FILE`.
El proveedor inicial es `gemini`. Este archivo puede versionarse porque no
contiene credenciales. El router registra los tres adaptadores. Cada uno lee su
modelo desde `.env` al recibir una consulta; los nombres de modelos no están
fijados en el código del router.

Las variables requeridas para cada proveedor son:

| `LLM_PROVIDER` | Variables de `.env` |
| --- | --- |
| `openai` | `OPENAI_API_KEY`, `OPENAI_MODEL_ID` |
| `gemini` | `GEMINI_API_KEY`, `GEMINI_MODEL_ID` |
| `nvidia` | `NVIDIA_API_KEY`, `NVIDIA_MODEL_ID`, `NVIDIA_BASE_URL` |

Para usar NVIDIA, cambiá `LLM_PROVIDER = "nvidia"`. Para el endpoint alojado de
NVIDIA, la URL base es `https://integrate.api.nvidia.com/v1`; también se puede
configurar otro endpoint compatible mediante `NVIDIA_BASE_URL`.
El comando de ejecución es el mismo para los tres proveedores. Se comprueban
solamente las variables del seleccionado. Las variables ya definidas en el
entorno de la terminal tienen prioridad sobre `.env`, como en `load_dotenv`.

`main.py` crea la configuración con `AppConfig(project_dir / "config.toml")`.
Su constructor lee el archivo usando `tomllib` y guarda las opciones generales.
No hay parámetros ni atributos separados para cada proveedor o modelo.
`GeminiProvider` carga `GEMINI_API_KEY` y `GEMINI_MODEL_ID` al recibir una consulta.
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

`src/providers/` contiene la clase base `Provider` en `base.py` y las
implementaciones en `gemini_provider.py`, `openai_provider.py` y
`nvidia_provider.py`. Cada una utiliza
el SDK de su proveedor, pasa el límite de tokens, la temperatura y top-p desde
el YAML activo y devuelve texto. El modelo se carga desde la variable
`*_MODEL_ID` correspondiente. `OpenAIProvider` usa Chat Completions, como el ejemplo
del curso, con `messages=[{"role": "user", "content": prompt}]`. El límite
de tokens se envía como `max_completion_tokens`, según la
[referencia oficial](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create).
`NvidiaProvider` reutiliza el SDK de OpenAI con su propia clave y `base_url`,
y traduce `max_output_tokens` del YAML a `max_tokens`, como indica la
[referencia de NVIDIA](https://docs.api.nvidia.com/nim/reference/llm-apis).
El consumo se muestra tal como llega en `usage` o `usage_metadata`, también
para NVIDIA. No hace falta instalar otro SDK.
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

El YAML activo define `parameters.temperature`, `parameters.top_p` y
`parameters.max_output_tokens`. `PromptBuilder` los lee en `builder.parameters`;
`GeminiProvider` los pasa a `GenerateContentConfig` mediante `temperature` y `top_p`;
`OpenAIProvider` los pasa directamente a `chat.completions.create`.
La temperatura modifica el muestreo de las posibles continuaciones; top-p limita
los candidatos por su probabilidad acumulada. Son opciones para experimentar,
no garantías de exactitud ni de respuestas idénticas.

La consulta recibida desde la terminal se envía explícitamente con `role="user"`.
Ese rol identifica el mensaje como una consulta del usuario, como en los ejemplos
del curso. En Gemini se representa con `types.Content(role="user", parts=[...])`.
El mensaje contiene la plantilla completa, que incluye las instrucciones, el
contexto y la consulta insertada en `{consulta}`.

## Plantillas YAML versionadas

`config.toml` selecciona la plantilla mediante:

```toml
PROMPT_FILE = "prompts/support_prompt_v1.yaml"
```

Ese archivo contiene metadatos (`nombre`, `version`, `tecnica`, `fecha`, `notas`),
el mapa `parameters` y el texto `plantilla`. `PromptBuilder` utiliza `yaml.safe_load`
para leerlo, comprueba los parámetros y completa la plantilla con
`plantilla.format(consulta=prompt)`. El ticket se inserta una vez como dato y no
se vuelve a interpretar como plantilla. Las llaves literales de los ejemplos
JSON deben duplicarse en el YAML: `{{"category": "..."}}`.

Para probar otra versión, copiá el YAML a `support_prompt_v2.yaml`, actualizá sus
metadatos y cambiá `PROMPT_FILE`. Instrucciones, contexto y parámetros se versionan
juntos. Los anteriores archivos TXT se conservan como referencia, pero ya no se leen.
Las diferencias se registran en `prompts/CHANGELOG.md`.

La plantilla actual pide JSON de clasificación con `category`; esto es una
instrucción al modelo y todavía no garantiza la validación automática de la salida.

## Orientación a objetos y SOLID

Los componentes preparados para las próximas etapas separan responsabilidades:

| Archivo | Responsabilidad |
| --- | --- |
| `src/config.py` | `AppConfig` lee `config.toml` al crear el objeto. |
| `src/cli.py` | `SupportCLI` recibe una instancia de configuración y gestiona la interacción con la terminal. |
| `src/router.py` | `Router` registra los adaptadores y delega la consulta al proveedor seleccionado. |
| `src/backoff.py` | Ejecuta la consulta con espera creciente ante un límite temporal de solicitudes. |
| `src/providers/` | `Provider` define el método común; los tres adaptadores cargan su configuración de entorno y llaman a sus APIs. |
| `src/prompt_builder.py` | Lee el YAML activo, valida sus parámetros y completa la plantilla con la consulta. |
| `src/usage.py` | Muestra el consumo original del SDK, sin estimar costos ni normalizar campos. |
| `src/main.py` | Recibe el prompt, crea la configuración y el router e imprime el resultado. |

La configuración se entrega al constructor del router mediante `Router(config)`.
Esto permite que el router reciba las opciones sin encargarse de leer el archivo.
El constructor de `AppConfig` recibe solamente la ruta del archivo; agregar
modelos más adelante no requerirá sumar parámetros por proveedor a esa clase.

`Provider.ask(prompt)` define un contrato común que devuelve texto. El router
crea los adaptadores en su constructor y utiliza su método `ask` para delegar
la consulta. Hay tres implementaciones: `GeminiProvider`, `OpenAIProvider` y `NvidiaProvider`.
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

- Comparar los proveedores configurados (Gemini, OpenAI y NVIDIA) con los modelos seleccionados en `.env`.
- Precisar los tipos y restricciones de cada campo del contrato.
- Definir qué información y políticas de soporte tendrá disponible el modelo.
- Documentar el uso de IA como apoyo al desarrollo, como solicita la guía.
