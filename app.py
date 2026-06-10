import base64
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend import ExpenseAgent
from sheets import GoogleSheetsClient

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

agent = ExpenseAgent()
sheets_client = GoogleSheetsClient()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_MB = 5


@app.get("/")
def read_root():
    return FileResponse("static/index.html")


@app.post("/api/analyze", response_class=HTMLResponse)
async def analyze(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non supporté : {file.content_type}. "
                   f"Formats acceptés : JPEG, PNG, WEBP.",
        )

    image_bytes = await file.read()
    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > MAX_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux ({size_mb:.1f} Mo). Maximum : {MAX_SIZE_MB} Mo.",
        )

    data = agent.extract_from_bytes(image_bytes, file.content_type)
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    html = f"""
    <form hx-post="/api/submit" hx-target="#confirmation-container" hx-swap="innerHTML">

        <label for="type_document">Type de document</label>
        <select name="type_document" id="type_document">
            <option value="restaurant" {"selected" if data.get("type_document") == "restaurant" else ""}>Restaurant</option>
            <option value="transport" {"selected" if data.get("type_document") == "transport" else ""}>Transport</option>
            <option value="hôtel" {"selected" if data.get("type_document") == "hôtel" else ""}>Hôtel</option>
            <option value="autre" {"selected" if data.get("type_document") == "autre" else ""}>Autre</option>
        </select>

        <label for="fournisseur">Fournisseur</label>
        <input type="text" name="fournisseur" id="fournisseur" value="{data.get('fournisseur') or ''}">

        <label for="date">Date</label>
        <input type="text" name="date" id="date" value="{data.get('date') or ''}" placeholder="JJ/MM/AAAA">

        <label for="montant_ttc">Montant TTC (€)</label>
        <input type="number" step="0.01" name="montant_ttc" id="montant_ttc" value="{data.get('montant_ttc') if data.get('montant_ttc') is not None else ''}">

        <label for="tva">TVA (€)</label>
        <input type="number" step="0.01" name="tva" id="tva" value="{data.get('tva') if data.get('tva') is not None else ''}">

        <label for="devise">Devise</label>
        <input type="text" name="devise" id="devise" value="{data.get('devise') or 'EUR'}">

        <label for="description">Description</label>
        <input type="text" name="description" id="description" value="{data.get('description') or ''}">

        <label for="confiance">Confiance</label>
        <select name="confiance" id="confiance">
            <option value="haute" {"selected" if data.get("confiance") == "haute" else ""}>Haute</option>
            <option value="moyen" {"selected" if data.get("confiance") == "moyen" else ""}>Moyen</option>
            <option value="basse" {"selected" if data.get("confiance") == "basse" else ""}>Basse</option>
        </select>

        <input type="hidden" name="image_data" value="{b64_image}">
        <input type="hidden" name="media_type" value="{file.content_type}">

        <button type="submit">Envoyer vers le Google Sheet</button>
    </form>
    """

    return HTMLResponse(content=html)


@app.post("/api/submit", response_class=HTMLResponse)
async def submit(
    type_document: str = Form(""),
    fournisseur: str = Form(""),
    date: str = Form(""),
    montant_ttc: str = Form(""),
    tva: str = Form(""),
    devise: str = Form("EUR"),
    description: str = Form(""),
    confiance: str = Form(""),
    image_data: str = Form(""),
    media_type: str = Form(""),
):
    def to_float(value: str):
        try:
            return float(value) if value.strip() != "" else None
        except ValueError:
            return None

    data = {
        "type_document": type_document or None,
        "fournisseur": fournisseur or None,
        "date": date or None,
        "montant_ttc": to_float(montant_ttc),
        "tva": to_float(tva),
        "devise": devise or "EUR",
        "description": description or None,
        "confiance": confiance or None,
    }

    image_url = None

    success = sheets_client.append_expense(data, image_url)

    if success:
        html = """
        <div class="success-message">
            Note de frais enregistrée avec succès dans le Google Sheet !
        </div>
        """
    else:
        html = """
        <div class="error-message">
            Une erreur est survenue lors de l'enregistrement. Veuillez réessayer.
        </div>
        """

    return HTMLResponse(content=html)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    html = f"""
    <div class="error-message">
         {exc.detail}
    </div>
    """
    return HTMLResponse(content=html, status_code=exc.status_code)