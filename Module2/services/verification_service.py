import requests
import hashlib

from Module2.services.firebase_service import find_identity_by_documents
from Module2.services.firpiv_service import extract_fingerprint_template
from Module2.services.matcher_service import match_templates
from Module2.routes.enrollment import generate_record_hash


def download_enrolled_firpiv(ipfs_url, ipfs_cid=None, timeout=5):
    """
    Attempt to download the enrolled .firpiv file from IPFS.
    Uses multiple public gateway fallbacks.
    Returns (bytes, error_message).
    """
    gateways = []
    if ipfs_url:
        gateways.append(ipfs_url)

    cid = ipfs_cid
    if not cid and ipfs_url and "/ipfs/" in ipfs_url:
        cid = ipfs_url.split("/ipfs/")[-1].split("?")[0].strip()

    if cid:
        for gw in [
            f"https://ipfs.io/ipfs/{cid}",
            f"https://cloudflare-ipfs.com/ipfs/{cid}",
            f"https://dweb.link/ipfs/{cid}",
            f"https://gateway.pinata.cloud/ipfs/{cid}"
        ]:
            if gw not in gateways:
                gateways.append(gw)

    for url in gateways:
        try:
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == 200 and resp.content:
                return resp.content, None
        except Exception as e:
            continue

    return None, "Unable to retrieve enrolled .firpiv from IPFS gateways"


