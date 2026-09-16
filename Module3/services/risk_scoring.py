"""
Module 3 - Risk Scoring Engine

Calculates a 0-100 risk score using the signals currently available
from face matching, liveness, and face quality analysis.

Higher score = higher risk.
"""

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

# SFace cosine similarity threshold currently used by the project.
MATCH_THRESHOLD = 0.363

# Similarity above this value is treated as strong confidence.
HIGH_CONFIDENCE_THRESHOLD = 0.60

# Quality score below this value is considered poor.
LOW_QUALITY_THRESHOLD = 0.35


# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def clamp(value, minimum=0.0, maximum=1.0):
    """Keep a numeric value inside a given range."""
    return max(minimum, min(maximum, float(value)))


def similarity_to_risk(similarity):
    """
    Convert face similarity into a risk value.

    similarity:
        0.0 -> very poor match
        1.0 -> excellent match

    Returns:
        0.0 -> no risk
        1.0 -> maximum risk
    """

    similarity = clamp(similarity)

    if similarity >= HIGH_CONFIDENCE_THRESHOLD:
        return 0.0

    if similarity <= MATCH_THRESHOLD:
        return 1.0

    # Linear interpolation between the match threshold
    # and high-confidence threshold.
    risk = (
        HIGH_CONFIDENCE_THRESHOLD - similarity
    ) / (
        HIGH_CONFIDENCE_THRESHOLD - MATCH_THRESHOLD
    )

    return clamp(risk)


def quality_to_risk(quality):
    """
    Convert face quality score into risk.

    Higher quality = lower risk.
    """

    quality = clamp(quality)

    return clamp(1.0 - quality)


def liveness_to_risk(liveness_decision):
    """
    Convert liveness result into risk.
    """

    if not liveness_decision:
        return 1.0

    decision = str(liveness_decision).upper()

    if decision == "REAL":
        return 0.0

    return 1.0


# ---------------------------------------------------------
# Main Risk Scoring Function
# ---------------------------------------------------------

