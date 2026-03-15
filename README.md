# DocFlow — Traitement Automatique de Documents Administratifs

Plateforme intelligente permettant d'automatiser la classification, l'extraction de données et la détection d'alertes sur des documents comptables (factures, devis, attestations).

## Architecture

- **Backend** : FastAPI + Python 3.12 (gestion automatisée par `uv`)
- **Frontend** : React 18 + Vite + TypeScript (gestion par `fnm`)
- **OCR** : Tesseract 5
- **LLM** : Multi-provider (Ollama pour le local, Groq pour la performance)
- **Data Lake** : Architecture Medallion (Bronze, Silver, Gold)

## Pré-requis

- [uv](https://github.com/astral-sh/uv) installé
- [fnm](https://github.com/Schniz/fnm) installé
- [Tesseract OCR](https://tesseract-ocr.github.io/tessdoc/Installation.html) installé (`brew install tesseract`)
- [Ollama](https://ollama.com/) (pour le mode local)

## Installation et Lancement

### 1. Backend

```bash
cd backend
uv sync
# Copier et configurer le .env
cp .env.example .env 
# Lancer le serveur
uv run uvicorn app.main:app --reload
```

### 2. Frontend

```bash
cd frontend
fnm use 20
npm install
npm run dev
```

## Fonctionnalités

- **Upload multi-PDF** : Glisser-déposer des documents.
- **Pipeline Automatisé** :
    - **Bronze** : Stockage du fichier brut.
    - **Silver** : OCR + Extraction des données structurées (SIREN, Montants, Dates).
    - **Gold** : Détection d'incohérences (SIRET mismatch, écarts de montants, dates incohérentes).
- **Dashboard Conformité** : Vue d'ensemble de la santé des documents.
- **CRM Fournisseurs** : Consolidation par SIREN.

## Tests

```bash
cd backend
uv run pytest
```
