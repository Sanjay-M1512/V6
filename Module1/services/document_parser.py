import re
from datetime import datetime


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):
    """Clean OCR text while preserving line structure."""

    if not text:
        return ""

    text = str(text).replace("\r", "\n")

    text = text.replace("—", "-")
    text = text.replace("–", "-")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)

    return text.strip()


def clean_value(value):
    """Clean a general OCR value."""

    if not value:
        return ""

    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def _strip_script_residue(name):
    """
    Remove leading single-letter tokens that are OCR residue
    from Tamil/Hindi script characters.

    e.g. "S MASILAMANI P" -> "MASILAMANI P"
         "B PALANIVEL"    -> "PALANIVEL"
         "Sanjay M"       -> "Sanjay M"  (trailing initial kept)

    Only leading single-letter tokens are stripped since
    Tamil/Hindi residue always appears as a prefix.
    """
    if not name:
        return name

    tokens = name.split()

    if len(tokens) <= 1:
        return name

    # Strip leading single-letter tokens only
    while len(tokens) > 1 and len(tokens[0]) == 1:
        tokens = tokens[1:]

    return " ".join(tokens)


def normalize_name(name):
    """Normalize a person's name."""

    if not name:
        return ""

    name = str(name).strip()

    name = re.sub(
        r"[^A-Za-z .'-]",
        "",
        name
    )

    name = re.sub(
        r"\s+",
        " ",
        name
    )

    name = _strip_script_residue(name.strip())

    return name.strip().upper()


# ============================================================
# DOCUMENT TYPE DETECTION
# ============================================================

def detect_document_type(text):
    """Detect Passport or Aadhaar from OCR text."""

    text = normalize_text(text)
    upper = text.upper()

    passport_keywords = [
        "PASSPORT",
        "REPUBLIC OF INDIA",
        "COUNTRY CODE",
        "PASSPORT NO",
        "PASSPORT NUMBER",
        "SURNAME",
        "GIVEN NAMES",
        "NATIONALITY",
        "PLACE OF BIRTH",
        "PLACE OF ISSUE",
        "DATE OF ISSUE",
        "DATE OF EXPIRY"
    ]

    aadhaar_keywords = [
        "AADHAAR",
        "UIDAI",
        "UNIQUE IDENTIFICATION",
        "YOUR AADHAAR",
        "ENROLMENT",
        "ENROLLMENT",
        "YEAR OF BIRTH"
    ]

    passport_score = sum(
        keyword in upper
        for keyword in passport_keywords
    )

    aadhaar_score = sum(
        keyword in upper
        for keyword in aadhaar_keywords
    )

    if passport_score > aadhaar_score:
        return "passport"

    if aadhaar_score > passport_score:
        return "aadhaar"

    # Additional simple detection
    if re.search(
        r"\bP<IND",
        upper
    ):
        return "passport"

    if re.search(
        r"\b\d{4}[^\S\n]+\d{4}[^\S\n]+\d{4}\b",
        text
    ):
        return "aadhaar"

    return "unknown"


# ============================================================
# DATE FUNCTIONS
# ============================================================

def normalize_date(date_value):
    """
    Convert:

    DD/MM/YYYY
    DD-MM-YYYY
    DD.MM.YYYY

    into:

    YYYY-MM-DD
    """

    if not date_value:
        return ""

    date_value = str(date_value).strip()

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y"
    ]

    for fmt in formats:

        try:

            date = datetime.strptime(
                date_value,
                fmt
            )

            return date.strftime(
                "%Y-%m-%d"
            )

        except ValueError:
            continue

    return ""


def extract_dates(text):
    """Extract normal dates from OCR text."""

    if not text:
        return []

    return re.findall(
        r"\b\d{2}[\/\-.]\d{2}[\/\-.]\d{4}\b",
        text
    )


# ============================================================
# PASSPORT MRZ
# ============================================================

def clean_mrz_line(line):
    """Clean an OCR line for MRZ processing."""

    if not line:
        return ""

    line = str(line).upper()

    line = re.sub(
        r"\s+",
        "",
        line
    )

    line = re.sub(
        r"[^A-Z0-9<]",
        "",
        line
    )

    return line


def find_mrz_lines(text):
    """
    Find the two Passport MRZ lines.
    """

    if not text:
        return None, None

    lines = text.splitlines()

    candidates = []

    for line in lines:

        cleaned = clean_mrz_line(
            line
        )

        if len(cleaned) >= 30:
            candidates.append(
                cleaned
            )

    # Normal case
    for i in range(
        len(candidates)
    ):

        first = candidates[i]

        if first.startswith("P"):

            if i + 1 < len(candidates):

                second = candidates[
                    i + 1
                ]

                if len(second) >= 27:

                    return first, second

    # Sometimes OCR returns both MRZ
    # lines without correctly preserving
    # the first character.
    if len(candidates) >= 2:

        return (
            candidates[-2],
            candidates[-1]
        )

    return None, None


