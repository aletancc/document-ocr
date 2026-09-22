"""
OCR MCP Server
==============

Espone un tool MCP `perform_ocr` che estrae il testo da documenti scansionati
(PDF, JPG, PNG, TIFF, BMP, WEBP) usando l'API di OCR.space.

Progettato per essere collegato come MCP server a un agente Neurons, così da
superare il limite dei Function Call "classici" (che accettano solo parametri
testuali/URL) e ricevere invece il CONTENUTO del file caricato in chat,
codificato in base64.

Variabili d'ambiente richieste:
    OCR_SPACE_API_KEY   -> API key di OCR.space (https://ocr.space/ocrapi)

Esecuzione locale (stdio, per test):
    python server.py

Esecuzione come servizio HTTP (per deploy su Cloud Run / esposizione a Neurons):
    python server.py --http --port 8080
"""

import argparse
import base64
import os
import sys
from typing import Optional

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()  # legge il file .env nella stessa cartella, se presente

OCR_SPACE_ENDPOINT = "https://api.ocr.space/parse/image"
OCR_SPACE_API_KEY = os.environ.get("OCR_SPACE_API_KEY", "")

# Mappa estensioni file -> filetype richiesto da OCR.space
EXTENSION_TO_FILETYPE = {
    "pdf": "PDF",
    "jpg": "JPG",
    "jpeg": "JPG",
    "png": "PNG",
    "gif": "GIF",
    "tif": "TIF",
    "tiff": "TIF",
    "bmp": "BMP",
    "webp": "WEBP",
}

mcp = FastMCP(
    name="OCR Server",
    instructions=(
        "Use the perform_ocr tool to extract text from any scanned document "
        "(PDF, image, invoice, contract, form, report) that has no readable "
        "text layer. Always pass the raw file content as base64, never a URL."
    ),
)


def _guess_filetype(filename: Optional[str], mime_type: Optional[str]) -> Optional[str]:
    """Deduce il filetype OCR.space da nome file o mime type."""
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in EXTENSION_TO_FILETYPE:
            return EXTENSION_TO_FILETYPE[ext]
    if mime_type:
        mime_map = {
            "application/pdf": "PDF",
            "image/jpeg": "JPG",
            "image/png": "PNG",
            "image/tiff": "TIF",
            "image/bmp": "BMP",
            "image/webp": "WEBP",
            "image/gif": "GIF",
        }
        if mime_type in mime_map:
            return mime_map[mime_type]
    return None


def _collect_parsed_text(ocr_json: dict) -> str:
    """Concatena il testo estratto da tutte le pagine, in ordine."""
    parsed_results = ocr_json.get("ParsedResults") or []
    pages = []
    for i, page in enumerate(parsed_results, start=1):
        text = (page.get("ParsedText") or "").strip()
        pages.append(f"--- Page {i} ---\n{text}" if len(parsed_results) > 1 else text)
    return "\n\n".join(pages).strip()


@mcp.tool()
def perform_ocr(
    file_base64: str,
    filename: Optional[str] = None,
    mime_type: Optional[str] = None,
    language: str = "auto",
) -> dict:
    """
    Estrae il testo da un documento scansionato (PDF o immagine) via OCR.space.

    Args:
        file_base64: Contenuto del file codificato in base64 (SENZA il prefisso
            "data:<mime>;base64,"; solo la stringa base64 pura).
        filename: Nome originale del file, usato per dedurre il tipo
            (es. "fattura.pdf"). Opzionale ma consigliato.
        mime_type: MIME type del file (es. "application/pdf"). Opzionale,
            usato come fallback se il filename non basta a dedurre il tipo.
        language: Lingua del documento per l'OCR engine. Usa "ita" per
            documenti in italiano, "eng" per l'inglese, oppure "auto" per
            lasciare che sia questo tool a scegliere l'engine più adatto
            (default "eng" con OCR Engine 2, che riconosce più lingue).

    Returns:
        dict con:
            success (bool)
            text (str): testo estratto, vuoto se fallito
            pages_processed (int)
            error (str | None): messaggio di errore se success è False
    """
    if not OCR_SPACE_API_KEY:
        return {
            "success": False,
            "text": "",
            "pages_processed": 0,
            "error": (
                "OCR_SPACE_API_KEY non configurata lato server. "
                "Contattare l'amministratore del servizio."
            ),
        }

    if not file_base64:
        return {
            "success": False,
            "text": "",
            "pages_processed": 0,
            "error": "Nessun contenuto file ricevuto (file_base64 è vuoto).",
        }

    filetype = _guess_filetype(filename, mime_type)
    resolved_mime = mime_type or "application/octet-stream"
    data_uri = f"data:{resolved_mime};base64,{file_base64}"

    payload = {
        "apikey": OCR_SPACE_API_KEY,
        "base64Image": data_uri,
        "OCREngine": 2,
        "scale": True,
        "isTable": True,
    }
    if language != "auto":
        payload["language"] = language
    if filetype:
        payload["filetype"] = filetype

    try:
        response = requests.post(OCR_SPACE_ENDPOINT, data=payload, timeout=60)
        response.raise_for_status()
    except requests.RequestException as exc:
        return {
            "success": False,
            "text": "",
            "pages_processed": 0,
            "error": f"Errore di rete verso OCR.space: {exc}",
        }

    try:
        result = response.json()
    except ValueError:
        return {
            "success": False,
            "text": "",
            "pages_processed": 0,
            "error": "Risposta non JSON ricevuta da OCR.space.",
        }

    if result.get("IsErroredOnProcessing"):
        error_message = result.get("ErrorMessage") or result.get("ErrorDetails") or "Errore sconosciuto da OCR.space."
        if isinstance(error_message, list):
            error_message = "; ".join(error_message)
        return {
            "success": False,
            "text": "",
            "pages_processed": 0,
            "error": error_message,
        }

    extracted_text = _collect_parsed_text(result)
    pages_processed = len(result.get("ParsedResults") or [])

    if not extracted_text:
        return {
            "success": False,
            "text": "",
            "pages_processed": pages_processed,
            "error": "OCR completato ma nessun testo riconosciuto nel documento.",
        }

    return {
        "success": True,
        "text": extracted_text,
        "pages_processed": pages_processed,
        "error": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="OCR MCP Server")
    parser.add_argument("--http", action="store_true", help="Esegui come server HTTP invece che stdio")
    parser.add_argument("--host", default="0.0.0.0", help="Host per la modalità HTTP")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8080)), help="Porta per la modalità HTTP")
    args = parser.parse_args()

    if not OCR_SPACE_API_KEY:
        print(
            "ATTENZIONE: variabile d'ambiente OCR_SPACE_API_KEY non impostata. "
            "Il tool perform_ocr risponderà sempre con errore finché non viene configurata.",
            file=sys.stderr,
        )

    if args.http:
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()