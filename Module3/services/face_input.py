import cv2
import numpy as np


# OpenCV built-in face detector
FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    "haarcascade_frontalface_default.xml"
)


def detect_faces(image):
    """Detect all usable faces in an image."""

    if image is None:
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Improve detection under uneven lighting
    gray = cv2.equalizeHist(gray)

    faces = FACE_CASCADE.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(50, 50)
    )

    results = []

    for x, y, w, h in faces:
        results.append({
            "x": int(x),
            "y": int(y),
            "width": int(w),
            "height": int(h),
            "area": int(w * h)
        })

    return results


def calculate_blur_score(face):
    """Calculate sharpness using Laplacian variance."""

    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)

    return float(
        cv2.Laplacian(
            gray,
            cv2.CV_64F
        ).var()
    )


def calculate_brightness_score(face):
    """Check whether face lighting is usable."""

    gray = cv2.cvtColor(
        face,
        cv2.COLOR_BGR2GRAY
    )

    brightness = float(np.mean(gray))

    if 60 <= brightness <= 200:
        return 1.0

    if brightness < 60:
        return max(
            0.0,
            brightness / 60.0
        )

    return max(
        0.0,
        1.0 - ((brightness - 200) / 55.0)
    )


def calculate_quality_score(face):
    """
    Return face quality score between 0 and 1.
    """

    if face is None or face.size == 0:
        return 0.0

    blur_score = calculate_blur_score(face)

    # Normalize sharpness.
    # 500+ is considered sufficiently sharp.
    sharpness = min(
        blur_score / 500.0,
        1.0
    )

    brightness = calculate_brightness_score(face)

    quality = (
        0.7 * sharpness +
        0.3 * brightness
    )

    return round(
        float(np.clip(quality, 0.0, 1.0)),
        3
    )


def crop_face(image, face_box):
    """Crop detected face with a small margin."""

    x = face_box["x"]
    y = face_box["y"]
    w = face_box["width"]
    h = face_box["height"]

    image_h, image_w = image.shape[:2]

    # Margin around face
    margin_x = int(w * 0.20)
    margin_y = int(h * 0.20)

    x1 = max(0, x - margin_x)
    y1 = max(0, y - margin_y)

    x2 = min(
        image_w,
        x + w + margin_x
    )

    y2 = min(
        image_h,
        y + h + margin_y
    )

    return image[y1:y2, x1:x2]


def normalize_face(face):
    """
    Resize face to a standard size.

    112x112 will later be used by the face
    embedding module.
    """

    return cv2.resize(
        face,
        (112, 112),
        interpolation=cv2.INTER_AREA
    )


def determine_image_type(image, faces):
    """
    Automatically determine whether the uploaded image
    is probably a direct face image or a document image.

    This does NOT depend on the filename.

    Logic:
      - Large image with relatively small face -> document
      - Face occupying most of image -> direct face
    """

    if image is None:
        return "unknown"

    if not faces:
        return "unknown"

    image_h, image_w = image.shape[:2]
    image_area = image_h * image_w

    largest_face = max(
        faces,
        key=lambda f: f["area"]
    )

    face_ratio = (
        largest_face["area"] /
        float(image_area)
    )

    # If face occupies a large part of the image,
    # treat it as a direct face photograph.
    if face_ratio >= 0.20:
        return "face"

    return "document"


def process_face_input(image):
    """
    Main automatic Passport/Aadhaar face-input pipeline.

    Input:
        OpenCV BGR image

    Returns:
        Dictionary containing:
          image_type
          face_found
          face_image
          face_box
          face_quality_score
          blur_score
          quality_status
          message
    """

    if image is None:
        return {
            "success": False,
            "message": "Invalid image."
        }

    faces = detect_faces(image)

    if not faces:
        return {
            "success": False,
            "image_type": "unknown",
            "face_found": False,
            "face_image": None,
            "face_box": None,
            "face_quality_score": 0.0,
            "message": (
                "No usable face detected. "
                "Please upload a clearer document or face image."
            )
        }

    # Select largest face
    selected_face = max(
        faces,
        key=lambda f: f["area"]
    )

    image_type = determine_image_type(
        image,
        faces
    )

    # Crop face
    face = crop_face(
        image,
        selected_face
    )

    if face is None or face.size == 0:
        return {
            "success": False,
            "image_type": image_type,
            "face_found": False,
            "message": "Face extraction failed."
        }

    # Quality checks
    blur_score = calculate_blur_score(face)
    quality_score = calculate_quality_score(face)

    # Minimum acceptable quality
    if quality_score < 0.35:
        quality_status = "LOW"
    else:
        quality_status = "PASS"

    # Normalize extracted face
    normalized_face = normalize_face(face)

    return {
        "success": True,
        "image_type": image_type,
        "face_found": True,
        "face_count": len(faces),

        "face_image": normalized_face,

        "face_box": selected_face,

        "face_quality_score": quality_score,

        "blur_score": round(
            blur_score,
            2
        ),

        "quality_status": quality_status,

        "message": (
            "Face extracted successfully."
            if quality_status == "PASS"
            else
            "Face detected, but image quality is low."
        )
    }


def process_face_file(image_path):
    """Load an uploaded image and process it."""

    image = cv2.imread(image_path)

    if image is None:
        return {
            "success": False,
            "message": "Unable to read uploaded image."
        }

    return process_face_input(image)