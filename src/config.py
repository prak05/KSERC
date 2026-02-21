# [Purpose] Configuration management for the KSERC ARA Backend
# [Source] Best practices for Python application configuration
# [Why] Centralized configuration makes the application more maintainable and secure

# [Library] os - Operating system interface for environment variables
# [Why] Used to read environment variables for configuration
import os

# [Library] dotenv - Load environment variables from .env file
# [Source] https://github.com/theskumar/python-dotenv
# [Why] Allows developers to use .env files for local development without hardcoding secrets
from dotenv import load_dotenv

# [Library Function] load_dotenv() - Loads variables from .env file into environment
# [Why] Automatically loads configuration from .env file if it exists
load_dotenv()

# [User Defined] Configuration class using class attributes
# [Source] Common Python pattern for configuration management
# [Why] Provides a single source of truth for all application settings
class Settings:
    # [Comment] Application metadata
    APP_NAME: str = "KSERC Autonomous Regulatory Agent (ARA)"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Backend for automating Truing Up of Accounts scrutiny"
    
    # [Comment] Server configuration
    # [Library] os.getenv() - Retrieves environment variable value
    # [Why] Uses environment variable if set, otherwise uses default value
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # [Comment] API configuration
    # [Why] Allows enabling/disabling automatic API documentation in production
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "True").lower() == "true"
    
    # [Comment] File upload limits
    # [Why] Prevents server overload from extremely large PDF files
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB in bytes
    
    # [Comment] Logging configuration
    # [Why] Determines the verbosity of application logs
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # [Comment] KSERC-specific configuration
    # [Why] Default values for KSERC regulatory analysis
    DEFAULT_FINANCIAL_YEAR: str = "2023-24"
    REGULATORY_AUTHORITY: str = "Kerala State Electricity Regulatory Commission (KSERC)"
    
    # [Comment] PDF Processing configuration
    # [Why] Settings specific to PDF extraction
    PDF_DPI: int = 300  # [Comment] Resolution for image extraction from PDFs
    TABLE_DETECTION_TOLERANCE: int = 3  # [Comment] Pixel tolerance for table detection

    # [Comment] Free LLM API configuration (Hugging Face Inference API)
    # [Why] Optional AI summary generation using a free-tier API
    HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")
    HF_API_MODEL: str = os.getenv("HF_API_MODEL", "deepseek-ai/DeepSeek-R1:fastest")
    HF_API_URL: str = os.getenv(
        "HF_API_URL",
        "https://router.huggingface.co/v1/chat/completions"
    )
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

    # [Comment] RAG configuration
    # [Why] Local indexing of KSERC regulatory documents
    RAG_STORAGE_DIR: str = os.getenv("RAG_STORAGE_DIR", "data/rag")
    RAG_INDEX_FILE: str = os.getenv("RAG_INDEX_FILE", "data/rag/index.json")
    RAG_SEED_DIR: str = os.getenv(
        "RAG_SEED_DIR",
        "/home/prak05/GITHUB/KSERC/Material"
    )
    # [Comment] Remote RAG index (Cloudflare Worker + R2)
    # [Why] Offload indexing away from local machine
    RAG_REMOTE_BASE_URL: str = os.getenv("RAG_REMOTE_BASE_URL", "")
    RAG_REMOTE_TOKEN: str = os.getenv("RAG_REMOTE_TOKEN", "")

    # [Comment] Verdict output directory
    # [Why] Store generated PDF verdicts
    VERDICT_DIR: str = os.getenv("VERDICT_DIR", "data/verdicts")

    # [Comment] GCS bucket for verdict PDFs
    # [Why] Persist verdicts across Cloud Run restarts
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "")
    GCS_PUBLIC_BASE_URL: str = os.getenv(
        "GCS_PUBLIC_BASE_URL",
        ""
    )

# [User Defined] Create a singleton instance of settings
# [Source] Singleton pattern for application-wide configuration
# [Why] Ensures only one instance of settings exists, accessible everywhere
settings = Settings()
