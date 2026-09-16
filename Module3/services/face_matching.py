import os
import cv2
import numpy as np


# ============================================================
# MODEL PATH
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "face_recognition_sface",
    "face_recognition_sface_2021dec.onnx"
)


# ============================================================
# MATCHING THRESHOLD
# ============================================================

# OpenCV SFace cosine similarity example uses approximately
# 0.363 as a reference threshold.
#
# This is a prototype threshold and should NOT be treated
# as a production identity-verification threshold.

COSINE_THRESHOLD = 0.363


# ============================================================
# LOAD SFACE MODEL
# ============================================================

_face_recognizer = None


def get_face_recognizer():
    """
    Load the SFace model only when required.
    """

    global _face_recognizer

    if _face_recognizer is not None:
        return _face_recognizer

    if not os.path.exists(MODEL_PATH):

        raise FileNotFoundError(
            "SFace model not found at: "
            + MODEL_PATH
        )

    _face_recognizer = cv2.FaceRecognizerSF.create(
        MODEL_PATH,
        ""
    )

    return _face_recognizer


# ============================================================
# LOAD IMAGE
# ============================================================

def load_face_image(image_path):
    """
    Load a face image from disk.
    """

    if not image_path:
        return None

    image = cv2.imread(
        image_path
    )

    return image


# ============================================================
# FACE ALIGNMENT / FEATURE EXTRACTION
# ============================================================

def extract_face_feature(face_image):
    """
    Extract the SFace feature vector from an already
    cropped face image.

    Returns:
        feature vector
    """

    if face_image is None:
        raise ValueError(
            "Face image is empty."
        )

    if face_image.size == 0:
        raise ValueError(
            "Face image contains no data."
        )

    recognizer = get_face_recognizer()

    # --------------------------------------------------------
    # SFace expects a face image and performs its own
    # feature extraction after alignment.
    #
    # Since our face_input module already gives us a cropped
    # face, we use that crop directly.
    # --------------------------------------------------------

    feature = recognizer.feature(
        face_image
    )

    return feature


# ============================================================
# COSINE SIMILARITY
# ============================================================

def cosine_similarity(
    feature1,
    feature2
):
    """
    Calculate cosine similarity between two SFace
    feature vectors.
    """

    if feature1 is None or feature2 is None:

        return 0.0

    feature1 = np.asarray(
        feature1,
        dtype=np.float32
    )

    feature2 = np.asarray(
        feature2,
        dtype=np.float32
    )

    norm1 = np.linalg.norm(
        feature1
    )

    norm2 = np.linalg.norm(
        feature2
    )

    if norm1 == 0 or norm2 == 0:

        return 0.0

    similarity = np.dot(
        feature1.flatten(),
        feature2.flatten()
    ) / (
        norm1 * norm2
    )

    return float(similarity)


# ============================================================
# MATCH TWO FACE IMAGES
# ============================================================

def match_face_images(
    face_image1,
    face_image2
):
    """
    Compare two face images using SFace.

    Returns:
        similarity
        decision
    """

    if face_image1 is None:

        return {
            "success": False,
            "similarity": 0.0,
            "decision": "ERROR",
            "message":
                "First face image is missing."
        }

    if face_image2 is None:

        return {
            "success": False,
            "similarity": 0.0,
            "decision": "ERROR",
            "message":
                "Second face image is missing."
        }

    try:

        feature1 = extract_face_feature(
            face_image1
        )

        feature2 = extract_face_feature(
            face_image2
        )

        similarity = cosine_similarity(
            feature1,
            feature2
        )

        similarity = round(
            similarity,
            4
        )

        if similarity >= COSINE_THRESHOLD:

            decision = "MATCHED"

        else:

            decision = "NOT MATCHED"

        return {

            "success": True,

            "similarity":
                similarity,

            "threshold":
                COSINE_THRESHOLD,

            "decision":
                decision,

            "message":
                (
                    "Faces matched successfully."
                    if decision == "MATCHED"
                    else "Faces do not match."
                )
        }

    except Exception as error:

        return {

            "success": False,

            "similarity": 0.0,

            "threshold":
                COSINE_THRESHOLD,

            "decision": "ERROR",

            "message":
                str(error)
        }


# ============================================================
# MATCH TWO FACE FILES
# ============================================================

def match_face_files(
    face_path1,
    face_path2
):
    """
    Load two face images from disk and compare them.
    """

    face1 = load_face_image(
        face_path1
    )

    face2 = load_face_image(
        face_path2
    )

    if face1 is None:

        return {

            "success": False,

            "similarity": 0.0,

            "decision": "ERROR",

            "message":
                "Unable to read first face image."
        }

    if face2 is None:

        return {

            "success": False,

            "similarity": 0.0,

            "decision": "ERROR",

            "message":
                "Unable to read second face image."
        }

    return match_face_images(
        face1,
        face2
    )


# ============================================================
# MATCH MULTIPLE FACES
# ============================================================

def compare_identity_faces(
    passport_face,
    aadhaar_face,
    live_face
):
    """
    Compare:

        Passport ↔ Aadhaar
        Passport ↔ Live
        Aadhaar ↔ Live

    Returns all three comparisons plus an overall result.
    """

    passport_aadhaar = match_face_images(
        passport_face,
        aadhaar_face
    )

    passport_live = match_face_images(
        passport_face,
        live_face
    )

    aadhaar_live = match_face_images(
        aadhaar_face,
        live_face
    )


    all_successful = (
        passport_aadhaar["success"]
        and
        passport_live["success"]
        and
        aadhaar_live["success"]
    )


    if not all_successful:

        overall_decision = "ERROR"

    else:

        all_matched = (

            passport_aadhaar["decision"]
            == "MATCHED"

            and

            passport_live["decision"]
            == "MATCHED"

            and

            aadhaar_live["decision"]
            == "MATCHED"
        )


        if all_matched:

            overall_decision = (
                "IDENTITY VERIFIED"
            )

        else:

            overall_decision = (
                "IDENTITY NOT VERIFIED"
            )


    return {

        "success":
            all_successful,

        "passport_aadhaar":
            passport_aadhaar,

        "passport_live":
            passport_live,

        "aadhaar_live":
            aadhaar_live,

        "overall_decision":
            overall_decision
    }