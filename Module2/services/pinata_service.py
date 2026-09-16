import os
import requests
from dotenv import load_dotenv

load_dotenv()

PINATA_API_KEY    = os.getenv("PINATA_API_KEY")
PINATA_SECRET_KEY = os.getenv("PINATA_SECRET_KEY")
PINATA_URL        = "https://api.pinata.cloud/pinning/pinFileToIPFS"


def upload_to_ipfs(file_bytes, filename):
    """
    Upload raw bytes to Pinata/IPFS.

    Parameters
    ----------
    file_bytes : bytes   — raw file content
    filename   : str     — original filename (e.g. a001.firpiv)

    Returns
    -------
    {
        "cid": "<IpfsHash>",
        "url": "https://gateway.pinata.cloud/ipfs/<IpfsHash>"
    }
    """

    if not PINATA_API_KEY or not PINATA_SECRET_KEY:
        raise EnvironmentError(
            "Pinata credentials missing — set PINATA_API_KEY "
            "and PINATA_SECRET_KEY in .env"
        )

    headers = {
        "pinata_api_key":        PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_SECRET_KEY
    }

    files = {
        "file": (filename, file_bytes, "application/octet-stream")
    }

    response = requests.post(
        PINATA_URL,
        files=files,
        headers=headers,
        timeout=60
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Pinata upload failed [{response.status_code}]: "
            f"{response.text}"
        )

    cid = response.json().get("IpfsHash")

    if not cid:
        raise RuntimeError(
            "Pinata response did not contain IpfsHash"
        )

    return {
        "cid": cid,
        "url": f"https://gateway.pinata.cloud/ipfs/{cid}"
    }
