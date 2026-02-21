# [Purpose] FastAPI application entry point for KSERC ARA Backend
# [Source] Main application orchestrator combining all services
# [Why] Central location for API endpoint definitions and application setup

# [Library] FastAPI - Modern, high-performance web framework
# [Source] https://fastapi.tiangolo.com/
# [Why] Chosen for speed, automatic API documentation, and async support
from fastapi import FastAPI, UploadFile, File, HTTPException, status

# [Library] FastAPI Response classes for HTTP responses
# [Why] Provides type-safe response models
from fastapi.responses import JSONResponse, FileResponse

# [Library] FastAPI middleware for CORS (Cross-Origin Resource Sharing)
# [Source] https://fastapi.tiangolo.com/tutorial/cors/
# [Why] Allows frontend (dashboard) to call backend from different origin
from fastapi.middleware.cors import CORSMiddleware

# [Library] Uvicorn - ASGI server for FastAPI
# [Source] https://www.uvicorn.org/
# [Why] Production-ready server for running async Python web apps
import uvicorn

# [Library] typing - Type hints for better code quality
# [Why] Enables IDE support and type checking
from typing import Dict, Any

# [User Defined] Import configuration settings
# [Source] src/config.py
# [Why] Centralized configuration management
from src.config import settings

# [User Defined] Import Pydantic models for request/response validation
# [Source] src/models/schemas.py
# [Why] Ensures type safety for API inputs and outputs
from src.models.schemas import (
    TruingUpResponse,
    ErrorResponse,
    HealthCheckResponse,
    SummaryRequest,
    SummaryResponse,
    RagIndexResponse,
    VerdictResponse
)

# [User Defined] Import PDF processing service
# [Source] src/services/pdf_ingestion.py
# [Why] Core functionality for processing regulatory orders
from src.services.pdf_ingestion import process_regulatory_order

# [User Defined] Import analysis service
# [Source] src/services/analyzer.py
# [Why] Provides compliance checking and gap analysis
from src.services.analyzer import (
    perform_compliance_checks,
    generate_analysis_summary
)

# [User Defined] Import LLM summary service
# [Source] src/services/llm_summary.py
# [Why] Provides optional AI executive summary using free-tier API
from src.services.llm_summary import generate_summary

# [User Defined] RAG and Verdict services
# [Source] src/services/rag.py, src/services/llm_orchestrator.py, src/services/verdict.py
from src.services.rag import build_chunks_from_dir, save_index, load_index, RagIndex
from src.services.rag_remote import (
    remote_index_seed,
    remote_upload_files,
    fetch_remote_index
)
from src.services.llm_orchestrator import run_four_agent_pipeline
from src.services.verdict import build_verdict_pdf, upload_verdict_to_gcs

# [Library] pathlib - Path handling
# [Why] Manage data directories safely
from pathlib import Path

# [Library] json - Parse LLM output
# [Why] Parse structured verdict if JSON-like
import json

# [Library] re - Clean LLM output
# [Why] Strip code fences
import re

# [User Defined] Import logger
# [Source] src/utils/logger.py
# [Why] Application-wide logging
from src.utils.logger import get_logger

# [User Defined] Create logger instance for this module
logger = get_logger(__name__)

# [Comment] Global RAG index cache
rag_index: RagIndex | None = None


def _load_rag_index_if_exists() -> None:
    """
    [Purpose] Load RAG index from disk if available
    [Why] Reuse across requests
    """
    global rag_index
    index_path = Path(settings.RAG_INDEX_FILE)
    if index_path.exists():
        rag_index = load_index(index_path)
        logger.info("Loaded RAG index from disk")
    elif settings.RAG_REMOTE_BASE_URL:
        logger.info("Local index missing; remote RAG base set. Use /rag/refresh to load.")


