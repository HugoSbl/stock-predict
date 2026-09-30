"""API sources simulées (D-14).

Squelette du lot 0 : les endpoints métier (/api/v1/sales, /stock-levels, /purchase-orders)
et le générateur de données arrivent au lot 1.
"""

from fastapi import FastAPI

app = FastAPI(title="StockPredict — sources simulées", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
