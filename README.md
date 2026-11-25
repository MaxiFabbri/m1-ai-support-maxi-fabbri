# M1 — Aplicación de soporte con IA

Proyecto de Maxi Fabbri para el módulo 1 de AI Engineer de Henry.

## Objetivo y estado actual

Construir una herramienta para los agentes de soporte de Nubbix, un servicio
de gestión para pymes de LATAM. Recibirá una consulta, la clasificará, propondrá
una respuesta y sugerirá acciones para el agente humano.

La consigna completa está en [Consigna_Modulo_M1.md](Consigna_Modulo_M1.md).

Actualmente funciona la consulta por CLI con Gemini, OpenAI o NVIDIA, usando
plantillas YAML versionadas. `ResponseHandler` obtiene y valida las respuestas
con Pydantic. Si el JSON está mal formado o no cumple el contrato, repite la
consulta al mismo proveedor, hasta tres intentos totales. Si todos fallan, la CLI
informa los errores acumulados y termina con código 2.

El contrato validado tiene estos cuatro campos obligatorios:

| Campo | Significado |
| --- | --- |
| `answer` | Respuesta propuesta para la consulta. |
| `confidence` | Confianza informada por el modelo; no garantiza exactitud. |
| `category` | Una de `billing`, `technical`, `account`, `other`. |
| `actions` | Lista de acciones sugeridas para el agente humano. |

## Instalación

Requiere Python 3.11 o posterior por el lector de TOML incorporado.
Desde la carpeta del proyecto, con el entorno virtual activo:

```powershell
python -m pip install -r requirements.txt
```

Para un proyecto nuevo, copiá `.env.example` a `.env` y completá las claves,
los modelos y la URL de NVIDIA. Si ya tenés `.env`, conservá el existente.
Las variables de la terminal tienen prioridad sobre las de `.env`.

| Proveedor | Variables requeridas |
| --- | --- |
| `gemini` | `GEMINI_API_KEY`, `GEMINI_MODEL_ID` |
| `openai` | `OPENAI_API_KEY`, `OPENAI_MODEL_ID` |
| `nvidia` | `NVIDIA_API_KEY`, `NVIDIA_MODEL_ID`, `NVIDIA_BASE_URL` |

Para el endpoint alojado de NVIDIA, la URL base es
`https://integrate.api.nvidia.com/v1`. También se puede configurar otro endpoint
compatible. Solo el proveedor elegido abre una conexión y comprueba sus variables.

Las opciones generales están en `config.toml`, sin credenciales:

```toml
LLM_PROVIDER = "gemini"
PROMPT_FILE = "prompts/support_prompt_v5.yaml"
```

`AppConfig` resuelve la ruta del YAML respecto de `config.toml`. Los parámetros
de generación se leen del YAML seleccionado.

## Uso

```powershell
python src/main.py "No puedo iniciar sesión."
python src/main.py "Me cobraron dos veces." --provider openai
python src/main.py "No encuentro mi factura." --provider nvidia
```

`--provider` tiene prioridad sobre `LLM_PROVIDER` para esa ejecución. Los nombres
se normalizan a minúsculas. Una consulta vacía o una configuración inválida
producen un mensaje de error y código de salida 2. Las consultas vacías se
identifican como `ConsultaInvalidaError`; agotar las respuestas inválidas se
identifica como `ContratoInvalidoError`.

La CLI muestra el resultado validado como JSON por stdout y el consumo original
del SDK por stderr. El consumo mostrado corresponde a la última llamada realizada.

## Organización y responsabilidades

Se conserva la estructura original: clases comunes con `__init__`, herencia,
métodos, listas y diccionarios. Los mensajes se pasan como una lista de
diccionarios, los parámetros como un diccionario y la respuesta como texto.

El flujo de una consulta es:

```text
main.py
  1. La CLI recibe la consulta.
  2. AppConfig carga config.toml y load_dotenv carga .env.
  3. PromptBuilder lee el YAML y prepara los mensajes.
  4. ResponseHandler consulta mediante Router y valida con SupportResponse.
  5. Si falla la validación, ResponseHandler repite hasta completar tres intentos.
  6. La CLI muestra el primer resultado válido y el consumo de la última llamada.
```

| Archivo | Responsabilidad |
| --- | --- |
| `src/main.py` | Coordinar los pasos de la aplicación. |
| `src/cli.py` | Recibir argumentos y mostrar respuestas y errores. |
| `src/config.py` | Cargar y comprobar las opciones de `config.toml`. |
| `src/prompt_builder.py` | Preparar el prompt desde el YAML y la consulta. |
| `src/router.py` | Seleccionar el proveedor y delegar una llamada. |
| `src/response_handler.py` | Gestionar los intentos para obtener una respuesta validada. |
| `src/errors.py` | Definir `ConsultaInvalidaError` y `ContratoInvalidoError`, como en el ejemplo de clase. |
| `src/support_response.py` | Definir los cuatro campos y sus reglas de validación con Pydantic. |
| `src/providers/base.py` | Definir `ask` y compartir la lectura de variables de entorno. |
| `src/providers/gemini_provider.py` | Consultar Gemini. |
| `src/providers/openai_provider.py` | Consultar OpenAI. |
| `src/providers/nvidia_provider.py` | Consultar NVIDIA. |
| `src/usage.py` | Mostrar el consumo original del SDK por stderr. |

