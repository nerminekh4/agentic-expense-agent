# Agentic Expense Agent — Application de gestion des notes de frais

## Contexte et objectif

Application web agentique permettant à un salarié de prendre en photo une note de
frais (ticket de restaurant, billet de train, facture d'hôtel, etc.) depuis son
téléphone. L'application :

1. Analyse l'image avec un modèle de vision (Llama 4 Scout via l'API Groq) et en
   extrait automatiquement les informations utiles (fournisseur, date, montant,
   TVA, devise, description, type de dépense, niveau de confiance).
2. Affiche ces informations dans un formulaire éditable, permettant à
   l'utilisateur de corriger les valeurs avant envoi.
3. Synchronise la dépense dans un Google Sheet partagé avec le service
   comptabilité.
4. Tente d'archiver l'image du justificatif sur Google Drive et d'en insérer le
   lien dans le Sheet (voir limitation connue ci-dessous).

## Stack technique

| Composant     | Technologie |
|---------------|-------------|
| Modèle IA     | `meta-llama/llama-4-scout-17b-16e-instruct` via SDK Groq |
| Backend       | Python · FastAPI |
| Frontend      | HTML · HTMX · CSS · JS Vanilla |
| Intégration   | Google Sheets API (via `gspread`) + Google Drive API |

## Structure du projet

```
agentic-expense-agent/
├── backend.py        # Classe ExpenseAgent — extraction IA depuis une image
├── app.py            # Serveur FastAPI — routes et orchestration
├── sheets.py         # Classe GoogleSheetsClient — intégration Sheets + Drive
├── context.txt       # Prompt système du modèle (rôle de l'agent)
├── prompt.txt        # Prompt utilisateur (structure JSON attendue)
├── requirements.txt
├── .env.example
├── .env              # Non commité — credentials et configuration locale
└── static/
    ├── index.html    # Interface HTMX
    ├── style.css     # Feuille de style (dark mode, violet/bleu)
    └── app.js        # JS Vanilla (preview image, events HTMX)
```

## Installation

### 1. Cloner le dépôt et créer l'environnement virtuel

```bash
git clone <url-du-repo>
cd agentic-expense-agent
python3 -m venv venv
source venv/bin/activate   # sous Windows : venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurer les variables d'environnement

Copie `.env.example` vers `.env` et remplis les valeurs :

```
GROQ_API_KEY=""
GOOGLE_SHEET_ID=""
GOOGLE_SERVICE_ACCOUNT_JSON=""
```

- `GROQ_API_KEY` : clé API obtenue sur https://console.groq.com/keys
- `GOOGLE_SHEET_ID` : identifiant du Google Sheet (voir section ci-dessous)
- `GOOGLE_SERVICE_ACCOUNT_JSON` : chemin local vers le fichier JSON du compte de
  service Google (jamais commité — voir `.gitignore`)

### 3. Lancer le serveur

```bash
uvicorn app:app --reload
```

Puis ouvrir http://127.0.0.1:8000

## Configuration Google Cloud

1. Créer un projet sur https://console.cloud.google.com
2. Activer les API **Google Sheets API** et **Google Drive API**
   (APIs & Services > Library)
3. Créer un **compte de service** (APIs & Services > Credentials > Create
   Credentials > Service account), rôle **Editor**
4. Télécharger la clé JSON du compte de service et la placer dans le projet
   (sans la commiter — elle est ignorée via `*.json` dans `.gitignore`)
5. Créer un Google Sheet, renommer la première feuille en `Notes de frais`, et
   créer la ligne d'en-têtes suivante :

   ```
   Horodatage | Type | Fournisseur | Date | Montant TTC (€) | TVA (€) | Devise | Description | Confiance | Image
   ```

6. Partager ce Sheet avec l'adresse email du compte de service (visible dans le
   fichier JSON, champ `client_email`), avec le rôle **Éditeur**
7. Copier l'ID du Sheet depuis l'URL (la chaîne entre `/d/` et `/edit`) dans
   `GOOGLE_SHEET_ID`

## Exemple de JSON retourné par le modèle

```json
{
  "type_document": "restaurant",
  "fournisseur": "Bistrot Paul",
  "date": "12/03/2025",
  "montant_ttc": 42.50,
  "tva": 7.08,
  "devise": "EUR",
  "description": "Déjeuner d'affaires",
  "confiance": "haute"
}
```

## Limitation connue — stockage des images sur Google Drive

L'application tente d'uploader chaque image de justificatif sur Google Drive via
le compte de service, puis d'insérer l'URL obtenue dans la colonne `Image` du
Sheet.

**Sur un compte Google personnel (Gmail gratuit, hors Google Workspace)**, les
comptes de service n'ont **aucun quota de stockage propre** sur Drive depuis
2021. L'upload échoue alors avec une erreur `403 storageQuotaExceeded`.

Le code gère ce cas de façon défensive : l'erreur est interceptée, journalisée
côté serveur, et la ligne est tout de même ajoutée au Sheet avec une colonne
`Image` vide — sans faire planter l'application.

### Solutions possibles en production

- **Google Workspace + Shared Drive** : si l'organisation dispose d'un Shared
  Drive, le compte de service peut y uploader des fichiers normalement (il
  suffit de cibler ce Drive comme parent du fichier).
- **Délégation OAuth utilisateur** : utiliser des credentials OAuth liés à un
  compte utilisateur réel (qui dispose d'un quota de stockage) pour les appels
  à l'API Drive, via un flow d'autorisation effectué une fois (`token.json`
  mis en cache).
- **Stockage alternatif** : héberger les images sur un autre service de
  stockage (S3, Cloudinary, etc.) et insérer l'URL publique correspondante dans
  le Sheet.
