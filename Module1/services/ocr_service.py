import os
import re
import pytesseract


# ============================================================
# TESSERACT CONFIGURATION
# ============================================================

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# ============================================================
# BASIC OCR
# ============================================================

def extract_text(
    image,
    psm=6
):
    """
    Extract text from an image using Tesseract.

    psm:
        6  = Assume a uniform block of text
        11 = Sparse text
        7  = Single text line
    """

    if image is None:
        raise ValueError(
            "Invalid image supplied to OCR"
        )

    config = f"--oem 3 --psm {psm}"

    text = pytesseract.image_to_string(
        image,
        config=config
    )

    return text.strip()


# ============================================================
# OCR WITH POSITION + CONFIDENCE
# ============================================================

def extract_text_with_data(
    image,
    psm=6
):
    """
    Extract OCR text together with:

        text
        confidence
        x/y position
        width/height
    """

    if image is None:
        raise ValueError(
            "Invalid image supplied to OCR"
        )

    config = f"--oem 3 --psm {psm}"

    data = pytesseract.image_to_data(
        image,
        config=config,
        output_type=pytesseract.Output.DICT
    )

    results = []

    for i in range(
        len(data["text"])
    ):

        text = data["text"][i].strip()

        if not text:
            continue

        try:
            confidence = float(
                data["conf"][i]
            )
        except (
            ValueError,
            TypeError
        ):
            confidence = -1

        results.append({
            "text": text,
            "confidence": confidence,

            "left": data["left"][i],
            "top": data["top"][i],
            "width": data["width"][i],
            "height": data["height"][i]
        })

    return results


# ============================================================
# CONFIDENCE CALCULATION
# ============================================================

def calculate_ocr_confidence(
    ocr_data
):
    """
    Calculate average OCR confidence.
    """

    if not ocr_data:
        return 0.0

    valid = [
        item["confidence"]
        for item in ocr_data
        if item["confidence"] >= 0
    ]

    if not valid:
        return 0.0

    return round(
        sum(valid) / len(valid),
        2
    )


# ============================================================
# SELECT BEST OCR RESULT
# ============================================================

def select_best_result(
    results
):
    """
    Select the most useful OCR result.

    We don't simply select the longest text.
    Confidence and text quantity are both considered.
    """

    if not results:
        return {
            "text": "",
            "ocr_data": [],
            "confidence": 0.0,
            "psm": None,
            "variant": None
        }

    best = None
    best_score = -1

    for result in results:

        text = result["text"]

        confidence = result[
            "confidence"
        ]

        # Number of useful characters
        useful_chars = len(
            re.sub(
                r"\s+",
                "",
                text
            )
        )

        # Don't reward extremely tiny OCR results
        text_score = min(
            useful_chars,
            500
        )

        score = (
            confidence * 0.7
            +
            text_score * 0.3
        )

        if score > best_score:

            best_score = score
            best = result

    return best


# ============================================================
# GENERAL DOCUMENT OCR
# ============================================================

def perform_general_ocr(
    preprocessed_images
):
    """
    Run OCR over the main document using several
    preprocessing variants.
    """

    variants = [
        (
            "gray",
            preprocessed_images.get("gray"),
            6
        ),
        (
            "contrast",
            preprocessed_images.get("contrast"),
            6
        ),
        (
            "denoised",
            preprocessed_images.get("denoised"),
            6
        ),
        (
            "sharpened",
            preprocessed_images.get("sharpened"),
            6
        ),
        (
            "adaptive",
            preprocessed_images.get("adaptive"),
            6
        ),
        (
            "otsu",
            preprocessed_images.get("otsu"),
            6
        )
    ]

    results = []

    for variant_name, image, psm in variants:

        if image is None:
            continue

        text = extract_text(
            image,
            psm=psm
        )

        ocr_data = extract_text_with_data(
            image,
            psm=psm
        )

        confidence = calculate_ocr_confidence(
            ocr_data
        )

        results.append({
            "text": text,
            "ocr_data": ocr_data,
            "confidence": confidence,
            "psm": psm,
            "variant": variant_name
        })

    return select_best_result(
        results
    )


# ============================================================
# PASSPORT MRZ OCR
# ============================================================