def parse_mrz_name(line1):
    """
    Extract surname and given names from MRZ line 1.

    Example:

    P<INDPALANIVEL<<MASILAMANI
    """

    if not line1:
        return "", ""

    # Standard TD3 passport MRZ:
    # positions:
    # 0      P
    # 1      <
    # 2-4    country
    # 5+     name

    if len(line1) > 5:
        name_part = line1[5:]
    else:
        name_part = line1

    parts = name_part.split(
        "<<",
        1
    )

    if len(parts) != 2:
        return "", ""

    surname_raw = parts[0]
    given_raw = parts[1]

    def clean_mrz_name_segment(value):

        if not value:
            return ""

        tokens = []

        # Characters that OCR commonly produces
        # when misreading MRZ '<' filler
        FILLER_CHARS = set("KSXEI")

        for token in value.split("<"):

            token = re.sub(
                r"[^A-Z]",
                "",
                token
            )

            if not token:
                continue

            # Strip trailing filler characters only when 2+ consecutive
            # e.g. "MASILAMANIKSSSS" -> "MASILAMANI"
            # but "MASILAMANI" stays (single trailing I is part of name)
            token = re.sub(
                r"[KSXEI]{2,}$",
                "",
                token
            )

            if not token:
                continue

            # Skip tokens made entirely of
            # filler characters
            if all(
                ch in FILLER_CHARS
                for ch in token
            ):
                continue

            # Skip tokens where most characters
            # are filler (>50% filler = garbage)
            filler_count = sum(
                1 for ch in token
                if ch in FILLER_CHARS
            )

            if (
                len(token) >= 3
                and filler_count / len(token) > 0.5
            ):
                continue

            # Skip single-character filler letters
            if (
                len(token) == 1
                and token in FILLER_CHARS
            ):
                continue

            tokens.append(token)

        return " ".join(tokens)

    surname = clean_mrz_name_segment(
        surname_raw
    )

    given_name = clean_mrz_name_segment(
        given_raw
    )

    return (
        normalize_name(surname),
        normalize_name(given_name)
    )


def convert_mrz_date(value):
    """
    Convert YYMMDD into YYYY-MM-DD.
    """

    if not re.fullmatch(
        r"\d{6}",
        value or ""
    ):
        return ""

    try:

        yy = int(value[:2])
        month = int(value[2:4])
        day = int(value[4:6])

        current_year = (
            datetime.now().year % 100
        )

        if yy <= current_year:
            year = 2000 + yy
        else:
            year = 1900 + yy

        date = datetime(
            year,
            month,
            day
        )

        return date.strftime(
            "%Y-%m-%d"
        )

    except ValueError:
        return ""


def parse_mrz_text(mrz_text):
    """
    Parse dedicated MRZ OCR result.

    TD3 Passport MRZ:

    Line 1:
        P<COUNTRYSURNAME<<GIVENNAME

    Line 2:
        PASSPORTNUMBER<CHECK
        NATIONALITY
        DOB
        CHECK
        SEX
        EXPIRY
    """

    if not mrz_text:
        return {}

    line1, line2 = find_mrz_lines(
        mrz_text
    )

    if not line1 or not line2:
        return {}

    if len(line2) < 27:
        return {}

    # Passport type
    passport_type = "P"

    if line1:
        if line1[0] in [
            "P",
            "V",
            "I",
            "A",
            "C"
        ]:
            passport_type = line1[0]

    # Name
    surname, given_name = parse_mrz_name(
        line1
    )

    # Passport number
    passport_number = (
        line2[0:9]
        .replace("<", "")
    )

    # Remove obvious OCR garbage
    passport_number = re.sub(
        r"[^A-Z0-9]",
        "",
        passport_number
    )

    # Nationality
    raw_nationality = line2[10:13]

    # Common OCR corrections
    translation = str.maketrans(
        {
            "0": "O",
            "1": "I",
            "2": "Z",
            "5": "S",
            "8": "B"
        }
    )

    nationality = (
        raw_nationality
        .translate(translation)
    )

    nationality = re.sub(
        r"[^A-Z]",
        "",
        nationality
    )

    # Date of birth
    dob_raw = line2[13:19]

    # Sex
    sex = line2[20:21]

    if sex not in ["M", "F", "<"]:
        sex = ""

    # Expiry
    expiry_raw = line2[21:27]

    return {

        "passport_type":
            passport_type,

        "passport_number":
            passport_number,

        "nationality":
            nationality,

        "date_of_birth":
            convert_mrz_date(
                dob_raw
            ),

        "sex":
            sex,

        "date_of_expiry":
            convert_mrz_date(
                expiry_raw
            ),

        "surname":
            surname,

        "given_name":
            given_name,

        "mrz":
            line1 + "\n" + line2
    }