async def _refresh_rag_index_from_remote() -> None:
    """
    [Purpose] Refresh RAG index from remote service
    [Why] Keeps local cache in sync with Cloudflare index
    """
    global rag_index
    remote_payload = await fetch_remote_index()
    chunks = remote_payload.get("chunks", [])
    rag_index = RagIndex(chunks)
    save_index(chunks, Path(settings.RAG_INDEX_FILE))
    logger.info("Loaded RAG index from remote service")

# [Library] FastAPI() - Initialize FastAPI application instance
# [Why] This 'app' object is the core of the web server
# [Parameters] Configure application metadata for auto-generated documentation
app = FastAPI(
    title=settings.APP_NAME,  # [Comment] Application name from config
    description=settings.APP_DESCRIPTION,  # [Comment] Description for API docs
    version=settings.APP_VERSION,  # [Comment] Version for tracking
    docs_url="/docs" if settings.DEBUG_MODE else None,  # [Comment] Swagger UI endpoint
    redoc_url="/redoc" if settings.DEBUG_MODE else None  # [Comment] ReDoc endpoint
)

# [Library] Add CORS middleware to allow cross-origin requests
# [Source] FastAPI CORS middleware
# [Why] Enables frontend applications to call this API from different domains
# [Security Note] In production, restrict origins to specific domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # [Comment] Allow all origins (restrict in production)
    allow_credentials=True,  # [Comment] Allow cookies
    allow_methods=["*"],  # [Comment] Allow all HTTP methods
    allow_headers=["*"],  # [Comment] Allow all headers
)


# [Library] @app.on_event("startup") - FastAPI lifecycle event
# [Source] FastAPI events documentation
# [Why] Code to run when application starts up
@app.on_event("startup")
async def startup_event():
    """
    [Purpose] Initialization code executed when application starts
    [Source] FastAPI lifecycle events
    [Why] Setup tasks like database connections, logging configuration
    """
    logger.info("=" * 60)
    _load_rag_index_if_exists()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Server: {settings.HOST}:{settings.PORT}")
    logger.info(f"Debug Mode: {settings.DEBUG_MODE}")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")
    logger.info("=" * 60)


# [Library] @app.on_event("shutdown") - FastAPI lifecycle event
# [Source] FastAPI events documentation
# [Why] Cleanup code when application shuts down
@app.on_event("shutdown")
async def shutdown_event():
    """
    [Purpose] Cleanup code executed when application shuts down
    [Source] FastAPI lifecycle events
    [Why] Graceful cleanup of resources (database connections, file handles)
    """
    logger.info("Shutting down KSERC ARA Backend")


# [User Defined] Root endpoint for health checks
# [Source] Standard REST API convention
# [Why] Allows monitoring systems and load balancers to check if service is alive
@app.get(
    "/",
    response_model=HealthCheckResponse,
    tags=["Health"],
    summary="Health Check",
    description="Check if the API service is running and healthy"
)
async def health_check():
    """
    [Purpose] Returns basic health status of the API
    [Source] Standard practice for microservices
    [Why] Load balancers and monitoring tools use this to check service health
    
    [Returns]
    - HealthCheckResponse: Status, system name, timestamp, version
    
    [HTTP Status]
    - 200 OK: Service is healthy
    """
    logger.debug("Health check requested")
    
    # [Comment] Return health status with current timestamp
    return HealthCheckResponse(
        status="active",
        system=f"ARA Backend v{settings.APP_VERSION}",
        version=settings.APP_VERSION
    )


# [User Defined] Endpoint to get API information
# [Source] Standard API metadata endpoint
# [Why] Provides information about the API capabilities
@app.get(
    "/info",
    tags=["Health"],
    summary="API Information",
    description="Get detailed information about the API"
)
async def api_info() -> Dict[str, Any]:
    """
    [Purpose] Returns API metadata and configuration
    [Source] User defined endpoint
    [Why] Helps API consumers understand capabilities
    
    [Returns]
    - Dict: API information including version, endpoints, configuration
    """
    logger.debug("API info requested")
    
    return {
        "api_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": settings.APP_DESCRIPTION,
        "regulatory_authority": settings.REGULATORY_AUTHORITY,
        "endpoints": {
            "health": "/",
            "info": "/info",
            "analyze_order": "/analyze-order/",
            "compliance_check": "/compliance-check/",
            "ai_summary": "/ai-summary/",
            "rag_index": "/rag/index-seed",
            "rag_upload": "/rag/upload",
            "verdict": "/verdict/"
        },
        "documentation": {
            "swagger_ui": "/docs" if settings.DEBUG_MODE else "Disabled in production",
            "redoc": "/redoc" if settings.DEBUG_MODE else "Disabled in production"
        },
        "capabilities": [
            "PDF ingestion and parsing",
            "Financial table extraction",
            "Truing Up analysis",
            "Compliance checks",
            "Deviation analysis"
        ]
    }


