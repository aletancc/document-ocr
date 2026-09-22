"""
Script di test per perform_ocr.

Il PDF/immagine NON va copiato dentro il progetto né incollato in base64 da
nessuna parte a mano: resta dove si trova sul tuo disco, e questo script lo
legge e lo converte in base64 al volo, solo in memoria, ad ogni esecuzione.

Uso:
    python test_ocr.py /percorso/al/documento.pdf
    python test_ocr.py /percorso/al/documento.pdf --language ita
"""

import argparse
import base64
import mimetypes
import os
import sys

from server import perform_ocr


def main() -> None:
    parser = argparse.ArgumentParser(description="Testa il tool perform_ocr su un file locale")
    parser.add_argument("file_path", help="Percorso del PDF o immagine da testare")
    parser.add_argument("--language", default="auto", help="Lingua per l'OCR (es. ita, eng, auto)")
    args = parser.parse_args()

    if not os.path.isfile(args.file_path):
        print(f"File non trovato: {args.file_path}", file=sys.stderr)
        sys.exit(1)

    with open(args.file_path, "rb") as f:
        file_bytes = f.read()

    file_b64 = base64.b64encode(file_bytes).decode("utf-8")
    filename = os.path.basename(args.file_path)
    mime_type, _ = mimetypes.guess_type(args.file_path)

    print(f"File: {filename} ({len(file_bytes) / 1024:.1f} KB, mime={mime_type})")
    print("Chiamata a perform_ocr in corso...\n")

    result = perform_ocr(
        file_base64=file_b64,
        filename=filename,
        mime_type=mime_type,
        language=args.language,
    )

    print(f"success: {result['success']}")
    print(f"pages_processed: {result['pages_processed']}")
    if result["error"]:
        print(f"error: {result['error']}")
    print("\n--- TESTO ESTRATTO ---\n")
    print(result["text"])


if __name__ == "__main__":
    main()
