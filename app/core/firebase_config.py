import os

import firebase_admin
from firebase_admin import credentials


def init_firebase():
    """Initialize Firebase Admin SDK with service account credentials."""
    if firebase_admin._apps:
        return firebase_admin.get_app()

    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "voicely-firebase-adminsdk.json")
    if not os.path.exists(cred_path):
        raise FileNotFoundError(f"Firebase credentials not found at {cred_path}")

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    return firebase_admin.get_app()
