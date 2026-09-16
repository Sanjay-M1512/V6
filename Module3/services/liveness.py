import cv2
import numpy as np
import mediapipe as mp


# ============================================================
# THRESHOLDS
# ============================================================

REAL_THRESHOLD = 0.70
UNCERTAIN_THRESHOLD = 0.40

# Eye Aspect Ratio (EAR) threshold used for blink detection.
# When EAR goes below this value, the eye is considered closed.
EAR_CLOSED_THRESHOLD = 0.21

# Minimum number of consecutive frames that the eye should
# remain closed before considering it a blink.
MIN_CLOSED_FRAMES = 2


# ============================================================
# MEDIAPIPE FACE MESH
# ============================================================

mp_face_mesh = mp.solutions.face_mesh

FACE_MESH = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)


# ============================================================
# EYE LANDMARKS
# ============================================================

# MediaPipe Face Mesh landmark indexes.
#
# Left eye
LEFT_EYE = [
    33,    # left corner
    160,   # upper
    158,   # upper
    133,   # right corner
    153,   # lower
    144    # lower
]

# Right eye
RIGHT_EYE = [
    362,   # left corner
    385,   # upper
    387,   # upper
    263,   # right corner
    373,   # lower
    380    # lower
]


# ============================================================
# BASIC IMAGE QUALITY FUNCTIONS
# ============================================================

def sharpness_score(face):
    """
    Calculate image sharpness using Laplacian variance.
    """

    if face is None or face.size == 0:
        return 0.0

    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)

    variance = cv2.Laplacian(
        gray,
        cv2.CV_64F
    ).var()

    score = min(
        variance / 500.0,
        1.0
    )

    return float(score)


def brightness_score(face):
    """
    Calculate brightness quality score.
    """

    if face is None or face.size == 0:
        return 0.0

    gray = cv2.cvtColor(
        face,
        cv2.COLOR_BGR2GRAY
    )

    brightness = float(
        np.mean(gray)
    )

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


def contrast_score(face):
    """
    Calculate contrast quality score.
    """

    if face is None or face.size == 0:
        return 0.0

    gray = cv2.cvtColor(
        face,
        cv2.COLOR_BGR2GRAY
    )

    contrast = float(
        np.std(gray)
    )

    score = min(
        contrast / 60.0,
        1.0
    )

    return float(score)


# ============================================================
# PASSIVE LIVENESS
# ============================================================

def passive_liveness_score(face):
    """
    Current passive liveness heuristic.

    This is NOT the final anti-spoofing mechanism.
    It checks image quality characteristics such as:
        - sharpness
        - brightness
        - contrast
    """

    if face is None or face.size == 0:

        return {
            "score": 0.0,
            "decision": "SPOOF",
            "sharpness": 0.0,
            "brightness": 0.0,
            "contrast": 0.0
        }

    sharpness = sharpness_score(face)
    brightness = brightness_score(face)
    contrast = contrast_score(face)

    score = (
        0.45 * sharpness +
        0.30 * brightness +
        0.25 * contrast
    )

    score = round(
        float(np.clip(score, 0.0, 1.0)),
        3
    )

    if score >= REAL_THRESHOLD:

        decision = "REAL"

    elif score >= UNCERTAIN_THRESHOLD:

        decision = "UNCERTAIN"

    else:

        decision = "SPOOF"

    return {

        "score": score,

        "decision": decision,

        "sharpness": round(
            sharpness,
            3
        ),

        "brightness": round(
            brightness,
            3
        ),

        "contrast": round(
            contrast,
            3
        )
    }


# ============================================================
# BLINK / EYE ASPECT RATIO
# ============================================================

def euclidean_distance(point1, point2):
    """
    Calculate Euclidean distance between two points.
    """

    return np.linalg.norm(
        np.array(point1) -
        np.array(point2)
    )


def calculate_eye_aspect_ratio(eye_points):
    """
    Calculate Eye Aspect Ratio (EAR).

    EAR becomes smaller when the eye closes.

    Formula:

        EAR = (vertical_distance_1 + vertical_distance_2)
              -------------------------------------------
                    (2 * horizontal_distance)
    """

    if len(eye_points) != 6:
        return 0.0

    p1 = eye_points[0]
    p2 = eye_points[1]
    p3 = eye_points[2]
    p4 = eye_points[3]
    p5 = eye_points[4]
    p6 = eye_points[5]

    horizontal = euclidean_distance(
        p1,
        p4
    )

    if horizontal == 0:
        return 0.0

    vertical_1 = euclidean_distance(
        p2,
        p6
    )

    vertical_2 = euclidean_distance(
        p3,
        p5
    )

    ear = (
        vertical_1 +
        vertical_2
    ) / (
        2.0 * horizontal
    )

    return float(ear)


def extract_eye_landmarks(image, landmarks, eye_indices):
    """
    Convert MediaPipe normalized landmarks
    into pixel coordinates.
    """

    image_h, image_w = image.shape[:2]

    points = []

    for index in eye_indices:

        landmark = landmarks[index]

        x = int(
            landmark.x * image_w
        )

        y = int(
            landmark.y * image_h
        )

        points.append(
            (x, y)
        )

    return points