# [User Defined] Main endpoint to upload and analyze regulatory orders
# [Source] Core API functionality based on 'ARA_Autonomous_Regulatory_Compliance.pdf' workflow
# [Why] Primary use case - upload PDF and get analysis results
@app.post(
    "/analyze-order/",
    response_model=TruingUpResponse,
    tags=["Analysis"],
    summary="Analyze Regulatory Order",
    description="Upload a KSERC regulatory order PDF and get truing up analysis",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request - Invalid file format"},
        500: {"model": ErrorResponse, "description": "Internal Server Error - Processing failed"}
    }
)
async def analyze_order(file: UploadFile = File(...)):
    """
    [Purpose] Analyzes uploaded KSERC regulatory order PDF
    [Source] User defined endpoint integrating PDF ingestion service
    [Why] Main API function for regulatory order analysis
    
    [Parameters]
    - file: UploadFile - PDF file of regulatory order
    
    [Returns]
    - TruingUpResponse: Complete analysis with financial data and deviations
    
    [HTTP Status Codes]
    - 200: Success - Analysis completed
    - 400: Bad Request - File is not a PDF
    - 500: Server Error - Processing failed
    
    [Process Flow]
    1. Validate file is PDF
    2. Check file size
    3. Read file bytes
    4. Process PDF (extract tables, metadata)
    5. Return structured response
    """
    logger.info(f"Received file upload: {file.filename}")
    
    # [Comment] Step 1: Validate file extension
    # [Library] str.endswith() - Check if string ends with suffix
    # [Why] Only PDF files should be processed
    if not file.filename.endswith(".pdf"):
        logger.warning(f"Invalid file format: {file.filename}")
        
        # [Library] HTTPException - FastAPI exception for HTTP errors
        # [Why] Returns proper HTTP error response to client
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF. Please upload a PDF file."
        )
    
    # [Comment] Step 2: Read file content
    # [Why] Need file bytes for processing
    try:
        # [Library] await file.read() - Async read of uploaded file
        # [Why] FastAPI UploadFile is async for performance
        logger.debug("Reading file content")
        file_content = await file.read()
        
        # [Comment] Step 3: Check file size
        # [Why] Prevent server overload from extremely large files
        file_size_mb = len(file_content) / (1024 * 1024)
        logger.info(f"File size: {file_size_mb:.2f} MB")
        
        if len(file_content) > settings.MAX_UPLOAD_SIZE:
            logger.warning(f"File too large: {file_size_mb:.2f} MB")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE / (1024*1024)} MB"
            )
        
        # [Comment] Step 4: Process the regulatory order PDF
        # [User Defined] Call PDF ingestion service
        # [Source] src/services/pdf_ingestion.py
        # [Why] Separates business logic from API layer
        logger.info("Processing regulatory order")
        result = process_regulatory_order(file_content)
        
        logger.info(f"Analysis complete for {result.licensee_name} - {result.financial_year}")
        return result
        
    except HTTPException:
        # [Comment] Re-raise HTTP exceptions (already formatted)
        raise
    
    except Exception as e:
        # [Comment] Catch all other exceptions and return 500 error
        # [Why] Prevents server crash and provides error details to client
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF: {str(e)}"
        )


