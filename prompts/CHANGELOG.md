# Historial de prompts

Este archivo describe los archivos de esta carpeta y registra los cambios entre
versiones de las plantillas de prompts.

## Descripción de los archivos

| Archivo | Descripción |
| --- | --- |
| `support_prompt_v1.yaml` | Plantilla activa para Nubbix: instrucciones, contexto, variable `{consulta}`, metadatos y parámetros de generación. Se selecciona mediante `PROMPT_FILE` en `config.toml`. |
| `instructions_v1.txt` | Instrucciones de la etapa anterior. Se conservan como referencia; la aplicación ahora utiliza el YAML. |
| `context_v1.txt` | Contexto de la etapa anterior, vacío. Se conserva como referencia; la aplicación ahora utiliza el YAML. |
| `CHANGELOG.md` | Descripción de los archivos e historial de cambios de los prompts. |

## Convención de versiones

- Cada YAML versiona el experimento completo: instrucciones, contexto y parámetros.
- Los archivos usan nombres como `support_prompt_v1.yaml`, `support_prompt_v2.yaml`, etc. El campo `version` debe coincidir con el nombre elegido.
- `PROMPT_FILE` en `config.toml` selecciona el YAML que usarán ambos proveedores.
- `PromptBuilder` reemplaza `{consulta}` con el texto recibido por terminal.
- Las llaves literales del JSON se escriben dobles en la plantilla: `{{"category": "..."}}`.
- Para conservar una versión que quieras comparar, copiá el archivo a una versión nueva antes de modificarlo.
- Al registrar una prueba, indicá el YAML, el proveedor, el modelo y los parámetros utilizados.

## Historial

### Contrato validado con Pydantic — 2026-11-25

- **Archivo nuevo:** `support_prompt_v5.yaml`, seleccionado en `config.toml`.
- **Versión anterior:** `support_prompt_v4.yaml`, conservada sin cambios.
- **Cambios:** solicita `answer`, `confidence`, `category` y `actions` con los tipos y límites definidos en `SupportResponse`.
- **Parámetros:** el límite de salida pasa de 50 a 400 tokens para permitir los cuatro campos.
- **Validación:** se comprueba una sola respuesta en `main.py`; los reintentos quedan pendientes.
- **Verificación:** respuestas simuladas; no se realizaron llamadas a APIs ni evaluaciones con modelos reales.

### Plantilla completa en YAML — 2026-11-20

- **Archivo activo:** `support_prompt_v1.yaml`.
- **Cambios:** se adaptó el ejemplo de restaurantes al soporte de Nubbix; instrucciones y contexto forman parte de una plantilla con `{consulta}`.
- **Parámetros:** `temperature: 0.2`, `top_p: 0.85`, `max_output_tokens: 300`, leídos del mismo YAML.
- **Integración:** OpenAI y Gemini reciben el prompt completo como mensaje de usuario. Los TXT ya no se cargan.
- **Verificación:** pruebas locales con respuestas de API simuladas. Los resultados de evaluación con LLMs reales están pendientes.

### Estado inicial documentado — 2026-11-19

- **Instrucciones:** `instructions_v1.txt`.
- **Contexto:** `context_v1.txt`.
- **Descripción:** clasificación de tickets en cuatro categorías, con una respuesta JSON solicitada en las instrucciones. El contexto está vacío.
- **Resultados de evaluación:** pendientes de registrar.

## Plantilla para próximos cambios

Copiá esta plantilla al historial cuando agregues una versión:

```markdown
### [Fecha] — [Descripción breve del cambio]

- **Archivo nuevo:**
- **Versión anterior con la que se compara:**
- **Diferencias:**
- **Motivo o hipótesis:**
- **YAML y versión probados:**
- **Proveedor y modelo:**
- **Parámetros de generación:**
- **Casos probados y resultados:**
```