def calculate_risk_score(
    passport_aadhaar_similarity,
    passport_live_similarity,
    aadhaar_live_similarity,
    liveness_decision,
    passport_quality=1.0,
    aadhaar_quality=1.0,
    live_quality=1.0
):
    """
    Calculate the overall Module 3 risk score.

    The current prototype uses only signals already available
    in Module 3.

    Weights:

        Passport <-> Aadhaar    20%
        Passport <-> Live       25%
        Aadhaar <-> Live        25%
        Liveness                15%
        Passport quality         5%
        Aadhaar quality          3%
        Live quality             7%

        Total                   100%

    Returns a dictionary containing:
        - risk_score
        - risk_level
        - identity_status
        - liveness_status
        - face_match_confidence
        - document_face_quality
        - reasons
    """

    # -----------------------------------------------------
    # Convert similarities / quality values to risk values
    # -----------------------------------------------------

    passport_aadhaar_risk = similarity_to_risk(
        passport_aadhaar_similarity
    )

    passport_live_risk = similarity_to_risk(
        passport_live_similarity
    )

    aadhaar_live_risk = similarity_to_risk(
        aadhaar_live_similarity
    )

    liveness_risk = liveness_to_risk(
        liveness_decision
    )

    passport_quality_risk = quality_to_risk(
        passport_quality
    )

    aadhaar_quality_risk = quality_to_risk(
        aadhaar_quality
    )

    live_quality_risk = quality_to_risk(
        live_quality
    )

    # -----------------------------------------------------
    # Weighted risk calculation
    # -----------------------------------------------------

    weighted_risk = (
        passport_aadhaar_risk * 0.20
        + passport_live_risk * 0.25
        + aadhaar_live_risk * 0.25
        + liveness_risk * 0.15
        + passport_quality_risk * 0.05
        + aadhaar_quality_risk * 0.03
        + live_quality_risk * 0.07
    )

    # Convert 0-1 risk to 0-100.
    risk_score = round(
        clamp(weighted_risk) * 100,
        2
    )

    # -----------------------------------------------------
    # Risk level
    # -----------------------------------------------------

    if risk_score < 30:
        risk_level = "LOW"

    elif risk_score < 60:
        risk_level = "MEDIUM"

    else:
        risk_level = "HIGH"

    # -----------------------------------------------------
    # Identity status
    # -----------------------------------------------------

    all_faces_match = (
        passport_aadhaar_similarity >= MATCH_THRESHOLD
        and passport_live_similarity >= MATCH_THRESHOLD
        and aadhaar_live_similarity >= MATCH_THRESHOLD
    )

    identity_status = (
        "IDENTITY VERIFIED"
        if all_faces_match and str(liveness_decision).upper() == "REAL"
        else "IDENTITY NOT VERIFIED"
    )

    # -----------------------------------------------------
    # Face match confidence
    # -----------------------------------------------------

    minimum_similarity = min(
        passport_aadhaar_similarity,
        passport_live_similarity,
        aadhaar_live_similarity
    )

    if minimum_similarity >= HIGH_CONFIDENCE_THRESHOLD:
        face_match_confidence = "HIGH"

    elif minimum_similarity >= MATCH_THRESHOLD:
        face_match_confidence = "MEDIUM"

    else:
        face_match_confidence = "LOW"

    # -----------------------------------------------------
    # Document face quality
    # -----------------------------------------------------

    document_quality_average = (
        passport_quality + aadhaar_quality
    ) / 2.0

    if document_quality_average >= 0.70:
        document_face_quality = "GOOD"

    elif document_quality_average >= LOW_QUALITY_THRESHOLD:
        document_face_quality = "ACCEPTABLE"

    else:
        document_face_quality = "LOW"

    # -----------------------------------------------------
    # Reasons
    # -----------------------------------------------------

    reasons = []

    if passport_aadhaar_similarity < MATCH_THRESHOLD:
        reasons.append(
            "Passport and Aadhaar face similarity is below threshold."
        )

    if passport_live_similarity < MATCH_THRESHOLD:
        reasons.append(
            "Passport and live face similarity is below threshold."
        )

    if aadhaar_live_similarity < MATCH_THRESHOLD:
        reasons.append(
            "Aadhaar and live face similarity is below threshold."
        )

    if str(liveness_decision).upper() != "REAL":
        reasons.append(
            "Liveness verification was not confirmed."
        )

    if passport_quality < LOW_QUALITY_THRESHOLD:
        reasons.append(
            "Passport face image quality is low."
        )

    if aadhaar_quality < LOW_QUALITY_THRESHOLD:
        reasons.append(
            "Aadhaar face image quality is low."
        )

    if live_quality < LOW_QUALITY_THRESHOLD:
        reasons.append(
            "Live face image quality is low."
        )

    if not reasons:
        reasons.append(
            "No significant Module 3 risk indicators detected."
        )

    # -----------------------------------------------------
    # Final result
    # -----------------------------------------------------

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,

        "identity_status": identity_status,

        "liveness_status": (
            "REAL"
            if str(liveness_decision).upper() == "REAL"
            else "NOT VERIFIED"
        ),

        "face_match_confidence": face_match_confidence,

        "document_face_quality": document_face_quality,

        "minimum_face_similarity": round(
            float(minimum_similarity),
            4
        ),

        "reasons": reasons,

        "signals": {
            "passport_aadhaar_similarity": round(
                float(passport_aadhaar_similarity),
                4
            ),
            "passport_live_similarity": round(
                float(passport_live_similarity),
                4
            ),
            "aadhaar_live_similarity": round(
                float(aadhaar_live_similarity),
                4
            ),
            "passport_quality": round(
                float(passport_quality),
                3
            ),
            "aadhaar_quality": round(
                float(aadhaar_quality),
                3
            ),
            "live_quality": round(
                float(live_quality),
                3
            ),
            "liveness_decision": liveness_decision
        }
    }


# ---------------------------------------------------------
# Convenience Function
# ---------------------------------------------------------

def calculate_risk_from_identity_result(
    identity_result,
    passport_quality=1.0,
    aadhaar_quality=1.0,
    live_quality=1.0,
    liveness_decision="REAL"
):
    """
    Calculate risk directly from the result returned by
    compare_identity_faces().
    """

    passport_aadhaar = identity_result.get(
        "passport_aadhaar",
        {}
    )

    passport_live = identity_result.get(
        "passport_live",
        {}
    )

    aadhaar_live = identity_result.get(
        "aadhaar_live",
        {}
    )

    return calculate_risk_score(
        passport_aadhaar_similarity=passport_aadhaar.get(
            "similarity",
            0.0
        ),

        passport_live_similarity=passport_live.get(
            "similarity",
            0.0
        ),

        aadhaar_live_similarity=aadhaar_live.get(
            "similarity",
            0.0
        ),

        liveness_decision=liveness_decision,

        passport_quality=passport_quality,

        aadhaar_quality=aadhaar_quality,

        live_quality=live_quality
    )