def calculate_blink_metrics(image):
    """
    Detect eyes and calculate EAR for both eyes.

    Returns:
        left_ear
        right_ear
        average_ear
        face_detected
    """

    if image is None or image.size == 0:

        return {
            "face_detected": False,
            "left_ear": 0.0,
            "right_ear": 0.0,
            "average_ear": 0.0
        }

    rgb_image = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2RGB
    )

    result = FACE_MESH.process(
        rgb_image
    )

    if not result.multi_face_landmarks:

        return {
            "face_detected": False,
            "left_ear": 0.0,
            "right_ear": 0.0,
            "average_ear": 0.0
        }

    face_landmarks = (
        result.multi_face_landmarks[0]
    )

    landmarks = face_landmarks.landmark

    left_eye_points = extract_eye_landmarks(
        image,
        landmarks,
        LEFT_EYE
    )

    right_eye_points = extract_eye_landmarks(
        image,
        landmarks,
        RIGHT_EYE
    )

    left_ear = calculate_eye_aspect_ratio(
        left_eye_points
    )

    right_ear = calculate_eye_aspect_ratio(
        right_eye_points
    )

    average_ear = (
        left_ear +
        right_ear
    ) / 2.0

    return {

        "face_detected": True,

        "left_ear": round(
            left_ear,
            4
        ),

        "right_ear": round(
            right_ear,
            4
        ),

        "average_ear": round(
            average_ear,
            4
        )
    }


# ============================================================
# SINGLE-FRAME BLINK STATE
# ============================================================

def classify_eye_state(average_ear):
    """
    Determine whether the eyes are open or closed.
    """

    if average_ear <= EAR_CLOSED_THRESHOLD:

        return "CLOSED"

    return "OPEN"


# ============================================================
# ACTIVE BLINK STATE MACHINE
# ============================================================

class BlinkDetector:
    """
    Detects the sequence:

        OPEN
          ↓
        CLOSED
          ↓
        OPEN

    That sequence represents one blink.
    """

    def __init__(self):

        self.eye_was_closed = False

        self.closed_frames = 0

        self.blink_detected = False

        self.total_blinks = 0

    def update(self, average_ear):

        if average_ear <= EAR_CLOSED_THRESHOLD:

            self.closed_frames += 1

            if self.closed_frames >= MIN_CLOSED_FRAMES:

                self.eye_was_closed = True

        else:

            if self.eye_was_closed:

                self.blink_detected = True

                self.total_blinks += 1

            self.closed_frames = 0

            self.eye_was_closed = False

        return {

            "blink_detected": self.blink_detected,

            "total_blinks": self.total_blinks,

            "eye_state": (
                "CLOSED"
                if average_ear <= EAR_CLOSED_THRESHOLD
                else "OPEN"
            ),

            "average_ear": round(
                average_ear,
                4
            )
        }


# ============================================================
# CREATE BLINK CHALLENGE
# ============================================================

def create_liveness_challenge():

    return {

        "challenge": "BLINK",

        "instruction": (
            "Please blink naturally once."
        ),

        "required": True,

        "completed": False
    }


# ============================================================
# LEGACY / PASSIVE LIVENESS PROCESSING
# ============================================================

def process_liveness(face):
    """
    Existing liveness processing.

    This keeps the current API working while the
    active blink system is added to the camera flow.
    """

    passive_result = passive_liveness_score(
        face
    )

    if passive_result["decision"] == "REAL":

        return {

            "success": True,

            "liveness_score":
                passive_result["score"],

            "liveness_decision":
                "REAL",

            "challenge_required":
                False,

            "challenge":
                None,

            "details":
                passive_result
        }

    if passive_result["decision"] == "UNCERTAIN":

        challenge = create_liveness_challenge()

        return {

            "success": True,

            "liveness_score":
                passive_result["score"],

            "liveness_decision":
                "UNCERTAIN",

            "challenge_required":
                True,

            "challenge":
                challenge,

            "details":
                passive_result
        }

    return {

        "success": True,

        "liveness_score":
            passive_result["score"],

        "liveness_decision":
            "SPOOF",

        "challenge_required":
            False,

        "challenge":
            None,

        "details":
            passive_result
    }


# ============================================================
# ACTIVE BLINK FRAME PROCESSING
# ============================================================

def process_blink_frame(image, blink_detector):
    """
    Process one camera frame for active blink detection.

    The frontend will eventually send multiple frames
    while the user is performing the blink challenge.
    """

    if image is None or image.size == 0:

        return {

            "success": False,

            "face_detected": False,

            "blink_detected": False,

            "message":
                "Invalid camera frame."
        }

    metrics = calculate_blink_metrics(
        image
    )

    if not metrics["face_detected"]:

        return {

            "success": False,

            "face_detected": False,

            "blink_detected": False,

            "message":
                "Face not detected. Please keep your face visible."
        }

    blink_result = blink_detector.update(
        metrics["average_ear"]
    )

    return {

        "success": True,

        "face_detected": True,

        "blink_detected":
            blink_result["blink_detected"],

        "total_blinks":
            blink_result["total_blinks"],

        "eye_state":
            blink_result["eye_state"],

        "left_ear":
            metrics["left_ear"],

        "right_ear":
            metrics["right_ear"],

        "average_ear":
            metrics["average_ear"],

        "liveness_decision":
            (
                "REAL"
                if blink_result["blink_detected"]
                else "BLINK_REQUIRED"
            ),

        "message":
            (
                "Blink detected successfully."
                if blink_result["blink_detected"]
                else "Please blink naturally once."
            )
    }


# ============================================================
# CREATE A NEW BLINK DETECTOR
# ============================================================

def create_blink_detector():

    return BlinkDetector()