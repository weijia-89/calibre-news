"""CLI entry point for the `getnews` console script."""

from .build import main as build_main


def main() -> None:
    build_main()


if __name__ == "__main__":
    main()