def verify_identity_workflow(passport_number, second_doc_number=None, second_doc_type=None, officer_firpiv_bytes=None):
    """
    Main Module 2 Officer Verification Workflow.

    Steps:
    1. Search Firestore verification_db by document numbers from Module 1.
    2. Retrieve enrolled record and obtain Template A.
    3. Extract Template B from officer's newly uploaded .firpiv bytes.
    4. Biometric matching: Template A vs Template B.
    5. If fingerprint matches, verify canonical blockchain integrity hash.
    6. Return unified verification decision according to required schema.
    """
    # ----------------------------------------------------
    # Input Validation
    # ----------------------------------------------------
    if not passport_number:
        return {
            "success": False,
            "verification": {
                "identity_found": False,
                "fingerprint_match": False,
                "hash_match": False,
                "final_status": "NOT_VERIFIED"
            },
            "reason": "Passport number missing from Module 1 extraction"
        }, 400

    if not second_doc_number:
        return {
            "success": False,
            "verification": {
                "identity_found": False,
                "fingerprint_match": False,
                "hash_match": False,
                "final_status": "NOT_VERIFIED"
            },
            "reason": f"{second_doc_type or 'Aadhaar / Driving License'} number missing from Module 1 extraction"
        }, 400

    if not officer_firpiv_bytes:
        return {
            "success": False,
            "verification": {
                "identity_found": False,
                "fingerprint_match": False,
                "hash_match": False,
                "final_status": "NOT_VERIFIED"
            },
            "reason": "Fingerprint file (.firpiv) missing"
        }, 400

    # ----------------------------------------------------
    # 1. Search Firestore for Enrolled Identity Record
    # ----------------------------------------------------
    enrolled_record, search_error = find_identity_by_documents(
        passport_number=passport_number,
        second_doc_number=second_doc_number,
        second_doc_type=second_doc_type
    )

    if not enrolled_record:
        return {
            "success": True,
            "verification": {
                "identity_found": False,
                "fingerprint_match": False,
                "hash_match": False,
                "final_status": "NOT_VERIFIED"
            },
            "reason": search_error or "Identity record not found"
        }, 200

    # ----------------------------------------------------
    # 2. Extract Template B from Officer's .firpiv File
    # ----------------------------------------------------
    try:
        template_b = extract_fingerprint_template(officer_firpiv_bytes)
    except ValueError as ve:
        return {
            "success": False,
            "verification": {
                "identity_found": True,
                "fingerprint_match": False,
                "hash_match": False,
                "final_status": "NOT_VERIFIED"
            },
            "reason": f"Invalid .firpiv file: {str(ve)}"
        }, 400
    except Exception as e:
        return {
            "success": False,
            "verification": {
                "identity_found": True,
                "fingerprint_match": False,
                "hash_match": False,
                "final_status": "NOT_VERIFIED"
            },
            "reason": f"FIRPIV template extraction failure: {str(e)}"
        }, 400

    # ----------------------------------------------------
    # 3. Retrieve Enrolled Template A
    #    (From Firestore record; optionally enriched from IPFS)
    # ----------------------------------------------------
    template_a = enrolled_record.get("fingerprint_template")

    # If not directly stored or if verifying against IPFS binary
    fp_file_info = enrolled_record.get("fingerprint_file", {})
    ipfs_url = fp_file_info.get("ipfs_url") if isinstance(fp_file_info, dict) else None
    ipfs_cid = fp_file_info.get("ipfs_cid") if isinstance(fp_file_info, dict) else None

    if not template_a and ipfs_url:
        ipfs_bytes, ipfs_err = download_enrolled_firpiv(ipfs_url, ipfs_cid=ipfs_cid)
        if ipfs_bytes:
            try:
                template_a = extract_fingerprint_template(ipfs_bytes)
            except Exception as e:
                return {
                    "success": False,
                    "verification": {
                        "identity_found": True,
                        "fingerprint_match": False,
                        "hash_match": False,
                        "final_status": "NOT_VERIFIED"
                    },
                    "reason": f"Enrolled fingerprint extraction failure from IPFS: {str(e)}"
                }, 500
        else:
            return {
                "success": False,
                "verification": {
                    "identity_found": True,
                    "fingerprint_match": False,
                    "hash_match": False,
                    "final_status": "NOT_VERIFIED"
                },
                "reason": f"IPFS file unavailable and no stored template: {ipfs_err}"
            }, 502

    if not template_a:
        return {
            "success": False,
            "verification": {
                "identity_found": True,
                "fingerprint_match": False,
                "hash_match": False,
                "final_status": "NOT_VERIFIED"
            },
            "reason": "Enrolled fingerprint template missing from record"
        }, 500

    # ----------------------------------------------------
    # 4. Biometric Fingerprint Matching (Template A vs Template B)
    # ----------------------------------------------------
    is_fp_match, match_score, match_details = match_templates(
        template_a=template_a,
        template_b=template_b,
        min_good_matches=15,
        min_score=0.15
    )

    if not is_fp_match:
        return {
            "success": True,
            "verification": {
                "identity_found": True,
                "fingerprint_match": False,
                "hash_match": False,
                "final_status": "NOT_VERIFIED"
            },
            "reason": "Fingerprint mismatch",
            "identity": {
                "national_id": enrolled_record.get("national_id"),
                "name": enrolled_record.get("name")
            },
            "fingerprint": {
                "match": False,
                "score": match_score
            }
        }, 200

    # ----------------------------------------------------
    # 5. Simulated Blockchain Hash / Integrity Check
    #    CRITICAL: Uses canonical enrolled data & Template A!
    # ----------------------------------------------------
    calculated_hash = generate_record_hash(enrolled_record)
    stored_hash = enrolled_record.get("hash")

    is_hash_match = bool(stored_hash and calculated_hash == stored_hash)

    if not is_hash_match:
        return {
            "success": True,
            "verification": {
                "identity_found": True,
                "fingerprint_match": True,
                "hash_match": False,
                "final_status": "NOT_VERIFIED"
            },
            "reason": "Record integrity verification failed",
            "identity": {
                "national_id": enrolled_record.get("national_id"),
                "name": enrolled_record.get("name")
            },
            "fingerprint": {
                "match": True,
                "score": match_score
            },
            "integrity": {
                "hash_match": False
            }
        }, 200

    # ----------------------------------------------------
    # 6. Full Verification Succeeded!
    # ----------------------------------------------------
    return {
        "success": True,
        "verification": {
            "identity_found": True,
            "fingerprint_match": True,
            "hash_match": True,
            "final_status": "VERIFIED"
        },
        "identity": {
            "national_id": enrolled_record.get("national_id"),
            "name": enrolled_record.get("name")
        },
        "fingerprint": {
            "match": True,
            "score": match_score
        },
        "integrity": {
            "hash_match": True
        }
    }, 200

