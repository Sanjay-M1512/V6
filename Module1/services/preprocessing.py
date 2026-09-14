import cv2
import numpy as np


# ============================================================
# IMAGE LOADING
# ============================================================

def load_image(image_path):
    """
    Load an image from disk.
    """

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(
            f"Unable to read image: {image_path}"
        )

    return image


# ============================================================
# IMAGE RESIZING
# ============================================================

def resize_image(
    image,
    target_width=2000
):
    """
    Resize image while preserving aspect ratio.

    OCR generally performs better when document text
    has sufficient pixel resolution.
    """

    height, width = image.shape[:2]

    # Do not enlarge an already large image
    if width >= target_width:
        return image

    scale = target_width / width

    new_width = int(width * scale)
    new_height = int(height * scale)

    return cv2.resize(
        image,
        (new_width, new_height),
        interpolation=cv2.INTER_CUBIC
    )


# ============================================================
# GRAYSCALE
# ============================================================

def convert_to_grayscale(image):
    """
    Convert BGR image to grayscale.
    """

    return cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )


# ============================================================
# CONTRAST ENHANCEMENT
# ============================================================

def enhance_contrast(gray_image):
    """
    Improve local contrast using CLAHE.

    Useful when document text has uneven lighting.
    """

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    return clahe.apply(gray_image)


# ============================================================
# DENOISING
# ============================================================

def remove_noise(gray_image):
    """
    Remove small image noise while keeping text edges.
    """

    return cv2.GaussianBlur(
        gray_image,
        (3, 3),
        0
    )


# ============================================================
# ADAPTIVE THRESHOLD
# ============================================================

def adaptive_threshold(gray_image):
    """
    Convert image into a binary document image.
    """

    return cv2.adaptiveThreshold(
        gray_image,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )


# ============================================================
# OTSU THRESHOLD
# ============================================================

def otsu_threshold(gray_image):
    """
    Global Otsu thresholding.

    Provides an additional OCR version when adaptive
    thresholding is not ideal.
    """

    _, binary = cv2.threshold(
        gray_image,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return binary


# ============================================================
# SHARPENING
# ============================================================

def sharpen_image(gray_image):
    """
    Slightly sharpen text edges.
    """

    kernel = np.array([
        [0, -1, 0],
        [-1, 5, -1],
        [0, -1, 0]
    ])

    return cv2.filter2D(
        gray_image,
        -1,
        kernel
    )


# ============================================================
# DOCUMENT BORDER CROP
# ============================================================

def crop_document_border(image):
    """
    Remove a small outer border from the document.

    This helps prevent page borders and black edges from
    confusing OCR.
    """

    height, width = image.shape[:2]

    margin_x = int(width * 0.01)
    margin_y = int(height * 0.01)

    if (
        width <= 2 * margin_x
        or height <= 2 * margin_y
    ):
        return image

    return image[
        margin_y:height - margin_y,
        margin_x:width - margin_x
    ]


# ============================================================
# PASSPORT MRZ REGION
# ============================================================

def extract_passport_mrz_region(image):
    """
    Extract the lower portion of a passport image where
    the two-line MRZ normally appears.

    This does NOT attempt to parse the MRZ.
    It only creates a focused image for OCR.
    """

    height, width = image.shape[:2]

    # Bottom approximately 24% of the passport page
    start_y = int(height * 0.76)

    mrz_region = image[
        start_y:height,
        0:width
    ]

    return mrz_region


# ============================================================
# AADHAAR TEXT REGION
# ============================================================

def extract_aadhaar_text_region(image):
    """
    Extract the central text-heavy portion of an Aadhaar
    image.

    QR code is deliberately excluded from processing.
    """

    height, width = image.shape[:2]

    # Keep central/left document content.
    # This avoids focusing OCR on the large QR area.
    x1 = int(width * 0.03)
    x2 = int(width * 0.75)

    y1 = int(height * 0.25)
    y2 = int(height * 0.90)

    return image[
        y1:y2,
        x1:x2
    ]


# ============================================================
# PREPARE OCR VARIANTS
# ============================================================

def create_ocr_variants(image):
    """
    Create multiple image variants for OCR.

    Different document regions may work better with
    different preprocessing methods.
    """

    gray = convert_to_grayscale(image)

    contrast = enhance_contrast(gray)

    denoised = remove_noise(contrast)

    sharpened = sharpen_image(denoised)

    adaptive = adaptive_threshold(
        denoised
    )

    otsu = otsu_threshold(
        denoised
    )

    return {
        "gray": gray,
        "contrast": contrast,
        "denoised": denoised,
        "sharpened": sharpened,
        "adaptive": adaptive,
        "otsu": otsu
    }


# ============================================================
# COMPLETE DOCUMENT PREPROCESSING
# ============================================================

def preprocess_image(image_path):
    """
    Complete preprocessing pipeline.

    Returns the original image plus multiple OCR-ready
    versions and focused document regions.
    """

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    original = load_image(
        image_path
    )

    # --------------------------------------------------------
    # Resize
    # --------------------------------------------------------

    resized = resize_image(
        original,
        target_width=2000
    )

    # --------------------------------------------------------
    # Remove small outer border
    # --------------------------------------------------------

    document = crop_document_border(
        resized
    )

    # --------------------------------------------------------
    # General OCR variants
    # --------------------------------------------------------

    variants = create_ocr_variants(
        document
    )

    # --------------------------------------------------------
    # Passport MRZ region
    # --------------------------------------------------------

    mrz_region = extract_passport_mrz_region(
        document
    )

    mrz_variants = create_ocr_variants(
        mrz_region
    )

    # --------------------------------------------------------
    # Aadhaar text region
    # --------------------------------------------------------

    aadhaar_region = extract_aadhaar_text_region(
        document
    )

    aadhaar_variants = create_ocr_variants(
        aadhaar_region
    )

    # --------------------------------------------------------
    # Return everything
    # --------------------------------------------------------

    return {
        "original": original,

        "document": document,

        # General document OCR
        "gray": variants["gray"],
        "contrast": variants["contrast"],
        "denoised": variants["denoised"],
        "sharpened": variants["sharpened"],
        "adaptive": variants["adaptive"],
        "otsu": variants["otsu"],

        # Passport MRZ
        "mrz_region": mrz_region,
        "mrz_gray": mrz_variants["gray"],
        "mrz_contrast": mrz_variants["contrast"],
        "mrz_sharpened": mrz_variants["sharpened"],
        "mrz_adaptive": mrz_variants["adaptive"],
        "mrz_otsu": mrz_variants["otsu"],

        # Aadhaar text region
        "aadhaar_region": aadhaar_region,
        "aadhaar_gray": aadhaar_variants["gray"],
        "aadhaar_contrast": aadhaar_variants["contrast"],
        "aadhaar_sharpened": aadhaar_variants["sharpened"],
        "aadhaar_adaptive": aadhaar_variants["adaptive"],
        "aadhaar_otsu": aadhaar_variants["otsu"]
    }