import argparse
from pathlib import Path

from config import AppConfig
from router import Router


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Envía un prompt al proveedor configurado e imprime la respuesta."
    )
    parser.add_argument("prompt", help="Texto del prompt entre comillas.")
    args = parser.parse_args()

    if not args.prompt.strip():
        parser.error("El prompt no puede estar vacío.")

    project_dir = Path(__file__).resolve().parent.parent
    config = AppConfig(project_dir / "config.toml")
    try:
        router = Router(config)
        answer = router.ask(args.prompt)
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))

    print("====================================================================")
    print(answer)
    print("====================================================================")


if __name__ == "__main__":
    main()
