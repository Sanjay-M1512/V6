import base64


# ============================================================
# HELPERS
# ============================================================

def _read_uint(data, start, length):
    return int.from_bytes(data[start:start + length], "big")


# ============================================================
# FIRPIV PARSER
# ============================================================

def parse_firpiv(file_bytes):
    """
    Parse a FIRPIV binary file (ISO/IEC 19794-4 FIR format).

    Returns a list of dicts, one per fingerprint:
        {
            "finger_position": int,
            "view_number":     int,
            "quality":         int,
            "impression_type": int,
            "width":           int,
            "height":          int,
            "wsq_b64":         str   # base64-encoded WSQ image data
        }

    Raises ValueError if the file is not a valid FIRPIV.
    """

    fir_pos = file_bytes.find(b"FIR\x00")

    if fir_pos == -1:
        raise ValueError(
            "FIR header not found — not a valid FIRPIV file"
        )

    number_of_fingerprints = file_bytes[fir_pos + 22]
    compression            = file_bytes[fir_pos + 33]

    if compression != 2:
        raise ValueError(
            f"Unsupported compression algorithm: {compression} "
            f"(expected 2 = WSQ)"
        )

    position = fir_pos + 36   # skip 36-byte general header

    fingerprints = []

    for _ in range(number_of_fingerprints):

        block_length     = _read_uint(file_bytes, position, 4)
        finger_position  = file_bytes[position + 4]
        view_number      = file_bytes[position + 5]
        quality          = file_bytes[position + 7]
        impression_type  = file_bytes[position + 8]
        width            = _read_uint(file_bytes, position + 9,  2)
        height           = _read_uint(file_bytes, position + 11, 2)

        image_start = position + 14
        image_end   = position + block_length

        wsq_data = file_bytes[image_start:image_end]

        fingerprints.append({
            "finger_position":  finger_position,
            "view_number":      view_number,
            "quality":          quality,
            "impression_type":  impression_type,
            "width":            width,
            "height":           height,
            "wsq_b64":          base64.b64encode(wsq_data).decode("utf-8")
        })

        position = image_end

    return fingerprints


def extract_fingerprint_template(file_bytes):
    """
    Parse a FIRPIV file and return a compact template string
    suitable for storing in Firebase.

    Format:
        <num_fingers>|<fp1_b64>|<fp2_b64>|...

    Raises ValueError on invalid file.
    """

    fingerprints = parse_firpiv(file_bytes)

    if not fingerprints:
        raise ValueError("No fingerprints found in FIRPIV file")

    parts = [str(len(fingerprints))]

    for fp in fingerprints:
        parts.append(fp["wsq_b64"])

    return "|".join(parts)
