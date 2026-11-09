"""Proses sementara untuk mengecilkan satu PDF."""

import sys

from app.shared.pdf import shrink_pdf


def main() -> None:
    ceiling = int(sys.argv[1])
    content = sys.stdin.buffer.read()
    sys.stdout.buffer.write(shrink_pdf(content, ceiling))


if __name__ == "__main__":
    main()
