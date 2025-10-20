
import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    UPLOAD_ROOT = os.getenv("UPLOAD_ROOT", "uploads")
    ALLOWED_VIDEO_EXT = set(os.getenv("ALLOWED_VIDEO_EXT", "mp4,webm,mov,m4v,avi").lower().split(","))
    SITE_TITLE = os.getenv("SITE_TITLE", "Knowledge Base - Tawrid")
    BRAND = os.getenv("BRAND", "Tawrid")
    CATEGORIES = [
        ("01_supplier", "Supplier"),
        ("02_buyer", "Buyer"),
        ("03_funder", "Funder"),
    ]