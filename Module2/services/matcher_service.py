import io
import base64
import numpy as np
import cv2
from PIL import Image
import wsq


def match_fingerprint_wsq(wsq_bytes_a, wsq_bytes_b, min_good_matches=15, min_score=0.15):
    """
    Compare two WSQ fingerprint images using OpenCV ORB feature extraction
    and brute-force Hamming matcher with Lowe's ratio test.

    Parameters
    ----------
    wsq_bytes_a : bytes - Raw WSQ byte data of fingerprint A
    wsq_bytes_b : bytes - Raw WSQ byte data of fingerprint B
    min_good_matches : int - Threshold of good keypoint matches
    min_score : float - Threshold of match score relative to keypoints

    Returns
    -------
    (matched: bool, score: float, good_matches_count: int)
    """
    try:
        img_a = np.array(Image.open(io.BytesIO(wsq_bytes_a)).convert("L"))
        img_b = np.array(Image.open(io.BytesIO(wsq_bytes_b)).convert("L"))

        orb = cv2.ORB_create(nfeatures=1000)
        kp_a, des_a = orb.detectAndCompute(img_a, None)
        kp_b, des_b = orb.detectAndCompute(img_b, None)

        if des_a is None or des_b is None or len(des_a) < 10 or len(des_b) < 10:
            return False, 0.0, 0

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        knn_matches = bf.knnMatch(des_a, des_b, k=2)

        # Lowe's ratio test
        good_matches = []
        for pair in knn_matches:
            if len(pair) == 2:
                m, n = pair
                if m.distance < 0.75 * n.distance:
                    good_matches.append(m)

        denominator = min(len(kp_a), len(kp_b))
        if denominator == 0:
            return False, 0.0, 0

        score = len(good_matches) / denominator
        score = min(max(score, 0.0), 1.0)
        matched = (len(good_matches) >= min_good_matches) or (score >= min_score)

        return matched, round(float(score), 4), len(good_matches)

    except Exception as e:
        print(f"[MatcherService] Error matching WSQ fingerprints: {e}")
        return False, 0.0, 0


def match_templates(template_a, template_b, min_good_matches=15, min_score=0.15):
    """
    Compare two fingerprint templates in format:
        <num_fingers>|<fp1_b64>|<fp2_b64>|...

    Cross-compares all fingerprint views present in both templates.

    Parameters
    ----------
    template_a : str - Enrolled template string
    template_b : str - Officer/verification template string

    Returns
    -------
    (matched: bool, best_score: float, details: dict)
    """
    if not template_a or not template_b:
        return False, 0.0, {"error": "One or both templates are empty"}

    parts_a = template_a.split("|")[1:]
    parts_b = template_b.split("|")[1:]

    if not parts_a or not parts_b:
        return False, 0.0, {"error": "Templates do not contain fingerprint data"}

    best_score = 0.0
    matched = False
    best_matches_count = 0

    for idx_a, b64_a in enumerate(parts_a):
        try:
            wsq_bytes_a = base64.b64decode(b64_a)
        except Exception:
            continue

        for idx_b, b64_b in enumerate(parts_b):
            try:
                wsq_bytes_b = base64.b64decode(b64_b)
            except Exception:
                continue

            is_match, score, count = match_fingerprint_wsq(
                wsq_bytes_a,
                wsq_bytes_b,
                min_good_matches=min_good_matches,
                min_score=min_score
            )

            if score > best_score:
                best_score = score
                best_matches_count = count

            if is_match:
                matched = True

    return matched, round(float(best_score), 4), {
        "good_matches": best_matches_count,
        "views_compared": len(parts_a) * len(parts_b)
    }

