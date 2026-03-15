"""Routes API pour la gestion des documents."""
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.schemas.document import DocumentResponse, ProcessingStatus, UploadedDocument
from app.services.pipeline import curate_all_documents, process_document
from app.storage import datalake

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

UPLOAD_DIR = Path("./storage/bronze")
ALLOWED_MIME = {"application/pdf"}


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_documents(
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
) -> list[DocumentResponse]:
    """Upload un ou plusieurs fichiers PDF et lance leur traitement en arrière-plan."""
    if not files:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    responses: list[DocumentResponse] = []

    for file in files:
        if file.content_type not in ALLOWED_MIME:
            raise HTTPException(
                status_code=415,
                detail=(
                    f"Type de fichier non supporté : {file.content_type}."
                    " Seuls les PDF sont acceptés."
                ),
            )

        content = await file.read()
        doc_id = uuid.uuid4()
        safe_filename = f"{doc_id}_{file.filename}"

        document = UploadedDocument(
            id=doc_id,
            filename=safe_filename,
            original_filename=file.filename or "document.pdf",
            file_size=len(content),
        )

        # Sauvegarde Bronze
        bronze = datalake.save_bronze(document, content)

        # Traitement lancé en arrière-plan
        file_path = Path(bronze.file_path)
        background_tasks.add_task(_process_and_curate, document, file_path)

        responses.append(DocumentResponse(
            id=document.id,
            filename=document.filename,
            original_filename=document.original_filename,
            status=ProcessingStatus.UPLOADED,
            upload_at=document.upload_at,
        ))

    return responses


async def _process_and_curate(document: UploadedDocument, file_path: Path) -> None:
    """Tâche de fond : traitement + curation globale."""
    try:
        process_document(document, file_path)
        curate_all_documents()
    except Exception as exc:
        logger.error("Erreur pipeline pour '%s' : %s", document.original_filename, exc)


@router.get("/", response_model=list[DocumentResponse])
async def list_documents() -> list[DocumentResponse]:
    """Liste tous les documents (depuis les zones Gold et Silver)."""
    gold_records = datalake.load_all_gold()
    silver_records = datalake.load_all_silver()
    gold_ids = {str(g.document_id) for g in gold_records}

    responses: list[DocumentResponse] = []

    for gold in gold_records:
        responses.append(DocumentResponse(
            id=gold.document_id,
            filename=str(gold.document_id),
            original_filename=gold.original_filename,
            status=ProcessingStatus.CURATED,
            document_type=gold.document_type,
            upload_at=gold.curated_at,
        ))

    for silver in silver_records:
        if str(silver.document_id) not in gold_ids:
            responses.append(DocumentResponse(
                id=silver.document_id,
                filename=str(silver.document_id),
                original_filename=silver.original_filename,
                status=ProcessingStatus.EXTRACTED,
                document_type=silver.document_type,
                upload_at=silver.processed_at,
            ))

    return responses


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: uuid.UUID) -> DocumentResponse:
    """Retourne le statut et les infos d'un document spécifique."""
    gold = datalake.load_gold(document_id)
    if gold:
        return DocumentResponse(
            id=gold.document_id,
            filename=str(gold.document_id),
            original_filename=gold.original_filename,
            status=ProcessingStatus.CURATED,
            document_type=gold.document_type,
            upload_at=gold.curated_at,
        )

    silver = datalake.load_silver(document_id)
    if silver:
        return DocumentResponse(
            id=silver.document_id,
            filename=str(silver.document_id),
            original_filename=silver.original_filename,
            status=ProcessingStatus.EXTRACTED,
            document_type=silver.document_type,
            upload_at=silver.processed_at,
        )

    bronze = datalake.load_bronze(document_id)
    if bronze:
        return DocumentResponse(
            id=bronze.document.id,
            filename=bronze.document.filename,
            original_filename=bronze.document.original_filename,
            status=ProcessingStatus.UPLOADED,
            upload_at=bronze.document.upload_at,
        )

    raise HTTPException(status_code=404, detail=f"Document '{document_id}' non trouvé")


@router.get("/{document_id}/extraction")
async def get_extraction(document_id: uuid.UUID) -> JSONResponse:
    """Retourne les données extraites (zone Silver) d'un document."""
    silver = datalake.load_silver(document_id)
    if not silver:
        raise HTTPException(status_code=404, detail="Extraction non disponible pour ce document")
    return JSONResponse(content=silver.extraction.model_dump(mode="json"))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: uuid.UUID) -> None:
    """Supprime un document à tous les niveaux du Data Lake (Medallion)."""
    success = datalake.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document non trouvé ou déjà supprimé")
    
    # Après suppression, on relance la curation globale pour mettre à jour les Gold et les alertes restantes
    curate_all_documents()