`PromptBuilder(prompt, prompt_path)` mantiene la forma que veníamos usando.
Sus métodos separan lectura del YAML, validación de la consulta, validación de
parámetros y armado del mensaje. Se prepara antes de llamar al router.

Los proveedores reciben `ask(messages, parameters)` y devuelven un `str`.
Cada uno guarda el consumo original en `last_usage`. El router lo expone mediante
`obtener_usage()` para que la CLI lo muestre. Los proveedores no leen plantillas
ni imprimen resultados. `ResponseHandler` valida el texto con `SupportResponse`.
`main.py` recibe el objeto validado y lo serializa a JSON para su presentación.

Cada adaptador conserva métodos pequeños para crear el cliente, consultar la API
y obtener el texto de la respuesta. OpenAI utiliza `max_completion_tokens`;
NVIDIA utiliza `max_tokens` y su propia URL base. Gemini conserva la traducción
de `assistant` al rol `model`.

## POO y principios SOLID con una estructura simple

- **Responsabilidad única:** cada componente se ocupa de una parte del flujo.
  Los métodos de coordinación llaman a métodos pequeños con objetivos concretos.
- **Extensión:** para agregar un proveedor, se crea una clase que hereda de
  `Provider` y se registra en `Router._crear_adaptadores()`.
- **Sustitución:** todos los proveedores ofrecen el mismo método
  `ask(messages, parameters) -> str` y conservan el consumo en `last_usage`.
- **Interfaz pequeña:** cada proveedor implementa `ask`; la lectura de variables
  se comparte en la clase base mediante un método común.
- **Dependencias:** el router trabaja con el método común de los proveedores.
  El diccionario de proveedores se crea dentro del router, como en la estructura original.

El objetivo es aplicar estas ideas con las herramientas ya estudiadas. No hace
falta una clase o un archivo adicional para cada paso de la ejecución.

## Plantillas YAML versionadas

Cada YAML contiene metadatos (`nombre`, `version`, `tecnica`, `fecha`, `notas`),
el mapa `parameters` y el texto `plantilla`.

`PromptBuilder` utiliza `yaml.safe_load` y comprueba los parámetros:

- `temperature`: número entre 0 y 2.
- `top_p`: número entre 0 y 1.
- `max_output_tokens`: entero mayor que cero.

`PromptBuilder` completa `plantilla.format(consulta=self.prompt)`. La única variable
admitida es `{consulta}`; las llaves literales de JSON se duplican en el YAML:
`{{"category": "..."}}`. La consulta se inserta como dato y sus propias llaves
no se vuelven a interpretar como plantilla.

El prompt completo se envía como un mensaje con `role="user"`, como en los ejemplos
del curso. En Gemini se representa mediante `types.Content`.
La temperatura y top-p modifican el muestreo; no garantizan exactitud ni respuestas
idénticas.

Para comparar versiones, copiá el YAML, actualizá sus metadatos y cambiá
`PROMPT_FILE`. Las diferencias se registran en `prompts/CHANGELOG.md`.
Por ahora los adaptadores utilizan los tres parámetros de generación anteriores;
agregar `response_format` en un YAML todavía no activa el modo JSON.

## Validación de respuesta con Pydantic

`src/support_response.py` define `Category`, con las cuatro categorías válidas,
y `SupportResponse`, que hereda de `BaseModel`.

Las reglas actuales son:

- `answer`: texto con al menos un carácter.
- `confidence`: número entre 0 y 1; no se aceptan textos como `"0.8"` ni booleanos.
- `category`: `billing`, `technical`, `account` u `other`.
- `actions`: lista de textos, que puede estar vacía.
- Los cuatro campos son obligatorios y no se aceptan campos adicionales.

`main.py` crea el manejador y le pide una respuesta validada:

```python
handler = ResponseHandler(router)
response = handler.obtener_respuesta_validada(messages, builder.parameters)
cli.show_response(response.model_dump_json(), router.obtener_usage())
```