def perform_mrz_ocr(
    preprocessed_images
):
    """
    Perform OCR specifically on the Passport MRZ region.

    MRZ is different from normal document text, so we
    use single-block/sparse-line OCR configurations.
    """

    variants = [
        (
            "mrz_gray",
            preprocessed_images.get(
                "mrz_gray"
            ),
            6
        ),
        (
            "mrz_contrast",
            preprocessed_images.get(
                "mrz_contrast"
            ),
            6
        ),
        (
            "mrz_sharpened",
            preprocessed_images.get(
                "mrz_sharpened"
            ),
            6
        ),
        (
            "mrz_adaptive",
            preprocessed_images.get(
                "mrz_adaptive"
            ),
            6
        ),
        (
            "mrz_otsu",
            preprocessed_images.get(
                "mrz_otsu"
            ),
            6
        )
    ]

    results = []

    for variant_name, image, psm in variants:

        if image is None:
            continue

        text = extract_text(
            image,
            psm=psm
        )

        ocr_data = extract_text_with_data(
            image,
            psm=psm
        )

        confidence = calculate_ocr_confidence(
            ocr_data
        )

        results.append({
            "text": text,
            "ocr_data": ocr_data,
            "confidence": confidence,
            "psm": psm,
            "variant": variant_name
        })

    return select_best_result(
        results
    )


# ============================================================
# AADHAAR OCR
# ============================================================

def perform_aadhaar_ocr(
    preprocessed_images
):
    """
    OCR the Aadhaar text-focused region.

    QR code is not processed.
    """

    variants = [
        (
            "aadhaar_gray",
            preprocessed_images.get(
                "aadhaar_gray"
            ),
            6
        ),
        (
            "aadhaar_contrast",
            preprocessed_images.get(
                "aadhaar_contrast"
            ),
            6
        ),
        (
            "aadhaar_sharpened",
            preprocessed_images.get(
                "aadhaar_sharpened"
            ),
            6
        ),
        (
            "aadhaar_adaptive",
            preprocessed_images.get(
                "aadhaar_adaptive"
            ),
            6
        ),
        (
            "aadhaar_otsu",
            preprocessed_images.get(
                "aadhaar_otsu"
            ),
            6
        )
    ]

    results = []

    for variant_name, image, psm in variants:

        if image is None:
            continue

        text = extract_text(
            image,
            psm=psm
        )

        ocr_data = extract_text_with_data(
            image,
            psm=psm
        )

        confidence = calculate_ocr_confidence(
            ocr_data
        )

        results.append({
            "text": text,
            "ocr_data": ocr_data,
            "confidence": confidence,
            "psm": psm,
            "variant": variant_name
        })

    return select_best_result(
        results
    )


# ============================================================
# COMBINE OCR TEXT
# ============================================================

def combine_text(
    general_result,
    special_result
):
    """
    Combine general OCR with special-region OCR.

    The parser can then use both sources.
    """

    texts = []

    general_text = general_result.get(
        "text",
        ""
    )

    special_text = special_result.get(
        "text",
        ""
    )

    if general_text:
        texts.append(
            general_text
        )

    if special_text:

        # Avoid duplicating the exact same OCR
        if special_text.strip() not in [
            text.strip()
            for text in texts
        ]:

            texts.append(
                special_text
            )

    return "\n".join(texts)


# ============================================================
# COMPLETE OCR PIPELINE
# ============================================================

def perform_ocr(
    preprocessed_images
):
    """
    Complete OCR pipeline.

    Runs:
        1. General OCR
        2. Passport MRZ OCR
        3. Aadhaar focused OCR

    The parser receives all relevant OCR results.
    """

    # --------------------------------------------------------
    # General OCR
    # --------------------------------------------------------

    general_result = perform_general_ocr(
        preprocessed_images
    )


    # --------------------------------------------------------
    # Passport MRZ OCR
    # --------------------------------------------------------

    mrz_result = perform_mrz_ocr(
        preprocessed_images
    )


    # --------------------------------------------------------
    # Aadhaar OCR
    # --------------------------------------------------------

    aadhaar_result = perform_aadhaar_ocr(
        preprocessed_images
    )


    # --------------------------------------------------------
    # Combine useful OCR text
    # --------------------------------------------------------

    combined_text = combine_text(
        general_result,
        mrz_result
    )

    combined_text = combine_text(
        {
            "text": combined_text
        },
        aadhaar_result
    )


    # --------------------------------------------------------
    # Overall confidence
    # --------------------------------------------------------

    confidences = [
        result["confidence"]
        for result in [
            general_result,
            mrz_result,
            aadhaar_result
        ]
        if result["confidence"] > 0
    ]

    if confidences:

        overall_confidence = round(
            sum(confidences) / len(confidences),
            2
        )

    else:

        overall_confidence = 0.0


    # --------------------------------------------------------
    # Return complete OCR result
    # --------------------------------------------------------

    return {
        "text": combined_text,

        "confidence": overall_confidence,

        "general": general_result,

        "mrz": mrz_result,

        "aadhaar": aadhaar_result
    }