import os
import io
import json
import base64
import uuid
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from dotenv import load_dotenv
from datetime import datetime


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class GoogleSheetsClient:
    def __init__(self):
        load_dotenv()

        # Deux façons de fournir les credentials du compte de service :
        # - GOOGLE_SERVICE_ACCOUNT_JSON_B64 : contenu du JSON encodé en base64
        #   (pratique pour le déploiement, ex: Railway/Render)
        # - GOOGLE_SERVICE_ACCOUNT_JSON : chemin vers le fichier JSON local
        creds_b64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64")
        creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

        if creds_b64:
            # Décodage base64 -> chaîne JSON -> dict Python
            creds_info = json.loads(base64.b64decode(creds_b64).decode("utf-8"))
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        elif creds_path:
            creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        else:
            raise ValueError(
                "Aucun credential Google trouvé. Définis GOOGLE_SERVICE_ACCOUNT_JSON "
                "(chemin local) ou GOOGLE_SERVICE_ACCOUNT_JSON_B64 (base64, pour le déploiement)."
            )

        # Autorisation gspread avec ces credentials
        client = gspread.authorize(creds)

        # Client Google Drive (mêmes credentials, scope "drive" inclus)
        self.drive_service = build("drive", "v3", credentials=creds)

        # Ouverture du Sheet par son ID, puis sélection de l'onglet "Notes de frais"
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        spreadsheet = client.open_by_key(sheet_id)
        self.sheet = spreadsheet.worksheet("Notes de frais")

    def upload_image(self, image_bytes: bytes, media_type: str) -> str:
        """
        Upload une image sur Google Drive et la rend accessible publiquement
        en lecture. Retourne l'URL de l'image, ou None en cas d'échec.
        """
        try:
            # Détermine une extension simple à partir du type MIME
            extension = media_type.split("/")[-1] if media_type else "jpg"
            filename = f"{uuid.uuid4()}.{extension}"

            file_metadata = {"name": filename}
            media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype=media_type)

            uploaded_file = (
                self.drive_service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )
            file_id = uploaded_file.get("id")

            # Permission de lecture publique (n'importe qui avec le lien)
            self.drive_service.permissions().create(
                fileId=file_id,
                body={"role": "reader", "type": "anyone"},
            ).execute()

            return f"https://drive.google.com/uc?id={file_id}"
        except Exception as e:
            print(f"Erreur lors de l'upload sur Drive : {e}")
            return None

    def append_expense(self, data: dict, image_url: str = None) -> bool:
        """
        Ajoute une ligne dans le Google Sheet "Notes de frais".
        data : dictionnaire contenant les champs extraits par ExpenseAgent.
        image_url : URL publique de l'image (Drive), optionnelle.
        """
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        row = [
            timestamp,
            data.get("type_document") or "",
            data.get("fournisseur") or "",
            data.get("date") or "",
            data.get("montant_ttc") if data.get("montant_ttc") is not None else "",
            data.get("tva") if data.get("tva") is not None else "",
            data.get("devise") or "",
            data.get("description") or "",
            data.get("confiance") or "",
            image_url or "",
        ]

        try:
            self.sheet.append_row(row)
            return True
        except gspread.exceptions.APIError as e:
            print(f"Erreur Google Sheets API : {e}")
            return False


if __name__ == "__main__":
    # Test rapide : vérifie la connexion et l'écriture dans le Sheet
    client = GoogleSheetsClient()
    print("Connexion réussie !")
    print("Titre de la feuille :", client.sheet.title)

    fake_data = {
        "type_document": "restaurant",
        "fournisseur": "Test Bistrot",
        "date": "10/06/2026",
        "montant_ttc": 25.50,
        "tva": 4.25,
        "devise": "EUR",
        "description": "Test d'intégration",
        "confiance": "haute",
    }

    success = client.append_expense(fake_data, image_url="https://example.com/test.jpg")
    print("Ligne ajoutée avec succès !" if success else "Échec de l'ajout.")