`model_validate_json` interpreta el texto JSON y comprueba el contrato. Si es
válido, devuelve un objeto `SupportResponse`. Si falla el parsing o alguna regla,
lanza `ValidationError`, que el manejador captura para realizar otro intento.
Si se agota el límite, se informa el error sin presentar un resultado válido.
`model_dump_json` convierte el objeto validado en texto JSON para mostrarlo.
Estos métodos están documentados en la [guía de modelos de Pydantic](https://docs.pydantic.dev/latest/concepts/models/).

La plantilla activa `support_prompt_v5.yaml` pide los cuatro campos. Su límite
es de 400 tokens, en lugar de los 50 de v4, para permitir una respuesta completa.
Las versiones anteriores se conservan para comparación y seguirán siendo rechazadas
si el modelo devuelve únicamente `category`.

Esta validación comprueba formato, tipos y restricciones. No garantiza que la
respuesta propuesta sea correcta ni que la confianza del modelo esté bien calibrada.
La activación del modo JSON específico de cada API sigue pendiente; la validación
local se aplica a la respuesta recibida de cualquiera de los tres proveedores.

## Política de intentos

`ResponseHandler` recibe el router en su constructor y guarda `max_intentos = 3`.
Su método `obtener_respuesta_validada(messages, parameters)` obtiene una respuesta y la valida con
`SupportResponse.model_validate_json`.

La política inicial es simple:

1. Llamar al proveedor seleccionado mediante `Router`.
2. Devolver inmediatamente la respuesta si cumple el contrato.
3. Si Pydantic lanza `ValidationError`, agregar su error como mensaje de corrección para el siguiente intento.
4. Si las tres respuestas son inválidas, lanzar `ContratoInvalidoError` con todos los errores.

El límite incluye la primera llamada: son hasta tres intentos totales. Cada intento
parte de una copia de los mensajes originales y agrega un mensaje con todos los
errores de Pydantic de los intentos anteriores, numerados por intento. El texto
se acumula con `+=` y el mensaje siguiente se prepara dentro del `except`,
sin modificar la consulta original. El límite de tres intentos
acota el crecimiento del mensaje. Los parámetros se mantienen.
La llamada al router está fuera del `try` que captura `ValidationError`, para
que los errores de API o configuración se propaguen sin reintentos.

`Router` conserva la selección y la llamada al proveedor; `SupportResponse`
conserva las reglas de validación. El bucle queda en `ResponseHandler`, fuera de
`main.py`. La lectura del límite desde configuración y el cambio de proveedor
según una política quedan para etapas posteriores.

No se utiliza backoff ni esperas, y los reintentos internos de los SDK siguen
desactivados. La suma del consumo de todos los intentos todavía está pendiente.

## Errores tipados

`src/errors.py` contiene las mismas dos clases del ejemplo de clase, ambas
heredadas directamente de `Exception`:

- `ConsultaInvalidaError`: consulta vacía. Se detecta antes de llamar al proveedor
  y no se reintenta. La CLI comprueba la entrada y `PromptBuilder` también la
  comprueba cuando se utiliza directamente desde Python.
- `ContratoInvalidoError`: se agotaron los intentos sin una respuesta válida.
  Lo lanza `ResponseHandler` con los errores de Pydantic acumulados.

Las capas que detectan el problema usan `raise`. `main.py` captura cada clase
con un `except` separado y llama a `cli.show_error` para mostrar el nombre del
error y su mensaje. La CLI termina con código de salida 2 en ambos casos.
Los errores de API y configuración conservan su manejo actual.

Este paso conserva la CLI. `HTTPException`, los códigos HTTP 400/502 y el endpoint
FastAPI del ejemplo se aplicarán cuando se agregue una interfaz web.

## Verificación local

Con las dependencias instaladas:

```powershell
python -m unittest discover -s tests -v
```

Las pruebas simulan los SDK y no necesitan claves ni consumen créditos.
Verifican el flujo de los tres proveedores, parámetros y roles, selección por CLI,
separación de stdout y stderr, prioridad de variables de entorno, plantillas,
configuraciones inválidas, contrato Pydantic y ausencia de reintentos en el router.
También comprueban el límite de intentos, la detención ante una respuesta válida,
el error tras agotar el límite y la propagación de errores de API sin reintentos.
No reemplazan una comprobación real de
conectividad con cada API. Esta suite comprueba el código; el runner de evaluación
del modelo y su dataset siguen pendientes.

## Próximas etapas

1. Conectar las opciones de salida JSON específicas de cada proveedor.
2. Ampliar progresivamente la política de intentos y el manejo de límites temporales.
3. Registrar tokens, latencia y costo estimado en `data/metrics.jsonl`.
4. Agregar guardrails de entrada y salida.
5. Construir al menos 30 casos etiquetados y un runner de evals por comando.
6. Comparar prompts y modelos con resultados globales y por categoría.
7. Completar la documentación con resultados reales y el uso de IA como apoyo.

La suite de 10 ataques adversariales figura como bonus. La rúbrica también
menciona al menos un extra credit entre FastAPI, caché, LLM-as-judge o comparativa
de modelos.

## Forma de trabajo

- Avanzar con un solo archivo por paso.
- Mantener cada cambio pequeño y explicar los conceptos nuevos.
- Usar las herramientas ya estudiadas y la solución más simple para la etapa actual.
- Introducir conceptos nuevos de a uno, sin anticipar necesidades de etapas futuras.
- Revisar y ejecutar el código antes de pasar al siguiente paso.
- Esperar las consultas del estudiante antes de continuar.

Para recorrer el código, comenzar por `main.py`, que muestra el flujo completo.
Después estudiar un archivo por vez: `cli.py`, `config.py`, `prompt_builder.py`,
`router.py`, `providers/base.py`, un proveedor, `support_response.py`,
`response_handler.py` y `usage.py`.
El backoff se retomará en una etapa posterior.
