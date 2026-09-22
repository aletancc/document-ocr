# OCR MCP Server

Server MCP che espone un tool `perform_ocr` per estrarre testo da documenti
scansionati (PDF, JPG, PNG, TIFF, BMP, WEBP) tramite l'API di [OCR.space](https://ocr.space/ocrapi).


## 1. Setup locale

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export OCR_SPACE_API_KEY="la-tua-api-key"
python server.py          # modalità stdio, per test con client MCP locali
# oppure
python server.py --http --port 8080   # modalità HTTP
```


## 2. Deploy su Google Cloud Run


```bash
gcloud run deploy ocr-mcp-server \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars OCR_SPACE_API_KEY=la-tua-api-key \
  --port 8080
```


## 3. Note su lingua e qualità

- `language="auto"` usa OCR Engine 2 di OCR.space, che riconosce automaticamente
  più lingue tra cui l'italiano — buona scelta di default per documenti
  Camere di Commercio.
- Per documenti misti italiano/inglese o con terminologia molto specifica,
  valuta di testare anche `language="ita"` esplicito e confrontare la qualità.
- Il piano gratuito di OCR.space ha un limite di 1 MB per file: per PDF
  scansionati multi-pagina di InfoCamere verifica se serve un piano superiore.