# ============================================================
# PASSPORT FIELD EXTRACTION
# ============================================================

def extract_passport_number(text):
    """Extract Passport number from OCR text."""

    if not text:
        return ""

    patterns = [

        r"PASSPORT\s*NO\.?\s*[:\-]?\s*([A-Z]\d{7})",

        r"PASSPORT\s*NUMBER\s*[:\-]?\s*([A-Z0-9]{6,9})",

        r"PASSPORT\s*NO\s*[:\-]?\s*([A-Z0-9]{6,9})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(
                1
            ).upper()

    return ""


def extract_passport_date(
    text,
    labels
):
    """Extract a date after a specific label."""

    if not text:
        return ""

    labels_pattern = "|".join(
        re.escape(label)
        for label in labels
    )

    pattern = (
        r"(?:"
        + labels_pattern
        + r")"
        r"\s*[:.]?\s*"
        r"(\d{2}[\/\-.]\d{2}[\/\-.]\d{4})"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if match:

        return normalize_date(
            match.group(1)
        )

    return ""


def extract_passport_sex(text):
    """Extract M/F after Sex."""

    if not text:
        return ""

    patterns = [

        r"\bSEX\s*[:.]?\s*(M|F)\b",

        r"\bSEX\b[^\n]*\b(M|F)\b"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(
                1
            ).upper()

    return ""


def extract_passport_nationality(text):
    """Extract passport nationality."""

    if not text:
        return ""

    match = re.search(
        r"\bNATIONALITY\s*[:.]?\s*"
        r"(INDIAN|IND)\b",
        text,
        re.IGNORECASE
    )

    if not match:
        return ""

    value = match.group(
        1
    ).upper()

    if value == "IND":
        return "INDIAN"

    return value


def extract_labeled_value(
    text,
    label,
    next_labels=None
):
    """Extract value following a label."""

    if not text:
        return ""

    if next_labels is None:
        next_labels = []

    # First try line-based extraction.
    lines = text.splitlines()

    label_pattern = re.compile(
        r"\b"
        + re.escape(label)
        + r"\b"
        r"\s*[:.]?\s*(.*)",
        re.IGNORECASE
    )

    for i, line in enumerate(lines):

        match = label_pattern.search(
            line
        )

        if not match:
            continue

        value = match.group(1).strip()

        if value:
            return clean_value(
                value
            )

        # Value may be on next line.
        if i + 1 < len(lines):

            next_line = (
                lines[i + 1].strip()
            )

            if next_line:

                blocked = any(
                    re.search(
                        r"\b"
                        + re.escape(next_label)
                        + r"\b",
                        next_line,
                        re.IGNORECASE
                    )
                    for next_label in next_labels
                )

                if not blocked:

                    return clean_value(
                        next_line
                    )

    # Fallback to regex across text.
    if next_labels:

        stop_pattern = "|".join(
            re.escape(label)
            for label in next_labels
        )

        pattern = (
            r"\b"
            + re.escape(label)
            + r"\b"
            r"\s*[:.]?\s*"
            r"(.+?)"
            r"(?=\b(?:"
            + stop_pattern
            + r")\b|$)"
        )

    else:

        pattern = (
            r"\b"
            + re.escape(label)
            + r"\b"
            r"\s*[:.]?\s*(.+)"
        )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:
        return ""

    return clean_value(
        match.group(1)
    )


def extract_passport_place(
    text,
    label
):
    """Extract passport place field."""

    next_labels = [
        "PLACE OF BIRTH",
        "PLACE OF ISSUE",
        "DATE OF ISSUE",
        "DATE OF EXPIRY",
        "NATIONALITY",
        "SEX"
    ]

    value = extract_labeled_value(
        text,
        label,
        next_labels
    )

    return value.upper()


# ============================================================
# PASSPORT VISUAL INSPECTION ZONE
# ============================================================

def extract_passport_visual_fields(text):
    """
    Extract fields from the visual inspection zone.

    This is a fallback when MRZ/general OCR
    does not provide a usable value.
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    fields = {}

    # --------------------------------------------------------
    # SURNAME
    # --------------------------------------------------------

    for i, line in enumerate(lines):

        if re.search(
            r"\bSURNAME\b",
            line,
            re.IGNORECASE
        ):

            for next_line in lines[
                i + 1:i + 4
            ]:

                cleaned = re.sub(
                    r"[^A-Za-z\s]",
                    "",
                    next_line
                ).strip()

                if not cleaned:
                    continue

                if re.search(
                    r"\b("
                    r"GIVEN|NAMES?|"
                    r"NATIONALITY|SEX|DATE|"
                    r"REPUBLIC|INDIA|PLACE|"
                    r"PASSPORT|TYPE|COUNTRY"
                    r")\b",
                    cleaned,
                    re.IGNORECASE
                ):
                    continue

                fields["surname"] = (
                    normalize_name(
                        cleaned
                    )
                )

                break

            break

    # --------------------------------------------------------
    # GIVEN NAMES
    # --------------------------------------------------------

    for i, line in enumerate(lines):

        if re.search(
            r"\bGIVEN\s*NAMES?\b",
            line,
            re.IGNORECASE
        ):

            for next_line in lines[
                i + 1:i + 4
            ]:

                cleaned = re.sub(
                    r"[^A-Za-z\s]",
                    "",
                    next_line
                ).strip()

                if not cleaned:
                    continue

                if re.search(
                    r"\b("
                    r"SURNAME|NATIONALITY|SEX|"
                    r"DATE|REPUBLIC|INDIA|"
                    r"PLACE|PASSPORT|TYPE|COUNTRY"
                    r")\b",
                    cleaned,
                    re.IGNORECASE
                ):
                    continue

                fields["given_name"] = (
                    normalize_name(
                        cleaned
                    )
                )

                break

            break

    # --------------------------------------------------------
    # PLACE OF BIRTH
    # --------------------------------------------------------

    for i, line in enumerate(lines):

        if re.search(
            r"\bPLACE\s*OF\s*BIRTH\b",
            line,
            re.IGNORECASE
        ):

            for next_line in lines[
                i + 1:i + 3
            ]:

                cleaned = re.sub(
                    r"[^A-Za-z,\s]",
                    "",
                    next_line
                ).strip()

                if not cleaned:
                    continue

                if re.search(
                    r"\b("
                    r"PLACE|ISSUE|DATE|EXPIRY|"
                    r"SEX|NATIONALITY"
                    r")\b",
                    cleaned,
                    re.IGNORECASE
                ):
                    continue

                fields["place_of_birth"] = (
                    cleaned.upper()
                )

                break

            break

    # --------------------------------------------------------
    # PLACE OF ISSUE
    # --------------------------------------------------------

    for i, line in enumerate(lines):

        if re.search(
            r"\bPLACE\s*OF\s*ISSUE\b",
            line,
            re.IGNORECASE
        ):

            for next_line in lines[
                i + 1:i + 3
            ]:

                cleaned = re.sub(
                    r"[^A-Za-z,\s]",
                    "",
                    next_line
                ).strip()

                if not cleaned:
                    continue

                if re.search(
                    r"\b("
                    r"PLACE|BIRTH|DATE|EXPIRY|"
                    r"SEX|NATIONALITY"
                    r")\b",
                    cleaned,
                    re.IGNORECASE
                ):
                    continue

                fields["place_of_issue"] = (
                    cleaned.upper()
                )

                break

            break

    # --------------------------------------------------------
    # DATES
    # --------------------------------------------------------

    for i, line in enumerate(lines):

        if re.search(
            r"\bDATE\s*OF\s*ISSUE\b",
            line,
            re.IGNORECASE
        ):

            search_text = " ".join(
                lines[i:i + 4]
            )

            found_dates = re.findall(
                r"\b\d{2}[\/\-.]\d{2}[\/\-.]\d{4}\b",
                search_text
            )

            if len(found_dates) >= 1:

                fields["date_of_issue"] = (
                    normalize_date(
                        found_dates[0]
                    )
                )

            if len(found_dates) >= 2:

                fields["date_of_expiry"] = (
                    normalize_date(
                        found_dates[1]
                    )
                )

            break

    # --------------------------------------------------------
    # NATIONALITY
    # --------------------------------------------------------

    if re.search(
        r"\b(INDIAN|IND)\b",
        text,
        re.IGNORECASE
    ):

        fields["nationality"] = "IND"

    # --------------------------------------------------------
    # SEX
    # --------------------------------------------------------

    sex_match = re.search(
        r"\b(?:SEX)\b[^\n]*\b([MFX])\b",
        text,
        re.IGNORECASE
    )

    if sex_match:

        fields["sex"] = (
            sex_match.group(1).upper()
        )

    return fields


# ============================================================
# PASSPORT PARSER
# ============================================================

def parse_passport(
    general_text,
    mrz_text=""
):
    """
    Parse Passport using:

    1. General OCR
    2. Visual Inspection Zone
    3. Dedicated MRZ OCR

    MRZ is preferred for:

    - Passport number
    - Nationality
    - DOB
    - Sex
    - Expiry
    - Name
    """

    general_text = normalize_text(
        general_text
    )

    mrz_text = normalize_text(
        mrz_text
    )

    fields = {

        "passport_type": "",

        "country_code": "",

        "passport_number": "",

        "surname": "",

        "given_name": "",

        "nationality": "",

        "sex": "",

        "date_of_birth": "",

        "place_of_birth": "",

        "place_of_issue": "",

        "date_of_issue": "",

        "date_of_expiry": "",

        "mrz": "",

        "signature": ""
    }

    # ========================================================
    # VISUAL FIELDS
    # ========================================================

    viz_fields = (
        extract_passport_visual_fields(
            general_text
        )
    )

    # ========================================================
    # PASSPORT TYPE
    # ========================================================

    if re.search(
        r"\bTYPE\s*[:.]?\s*P\b",
        general_text,
        re.IGNORECASE
    ):

        fields["passport_type"] = "P"

    # ========================================================
    # COUNTRY CODE
    # ========================================================

    if (
        re.search(
            r"\bIND\b",
            general_text.upper()
        )
        or "IND" in mrz_text.upper()
    ):

        fields["country_code"] = "IND"

    # ========================================================
    # MRZ
    # ========================================================

    mrz_data = parse_mrz_text(
        mrz_text
    )

    # ========================================================
    # MRZ VALUES FIRST
    # ========================================================

    if mrz_data:

        for key in [
            "passport_type",
            "passport_number",
            "nationality",
            "date_of_birth",
            "sex",
            "date_of_expiry",
            "surname",
            "given_name",
            "mrz"
        ]:

            value = mrz_data.get(
                key,
                ""
            )

            if value:
                fields[key] = value

    # ========================================================
    # PASSPORT TYPE FALLBACK
    # ========================================================

    if not fields["passport_type"]:

        if re.search(
            r"\bTYPE\s*[:.]?\s*P\b",
            general_text,
            re.IGNORECASE
        ):

            fields["passport_type"] = "P"

        elif mrz_data.get(
            "passport_type"
        ):

            fields["passport_type"] = (
                mrz_data[
                    "passport_type"
                ]
            )

    # ========================================================
    # COUNTRY CODE FALLBACK
    # ========================================================

    if not fields["country_code"]:

        if "IND" in mrz_text.upper():

            fields["country_code"] = "IND"

        elif re.search(
            r"\bIND\b",
            general_text.upper()
        ):

            fields["country_code"] = "IND"

    # ========================================================
    # PASSPORT NUMBER FALLBACK
    # ========================================================

    if not fields["passport_number"]:

        fields["passport_number"] = (
            extract_passport_number(
                general_text
            )
        )

    # ========================================================
    # SURNAME FALLBACK
    # ========================================================

    if not fields["surname"]:

        if viz_fields.get(
            "surname"
        ):

            fields["surname"] = (
                viz_fields["surname"]
            )

        else:

            surname = extract_labeled_value(
                general_text,
                "SURNAME",
                [
                    "GIVEN NAMES",
                    "GIVEN NAME",
                    "NATIONALITY"
                ]
            )

            fields["surname"] = (
                normalize_name(
                    surname
                )
            )

    # ========================================================
    # GIVEN NAME FALLBACK
    # ========================================================

    if not fields["given_name"]:

        if viz_fields.get(
            "given_name"
        ):

            fields["given_name"] = (
                viz_fields["given_name"]
            )

        else:

            given_name = (
                extract_labeled_value(
                    general_text,
                    "GIVEN NAMES",
                    [
                        "NATIONALITY",
                        "SEX",
                        "DATE OF BIRTH"
                    ]
                )
            )

            fields["given_name"] = (
                normalize_name(
                    given_name
                )
            )

    # ========================================================
    # NATIONALITY FALLBACK
    # ========================================================

    if not fields["nationality"]:

        fields["nationality"] = (
            extract_passport_nationality(
                general_text
            )
        )

    # Normalize IND -> INDIAN
    if fields["nationality"] == "IND":

        fields["nationality"] = "INDIAN"

    # ========================================================
    # SEX FALLBACK
    # ========================================================

    if not fields["sex"]:

        if viz_fields.get(
            "sex"
        ):

            fields["sex"] = (
                viz_fields["sex"]
            )

        else:

            fields["sex"] = (
                extract_passport_sex(
                    general_text
                )
            )

    # ========================================================
    # DATE OF BIRTH FALLBACK
    # ========================================================

    if not fields["date_of_birth"]:

        fields["date_of_birth"] = (
            extract_passport_date(
                general_text,
                [
                    "DATE OF BIRTH"
                ]
            )
        )

    # ========================================================
    # DATE OF ISSUE
    # ========================================================

    if viz_fields.get(
        "date_of_issue"
    ):

        fields["date_of_issue"] = (
            viz_fields[
                "date_of_issue"
            ]
        )

    else:

        fields["date_of_issue"] = (
            extract_passport_date(
                general_text,
                [
                    "DATE OF ISSUE"
                ]
            )
        )

    # ========================================================
    # DATE OF EXPIRY FALLBACK
    # ========================================================

    if not fields["date_of_expiry"]:

        if viz_fields.get(
            "date_of_expiry"
        ):

            fields["date_of_expiry"] = (
                viz_fields[
                    "date_of_expiry"
                ]
            )

        else:

            fields["date_of_expiry"] = (
                extract_passport_date(
                    general_text,
                    [
                        "DATE OF EXPIRY"
                    ]
                )
            )

    # ========================================================
    # PLACE OF BIRTH
    # ========================================================

    if viz_fields.get(
        "place_of_birth"
    ):

        fields["place_of_birth"] = (
            viz_fields[
                "place_of_birth"
            ]
        )

    else:

        fields["place_of_birth"] = (
            extract_passport_place(
                general_text,
                "PLACE OF BIRTH"
            )
        )

    # ========================================================
    # PLACE OF ISSUE
    # ========================================================

    if viz_fields.get(
        "place_of_issue"
    ):

        fields["place_of_issue"] = (
            viz_fields[
                "place_of_issue"
            ]
        )

    else:

        fields["place_of_issue"] = (
            extract_passport_place(
                general_text,
                "PLACE OF ISSUE"
            )
        )

    return fields


# ============================================================
# AADHAAR EXTRACTION
# ============================================================

def extract_aadhaar_number(text):
    """Extract 12-digit Aadhaar number."""

    if not text:
        return ""

    # Build a set of positions to skip - digits that are
    # part of a VID line (VID is 16 digits, first 12 would
    # otherwise look like an Aadhaar number)
    vid_ranges = set()
    for m in re.finditer(
        r"\bVID\s*[:\-]?\s*(?:\d{4}\s*){4}",
        text,
        re.IGNORECASE
    ):
        for i in range(m.start(), m.end()):
            vid_ranges.add(i)

    patterns = [

        r"\b\d{4}[^\S\n]+\d{4}[^\S\n]+\d{4}\b",

        r"\b\d{12}\b"
    ]

    for pattern in patterns:

        for m in re.finditer(pattern, text):

            # Skip if this match overlaps a VID line
            if any(i in vid_ranges for i in range(m.start(), m.end())):
                continue

            number = re.sub(r"\D", "", m.group())

            if len(number) == 12:
                return number

    return ""


def extract_mobile_number(text):
    """Extract Indian mobile number."""

    if not text:
        return ""

    matches = re.findall(
        r"\b[6-9]\d{9}\b",
        text
    )

    if matches:

        return matches[0]

    return ""


def extract_aadhaar_gender(text):
    """Extract Aadhaar gender."""

    if not text:
        return ""

    upper = text.upper()

    if re.search(
        r"\bFEMALE\b",
        upper
    ):

        return "FEMALE"

    if re.search(
        r"\bMALE\b",
        upper
    ):

        return "MALE"

    return ""


def extract_aadhaar_dob(text):
    """Extract Aadhaar DOB."""

    if not text:
        return ""

    match = re.search(
        r"(?:DOB|DATE OF BIRTH)"
        r"\s*[:\-]?\s*"
        r"(\d{2}[\/\-.]\d{2}[\/\-.]\d{4})",
        text,
        re.IGNORECASE
    )

    if match:

        return normalize_date(
            match.group(1)
        )

    dates = extract_dates(
        text
    )

    if dates:

        return normalize_date(
            dates[0]
        )

    return ""


def _is_likely_ocr_garbage(text):
    """
    Detect if a text line is likely OCR garbage
    from non-Latin scripts (e.g. Tamil).

    OCR garbage from Tamil/Hindi typically has:
    - No English vowels
    - Very short meaningless words
    - Too many consonant clusters
    """

    if not text:
        return True

    cleaned = re.sub(
        r"[^A-Za-z]",
        "",
        text
    )

    if len(cleaned) < 2:
        return True

    # Check for English vowels
    vowels = set("AEIOUaeiou")

    vowel_count = sum(
        1 for ch in cleaned
        if ch in vowels
    )

    # Real English names always have vowels
    # e.g. "FCHFW LOT" has only 1 vowel in 8 chars
    if len(cleaned) >= 4 and vowel_count == 0:
        return True

    # Very low vowel ratio suggests garbage
    vowel_ratio = vowel_count / len(cleaned)

    if (
        len(cleaned) >= 5
        and vowel_ratio < 0.15
    ):
        return True

    # Check each word individually - catches "FCHFW LOT" style garbage
    # where individual long words have no vowels
    _words = [w for w in re.findall(r"[A-Za-z]+", text) if len(w) >= 4]
    if _words:
        _garbage = sum(
            1 for w in _words
            if sum(1 for c in w if c in vowels) == 0
            or sum(1 for c in w if c in vowels) / len(w) < 0.15
        )
        if _garbage > len(_words) / 2:
            return True

    # Check for impossible consonant clusters
    # (3+ consonants in a row is rare in names)
    consonant_run = re.search(
        r"[^AEIOUaeiou]{4,}",
        cleaned
    )

    if consonant_run:
        # Allow common patterns like "SHRI", "CHDR"
        run = consonant_run.group()
        if len(run) >= 5:
            return True

    return False


def _is_valid_name_candidate(text):
    """
    Check if text looks like a valid person name.
    """

    if not text or len(text.strip()) < 2:
        return False

    cleaned = re.sub(
        r"[^A-Za-z .'-]",
        "",
        text
    ).strip()

    if len(cleaned) < 2:
        return False

    # Must have at least one vowel
    if not re.search(r"[AEIOUaeiou]", cleaned):
        return False

    # Must start with a letter
    if not re.match(r"[A-Za-z]", cleaned):
        return False

    # Must not be common non-name keywords
    upper = cleaned.upper().strip()

    skip_words = {
        "TO", "INDIA", "GOVERNMENT",
        "AADHAAR", "UIDAI", "MALE", "FEMALE",
        "UNIQUE", "IDENTIFICATION", "AUTHORITY",
        "ENROLMENT", "ENROLLMENT", "VID",
        "PROOF", "IDENTITY", "CITIZENSHIP",
        "MOBILE", "PIN", "CODE", "STATE",
        "DISTRICT", "TAMIL", "NADU",
        "YOUR", "NO", "DATE", "BIRTH",
        "ADDRESS", "STREET", "NAGAR",
    }

    if upper in skip_words:
        return False

    # Check it's not garbage
    if _is_likely_ocr_garbage(cleaned):
        return False

    return True


def extract_aadhaar_name(text):
    """
    Extract Aadhaar name from OCR text.

    Handles:
    - Tamil/Hindi OCR garbage filtering
    - Name after 'To' label
    - Name from compact back section (near DOB)
    - Name from S/O, D/O, W/O lines
    """

    if not text:
        return ""

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # ========================================================
    # COMPACT BACK SECTION
    # ========================================================
    # The Aadhaar back/bottom has format like:
    #   Sanjay M
    #   DOB: 15/12/2005
    #   MALE
    # Look for a name line right before "DOB" or
    # on the same line containing DOB.

    for i, line in enumerate(lines):

        # Check for DOB line
        dob_match = re.search(
            r"\bDOB\s*[:/]\s*\d{2}[/\-.]",
            line,
            re.IGNORECASE
        )

        if dob_match:

            # Extract name from same line if present
            # e.g. "Sanjay M DOB: 15/12/2005"
            before_dob = line[
                :dob_match.start()
            ].strip()

            # Remove Tamil/Hindi prefix
            before_dob = re.sub(
                r"[^\x20-\x7E]+",
                "",
                before_dob
            ).strip()

            if _is_valid_name_candidate(
                before_dob
            ):
                return normalize_name(
                    before_dob
                )

            # Check the line above DOB for name
            if i > 0:

                prev_line = re.sub(
                    r"[^\x20-\x7E]+",
                    "",
                    lines[i - 1]
                ).strip()

                if _is_valid_name_candidate(
                    prev_line
                ):
                    return normalize_name(
                        prev_line
                    )

    # ========================================================
    # SEARCH AFTER "TO"
    # ========================================================

    for i, line in enumerate(lines):

        if line.upper().strip() == "TO":

            candidates = lines[
                i + 1:i + 8
            ]

            for candidate in candidates:

                upper = candidate.upper()

                # Skip S/O, D/O, W/O lines
                if (
                    "S/O" in upper
                    or "D/O" in upper
                    or "W/O" in upper
                ):
                    continue

                # Skip document keywords
                if (
                    "AADHAAR" in upper
                    or "GOVERNMENT" in upper
                    or upper == "INDIA"
                    or "ENROLMENT" in upper
                    or "UNIQUE" in upper
                    or "IDENTIFICATION" in upper
                ):
                    continue

                # Skip address-like lines
                if re.search(
                    r"\b(STREET|NAGAR|VTC|"
                    r"DISTRICT|STATE|PIN|"
                    r"MOBILE|PO:|NO\s+\d)",
                    upper
                ):
                    continue

                # Strip non-ASCII characters
                # (Tamil/Hindi remnants)
                ascii_only = re.sub(
                    r"[^\x20-\x7E]",
                    "",
                    candidate
                ).strip()

                if not ascii_only:
                    continue

                # Check if it's a valid name
                if _is_valid_name_candidate(
                    ascii_only
                ):
                    return normalize_name(
                        ascii_only
                    )

            break

    # ========================================================
    # NAME LABEL
    # ========================================================

    match = re.search(
        r"\bNAME\s*[:\-]\s*"
        r"([A-Za-z][A-Za-z .'-]+)",
        text,
        re.IGNORECASE
    )

    if match:

        name = match.group(1).strip()

        if _is_valid_name_candidate(name):

            return normalize_name(name)

    # ========================================================
    # S/O LINE NAME EXTRACTION
    # ========================================================

    for i, line in enumerate(lines):

        if re.search(
            r"\b(S/O|D/O|W/O)\b",
            line,
            re.IGNORECASE
        ):

            # Try name from the line before S/O
            if i > 0:

                prev_line = re.sub(
                    r"[^\x20-\x7E]",
                    "",
                    lines[i - 1]
                ).strip()

                if _is_valid_name_candidate(
                    prev_line
                ):
                    return normalize_name(
                        prev_line
                    )

            # Try name from beginning of S/O line
            possible_name = re.split(
                r"\b(S/O|D/O|W/O)\b",
                line,
                flags=re.IGNORECASE
            )[0].strip()

            possible_name = re.sub(
                r"[^\x20-\x7E]",
                "",
                possible_name
            ).strip()

            if _is_valid_name_candidate(
                possible_name
            ):
                return normalize_name(
                    possible_name
                )

            break

    return ""


def extract_aadhaar_address(text):
    """Extract basic Aadhaar address."""

    if not text:
        return ""

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    start = -1

    # Search for S/O, D/O or W/O
    for i, line in enumerate(lines):

        if re.search(
            r"\b(S/O|D/O|W/O)\b",
            line,
            re.IGNORECASE
        ):

            start = i
            break

    if start == -1:
        return ""

    address_lines = []

    for line in lines[start:]:

        upper = line.upper()

        if (
            "AADHAAR" in upper
            or "MOBILE" in upper
            or "WWW." in upper
        ):
            break

        address_lines.append(
            line
        )

    return ", ".join(
        address_lines
    )


# ============================================================
# AADHAAR PARSER
# ============================================================

def parse_aadhaar(
    general_text,
    aadhaar_text=""
):
    """
    Parse Aadhaar using:

    - General OCR
    - Aadhaar-focused OCR
    """

    general_text = normalize_text(
        general_text
    )

    aadhaar_text = normalize_text(
        aadhaar_text
    )

    # Prefer focused OCR first.
    if aadhaar_text:

        combined_text = (
            aadhaar_text
            + "\n"
            + general_text
        )

    else:

        combined_text = general_text

    fields = {

        "name": "",

        "date_of_birth": "",

        "gender": "",

        "aadhaar_number": "",

        "mobile_number": "",

        "address": ""
    }

    # ========================================================
    # AADHAAR NUMBER
    # ========================================================

    fields["aadhaar_number"] = (
        extract_aadhaar_number(
            combined_text
        )
    )

    # ========================================================
    # MOBILE
    # ========================================================

    fields["mobile_number"] = (
        extract_mobile_number(
            combined_text
        )
    )

    # ========================================================
    # GENDER
    # ========================================================

    fields["gender"] = (
        extract_aadhaar_gender(
            combined_text
        )
    )

    # ========================================================
    # DOB
    # ========================================================

    fields["date_of_birth"] = (
        extract_aadhaar_dob(
            combined_text
        )
    )

    # ========================================================
    # NAME
    # ========================================================

    fields["name"] = (
        extract_aadhaar_name(
            combined_text
        )
    )

    # ========================================================
    # ADDRESS
    # ========================================================

    fields["address"] = (
        extract_aadhaar_address(
            combined_text
        )
    )

    return fields


# ============================================================
# MAIN DOCUMENT PARSER
# ============================================================

def parse_document(
    ocr_result
):
    """
    Main parser.

    Accepts the complete OCR result
    from ocr_service.py.
    """

    # ========================================================
    # STRING INPUT SUPPORT
    # ========================================================

    if isinstance(
        ocr_result,
        str
    ):

        general_text = ocr_result

        mrz_text = ""

        aadhaar_text = ""

    # ========================================================
    # DICTIONARY INPUT
    # ========================================================

    else:

        general = ocr_result.get(
            "general",
            {}
        )

        mrz = ocr_result.get(
            "mrz",
            {}
        )

        aadhaar = ocr_result.get(
            "aadhaar",
            {}
        )

        general_text = general.get(
            "text",
            ""
        )

        mrz_text = mrz.get(
            "text",
            ""
        )

        aadhaar_text = aadhaar.get(
            "text",
            ""
        )

        # Fallback to combined OCR
        if not general_text:

            general_text = (
                ocr_result.get(
                    "text",
                    ""
                )
            )

    # ========================================================
    # DOCUMENT TYPE
    # ========================================================

    document_type = detect_document_type(
        general_text
    )

    # If general OCR failed to detect Passport,
    # check MRZ separately.
    if (
        document_type == "unknown"
        and mrz_text
    ):

        if re.search(
            r"\bP",
            mrz_text.upper()
        ):

            document_type = "passport"

    # ========================================================
    # PASSPORT
    # ========================================================

    if document_type == "passport":

        fields = parse_passport(
            general_text,
            mrz_text
        )

    # ========================================================
    # AADHAAR
    # ========================================================

    elif document_type == "aadhaar":

        fields = parse_aadhaar(
            general_text,
            aadhaar_text
        )

    # ========================================================
    # UNKNOWN
    # ========================================================

    else:

        fields = {}

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "document_type":
            document_type,

        "fields":
            fields
    }