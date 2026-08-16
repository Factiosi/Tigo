"""Entry point for the standalone TigoUpdate.exe build."""

from src.update_splash.app import run_update_splash


def main() -> None:
    run_update_splash()


if __name__ == "__main__":
    main()
