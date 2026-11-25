from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

from cli import SupportCLI
from config import AppConfig
from prompt_builder import PromptBuilder
from router import Router
from support_response import SupportResponse


def main() -> None:
    """Coordina los pasos para responder una consulta desde la terminal."""
    cli = SupportCLI()
    args = cli.read_arguments()
    print("Procesando la consulta, por favor espere...")
    print(f"Consulta: {args}")
    project_dir = Path(__file__).resolve().parent.parent

    try:
        config = AppConfig(project_dir / "config.toml")
        load_dotenv(project_dir / ".env")
        builder = PromptBuilder(args.consulta, config.prompt_path)
        messages = builder.build_messages()
        print("----------------------------------------------------------------------------------------------")
        print(f"messages armados por el promptBuilder: {messages}")
        print("----------------------------------------------------------------------------------------------")
        print("datos para Router:")
        print(f"config: {config.__dict__}")
        print(f"args.provider: {args.provider}")
        router = Router(config, args.provider)
        answer = router.ask(messages, builder.parameters)
        response = SupportResponse.model_validate_json(answer)
    except ValidationError as error:
        cli.show_error(f"La respuesta del modelo no cumple el contrato:\n{error}")
    except (ValueError, RuntimeError) as error:
        cli.show_error(str(error))

    cli.show_response(response.model_dump_json(), router.obtener_usage())


if __name__ == "__main__":
    main()
