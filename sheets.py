import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from datetime import datetime


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class GoogleSheetsClient:
    def __init__(self):
        load_dotenv()

        # Chemin vers le fichier JSON du compte de service (résolu via .env)
        creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

        # Construction des credentials à partir du fichier JSON et des scopes
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)

        # Autorisation gspread avec ces credentials
        client = gspread.authorize(creds)

        # Ouverture du Sheet par son ID, puis sélection de l'onglet "Notes de frais"
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        spreadsheet = client.open_by_key(sheet_id)
        self.sheet = spreadsheet.worksheet("Notes de frais")

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