# [User Defined] Endpoint to perform compliance checks on analysis results
# [Source] Regulatory compliance verification workflow
# [Why] Separate endpoint for detailed compliance analysis
@app.post(
    "/compliance-check/",
    tags=["Analysis"],
    summary="Perform Compliance Check",
    description="Upload a regulatory order and get detailed compliance analysis",
    status_code=status.HTTP_200_OK
)
async def compliance_check(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    [Purpose] Performs comprehensive compliance checks on regulatory order
    [Source] User defined endpoint integrating analyzer service
    [Why] Provides detailed compliance report beyond basic analysis
    
    [Parameters]
    - file: UploadFile - PDF file of regulatory order
    
    [Returns]
    - Dict: Detailed compliance report with checks, warnings, and summary
    
    [Process Flow]
    1. Process PDF to get truing up analysis
    2. Perform compliance checks on results
    3. Generate analysis summary
    4. Return comprehensive report
    """
    logger.info(f"Compliance check requested for: {file.filename}")
    
    # [Comment] Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    try:
        # [Comment] Step 1: Process the PDF
        file_content = await file.read()
        logger.debug("Processing PDF for compliance check")
        analysis_result = process_regulatory_order(file_content)
        
        # [Comment] Step 2: Perform compliance checks
        # [User Defined] Call analyzer service
        # [Source] src/services/analyzer.py
        # [Why] Specialized service for regulatory compliance
        logger.info("Performing compliance checks")
        compliance_report = perform_compliance_checks(analysis_result)
        
        # [Comment] Step 3: Generate analysis summary
        logger.debug("Generating analysis summary")
        summary = generate_analysis_summary(analysis_result, compliance_report)
        
        # [Comment] Step 4: Combine results into comprehensive report
        comprehensive_report = {
            "basic_analysis": analysis_result.model_dump(),  # [Library] Pydantic model_dump()
            "compliance_report": compliance_report,
            "executive_summary": summary
        }
        
        logger.info("Compliance check completed successfully")
        return comprehensive_report
        
    except Exception as e:
        logger.error(f"Error during compliance check: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compliance check failed: {str(e)}"
        )


# [User Defined] Endpoint to generate AI summary for analysis results
# [Source] Free-tier Hugging Face Inference API integration
# [Why] Provides executive summary without paid APIs
@app.post(
    "/ai-summary/",
    response_model=SummaryResponse,
    tags=["Analysis"],
    summary="Generate AI Summary",
    description="Generate an executive summary using a free-tier LLM API",
    status_code=status.HTTP_200_OK
)
async def ai_summary(payload: SummaryRequest) -> SummaryResponse:
    """
    [Purpose] Generates AI summary for analysis results
    [Why] Delivers readable executive summary for dashboard use
    """
    try:
        logger.info("AI summary requested")
        result = generate_summary(
            analysis=payload.analysis.model_dump(),
            compliance_report=payload.compliance_report
        )
        return SummaryResponse(**result)
    except Exception as e:
        logger.error(f"Error generating AI summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI summary failed: {str(e)}"
        )


# [User Defined] Endpoint to index RAG documents from seed directory
# [Why] Builds local retrieval index for regulations
@app.post(
    "/rag/index-seed",
    response_model=RagIndexResponse,
    tags=["RAG"],
    summary="Index RAG Seed Documents",
    description="Index documents from configured RAG_SEED_DIR"
)
async def rag_index_seed() -> RagIndexResponse:
    global rag_index
    if settings.RAG_REMOTE_BASE_URL:
        remote_result = await remote_index_seed()
        await _refresh_rag_index_from_remote()
        return RagIndexResponse(
            status=remote_result.get("status", "indexed"),
            indexed_chunks=remote_result.get("indexed_chunks", 0),
            sources=remote_result.get("sources", [])
        )

    seed_dir = Path(settings.RAG_SEED_DIR)
    if not seed_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"RAG_SEED_DIR not found: {seed_dir}"
        )
    chunks = build_chunks_from_dir(seed_dir)
    save_index(chunks, Path(settings.RAG_INDEX_FILE))
    rag_index = RagIndex(chunks)
    sources = sorted({c["source"] for c in chunks})
    return RagIndexResponse(
        status="indexed",
        indexed_chunks=len(chunks),
        sources=sources
    )


# [User Defined] Endpoint to upload RAG files and re-index
# [Why] Allows backend-side doc updates
@app.post(
    "/rag/upload",
    response_model=RagIndexResponse,
    tags=["RAG"],
    summary="Upload RAG Documents",
    description="Upload new RAG files and rebuild index"
)
async def rag_upload(files: list[UploadFile] = File(...)) -> RagIndexResponse:
    global rag_index
    if settings.RAG_REMOTE_BASE_URL:
        upload_files = []
        for f in files:
            if not f.filename:
                continue
            content = await f.read()
            upload_files.append(
                ("files", (f.filename, content, f.content_type or "application/octet-stream"))
            )
        if not upload_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files uploaded"
            )
        remote_result = await remote_upload_files(upload_files)
        await _refresh_rag_index_from_remote()
        return RagIndexResponse(
            status=remote_result.get("status", "uploaded_and_indexed"),
            indexed_chunks=remote_result.get("indexed_chunks", 0),
            sources=remote_result.get("sources", [])
        )

    storage_dir = Path(settings.RAG_STORAGE_DIR)
    storage_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    for f in files:
        if not f.filename:
            continue
        target = storage_dir / f.filename
        content = await f.read()
        target.write_bytes(content)
        saved_files.append(target)

    if not saved_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files uploaded"
        )

    chunks = build_chunks_from_dir(storage_dir)
    save_index(chunks, Path(settings.RAG_INDEX_FILE))
    rag_index = RagIndex(chunks)
    sources = sorted({c["source"] for c in chunks})
    return RagIndexResponse(
        status="uploaded_and_indexed",
        indexed_chunks=len(chunks),
        sources=sources
    )


@app.post(
    "/rag/refresh",
    response_model=RagIndexResponse,
    tags=["RAG"],
    summary="Refresh RAG Index",
    description="Pull the latest index from the remote RAG service"
)
async def rag_refresh() -> RagIndexResponse:
    if not settings.RAG_REMOTE_BASE_URL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RAG_REMOTE_BASE_URL not configured"
        )
    await _refresh_rag_index_from_remote()
    sources = sorted({c["source"] for c in (rag_index.chunks if rag_index else [])})
    return RagIndexResponse(
        status="refreshed",
        indexed_chunks=len(rag_index.chunks) if rag_index else 0,
        sources=sources
    )


def _parse_verdict_json(raw_text: str) -> Dict[str, Any]:
    """
    [Purpose] Parse JSON-like verdict from LLM output
    [Why] Normalize output for API and PDF
    """
    cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return {
            "approved_items": [],
            "disallowed_items": [],
            "conditions": [],
            "final_summary": cleaned
        }


# [User Defined] Main verdict endpoint
# [Why] Upload ARR + Truing-up PDFs, run RAG + 4 LLMs, generate verdict PDF
@app.post(
    "/verdict/",
    response_model=VerdictResponse,
    tags=["Analysis"],
    summary="Generate KSERC Verdict",
    description="Upload ARR and Truing-Up PDFs to generate final verdict PDF",
    status_code=status.HTTP_200_OK
)
async def generate_verdict(
    arr_pdf: UploadFile = File(...),
    truing_pdf: UploadFile = File(...)
) -> VerdictResponse:
    global rag_index
    if rag_index is None and settings.RAG_REMOTE_BASE_URL:
        await _refresh_rag_index_from_remote()
    if rag_index is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RAG index not loaded. Call /rag/index-seed or /rag/upload first."
        )

    if not arr_pdf.filename.endswith(".pdf") or not truing_pdf.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both files must be PDFs"
        )

    try:
        arr_content = await arr_pdf.read()
        truing_content = await truing_pdf.read()

        arr_result = process_regulatory_order(arr_content)
        truing_result = process_regulatory_order(truing_content)
        compliance_report = perform_compliance_checks(truing_result)

        # Build RAG query
        query = (
            f"{truing_result.licensee_name} {truing_result.financial_year} "
            f"truing up ARR compliance regulation 73 tariff 2021 "
            f"deviation {truing_result.net_surplus_deficit}"
        )
        rag_snippets = rag_index.search(query, top_k=6)

        # Run 4-agent pipeline
        agent_outputs = run_four_agent_pipeline(
            arr_analysis=arr_result.model_dump(),
            truing_analysis=truing_result.model_dump(),
            compliance_report=compliance_report,
            rag_snippets=rag_snippets
        )

        verdict_parsed = _parse_verdict_json(agent_outputs.get("chief_regulatory_officer", ""))
        summary = verdict_parsed.get("final_summary") or "Verdict generated."
        approved_items = verdict_parsed.get("approved_items", []) or []
        disallowed_items = verdict_parsed.get("disallowed_items", []) or []
        conditions = verdict_parsed.get("conditions", []) or []

        # Build PDF
        verdict_payload = {
            "summary": summary,
            "approved_items": approved_items,
            "disallowed_items": disallowed_items,
            "conditions": conditions
        }
        verdict_path = build_verdict_pdf(Path(settings.VERDICT_DIR), verdict_payload)
        verdict_id = verdict_path.stem

        verdict_pdf_url = f"/verdict/{verdict_id}.pdf"
        if settings.GCS_BUCKET_NAME:
            verdict_pdf_url = upload_verdict_to_gcs(verdict_path)

        return VerdictResponse(
            verdict_id=verdict_id,
            verdict_pdf_url=verdict_pdf_url,
            summary=summary,
            approved_items=approved_items,
            disallowed_items=disallowed_items,
            conditions=conditions,
            agent_outputs=agent_outputs,
            rag_snippets=rag_snippets
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verdict generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verdict generation failed: {str(e)}"
        )


# [User Defined] Serve verdict PDF
@app.get(
    "/verdict/{verdict_id}.pdf",
    tags=["Analysis"],
    summary="Download Verdict PDF"
)
async def download_verdict(verdict_id: str):
    file_path = Path(settings.VERDICT_DIR) / f"{verdict_id}.pdf"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Verdict PDF not found")
    return FileResponse(path=str(file_path), media_type="application/pdf", filename=f"{verdict_id}.pdf")


# [Library] Exception handler for unhandled exceptions
# [Source] FastAPI exception handlers
# [Why] Provides consistent error response format
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    [Purpose] Global exception handler for uncaught exceptions
    [Source] FastAPI exception handling
    [Why] Prevents server crash and provides consistent error responses
    
    [Parameters]
    - request: Request object
    - exc: Exception that was raised
    
    [Returns]
    - JSONResponse: Error response with details
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    # [Library] JSONResponse - FastAPI response class
    # [Why] Returns JSON-formatted error
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "details": str(exc) if settings.DEBUG_MODE else "Contact administrator"
        }
    )


# [Library] Standard Python idiom for script execution
# [Why] Code only runs when file is executed directly, not when imported
if __name__ == "__main__":
    # [Library] uvicorn.run() - Start the ASGI server
    # [Source] Uvicorn documentation
    # [Why] Runs the FastAPI application
    # [Parameters]
    # - app: FastAPI application instance (can be string path)
    # - host: Network interface to bind to (0.0.0.0 = all interfaces)
    # - port: Port number to listen on
    # - reload: Auto-reload on code changes (development only)
    # - log_level: Logging verbosity
    
    logger.info("Starting server via uvicorn")
    
    uvicorn.run(
        "src.main:app",  # [Comment] String path to app object
        host=settings.HOST,  # [Comment] From config
        port=settings.PORT,  # [Comment] From config
        reload=settings.DEBUG_MODE,  # [Comment] Auto-reload in debug mode
        log_level=settings.LOG_LEVEL.lower()  # [Comment] Uvicorn log level
    )
