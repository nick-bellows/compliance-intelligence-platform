from __future__ import annotations

import argparse

from compliance_intelligence import __version__


def main() -> int:
    parser = argparse.ArgumentParser(description="Compliance intelligence project utilities")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()
    if args.version:
        print(__version__)
        return 0
    parser.print_help()
    return 0

