import os
import firebase_admin
from firebase_admin import credentials

_initialized = False


def get_firebase_app() -> firebase_admin.App:
    """Initialize and return the Firebase Admin app (singleton)."""
    global _initialized
    if _initialized:
        return firebase_admin.get_app()

    service_account_path = os.getenv(
        "FIREBASE_SERVICE_ACCOUNT_PATH",
        os.path.join(os.path.dirname(__file__), "service-account.json"),
    )

    if not os.path.isfile(service_account_path):
        raise FileNotFoundError(
            "Firebase Admin SDK service account JSON not found at "
            f"{service_account_path}. Download it from Firebase Console → "
            "Project settings → Service accounts, or set FIREBASE_SERVICE_ACCOUNT_PATH."
        )

    cred = credentials.Certificate(service_account_path)
    app = firebase_admin.initialize_app(cred)
    _initialized = True
    return app
