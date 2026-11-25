from pathlib import Path

from dotenv import load_dotenv

from cli import SupportCLI
from config import AppConfig
from errors import ConsultaInvalidaError, ContratoInvalidoError
from prompt_builder import PromptBuilder
from response_handler import ResponseHandler
from router import Router


def main() -> None:
    """Coordina los pasos para responder una consulta desde la terminal."""
    cli = SupportCLI()
    project_dir = Path(__file__).resolve().parent.parent

    try:
        args = cli.read_arguments()
        config = AppConfig(project_dir / "config.toml")
        load_dotenv(project_dir / ".env")
        builder = PromptBuilder(args.consulta, config.prompt_path)
        messages = builder.build_messages()
        router = Router(config, args.provider)
        handler = ResponseHandler(router)
        response = handler.obtener_respuesta_validada(messages, builder.parameters)
    except ConsultaInvalidaError as error:
        cli.show_error(f"ConsultaInvalidaError: {error}")
    except ContratoInvalidoError as error:
        cli.show_error(f"ContratoInvalidoError: {error}")
    except (ValueError, RuntimeError) as error:
        cli.show_error(str(error))

    cli.show_response(response.model_dump_json(), router.obtener_usage())


if __name__ == "__main__":
    main()
