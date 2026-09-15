import re
from datetime import datetime


# ============================================================
# GENERIC VALIDATION FUNCTIONS
# ============================================================

def is_valid_date(date_value):
    """
    Validate dates in:

        YYYY-MM-DD
        DD/MM/YYYY
        DD-MM-YYYY
        DD.MM.YYYY
        YYYY
    """

    if not date_value:
        return False

    date_value = str(date_value).strip()

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%Y"
    ]

    for fmt in formats:

        try:

            datetime.strptime(
                date_value,
                fmt
            )

            return True

        except ValueError:

            continue

    return False


def is_valid_name(name):
    """
    Validate a person's name.
    """

    if not name:
        return False

    name = str(name).strip()

    if len(name) < 2:
        return False

    return bool(
        re.fullmatch(
            r"[A-Za-z][A-Za-z .'-]*",
            name
        )
    )


# ============================================================
# PASSPORT VALIDATION
# ============================================================

def validate_passport(fields):
    """
    Validate extracted Passport fields.

    This validates FORMAT and presence only.
    It does not verify the Passport against
    a government database.
    """

    validation = {}

    passport_number = fields.get(
        "passport_number",
        ""
    )

    nationality = fields.get(
        "nationality",
        ""
    )

    sex = fields.get(
        "sex",
        ""
    )

    surname = fields.get(
        "surname",
        ""
    )

    given_name = fields.get(
        "given_name",
        ""
    )

    dob = fields.get(
        "date_of_birth",
        ""
    )

    expiry = fields.get(
        "date_of_expiry",
        ""
    )

    passport_type = fields.get(
        "passport_type",
        ""
    )

    country_code = fields.get(
        "country_code",
        ""
    )

    # --------------------------------------------------------
    # Passport Number
    # --------------------------------------------------------

    passport_number_valid = bool(
        re.fullmatch(
            r"[A-Z0-9]{6,9}",
            str(
                passport_number
            ).upper()
        )
    )

    validation["passport_number"] = {
        "valid":
            passport_number_valid,

        "message":
            "Valid passport number format"
            if passport_number_valid
            else "Invalid passport number format"
    }

    # --------------------------------------------------------
    # Nationality
    # --------------------------------------------------------

    nationality_upper = str(
        nationality
    ).upper().strip()

    is_valid_nat = bool(
        re.fullmatch(
            r"[A-Z]{3}",
            nationality_upper
        )
        or nationality_upper == "INDIAN"
    )

    validation["nationality"] = {
        "valid":
            is_valid_nat,

        "message":
            "Valid nationality"
            if is_valid_nat
            else "Invalid nationality code"
    }

    # --------------------------------------------------------
    # Sex
    # --------------------------------------------------------

    sex_upper = str(
        sex
    ).upper().strip()

    sex_valid = sex_upper in [
        "M",
        "F",
        "X"
    ]

    validation["sex"] = {
        "valid":
            sex_valid,

        "message":
            "Valid sex code"
            if sex_valid
            else "Invalid sex code"
    }

    # --------------------------------------------------------
    # Surname
    # --------------------------------------------------------

    surname_valid = is_valid_name(
        surname
    )

    validation["surname"] = {
        "valid":
            surname_valid,

        "message":
            "Valid surname"
            if surname_valid
            else "Invalid or missing surname"
    }

    # --------------------------------------------------------
    # Given Name
    # --------------------------------------------------------

    given_name_valid = is_valid_name(
        given_name
    )

    validation["given_name"] = {
        "valid":
            given_name_valid,

        "message":
            "Valid given name"
            if given_name_valid
            else "Invalid or missing given name"
    }

    # --------------------------------------------------------
    # Date of Birth
    # --------------------------------------------------------

    dob_valid = is_valid_date(
        dob
    )

    validation["date_of_birth"] = {
        "valid":
            dob_valid,

        "message":
            "Valid date of birth"
            if dob_valid
            else "Invalid or missing date of birth"
    }

    # --------------------------------------------------------
    # Expiry Date
    # --------------------------------------------------------

    expiry_valid = is_valid_date(
        expiry
    )

    validation["date_of_expiry"] = {
        "valid":
            expiry_valid,

        "message":
            "Valid expiry date"
            if expiry_valid
            else "Invalid or missing expiry date"
    }

    # --------------------------------------------------------
    # Passport Type
    # --------------------------------------------------------

    passport_type_upper = str(
        passport_type
    ).upper().strip()

    passport_type_valid = (
        passport_type_upper == "P"
    )

    validation["passport_type"] = {
        "valid":
            passport_type_valid,

        "message":
            "Valid passport type"
            if passport_type_valid
            else "Invalid or missing passport type"
    }

    # --------------------------------------------------------
    # Country Code
    # --------------------------------------------------------

    country_code_upper = str(
        country_code
    ).upper().strip()

    country_code_valid = bool(
        re.fullmatch(
            r"[A-Z]{3}",
            country_code_upper
        )
    )

    validation["country_code"] = {
        "valid":
            country_code_valid,

        "message":
            "Valid country code"
            if country_code_valid
            else "Invalid or missing country code"
    }

    return validation


# ============================================================
# AADHAAR VALIDATION
# ============================================================

def validate_aadhaar(fields):
    """
    Validate extracted Aadhaar fields.

    QR code validation is intentionally
    not performed.
    """

    validation = {}

    name = fields.get(
        "name",
        ""
    )

    aadhaar_number = fields.get(
        "aadhaar_number",
        ""
    )

    dob = fields.get(
        "date_of_birth",
        ""
    )

    gender = fields.get(
        "gender",
        ""
    )

    mobile_number = fields.get(
        "mobile_number",
        ""
    )

    # --------------------------------------------------------
    # Name
    # --------------------------------------------------------

    name_valid = is_valid_name(
        name
    )

    validation["name"] = {
        "valid":
            name_valid,

        "message":
            "Valid name"
            if name_valid
            else "Invalid or missing name"
    }

    # --------------------------------------------------------
    # Aadhaar Number
    # --------------------------------------------------------

    aadhaar_valid = bool(
        re.fullmatch(
            r"\d{12}",
            str(
                aadhaar_number
            ).strip()
        )
    )

    validation["aadhaar_number"] = {
        "valid":
            aadhaar_valid,

        "message":
            "Valid Aadhaar number format"
            if aadhaar_valid
            else "Invalid Aadhaar number format"
    }

    # --------------------------------------------------------
    # Date of Birth
    # --------------------------------------------------------

    dob_valid = is_valid_date(
        dob
    )

    validation["date_of_birth"] = {
        "valid":
            dob_valid,

        "message":
            "Valid date/year of birth"
            if dob_valid
            else "Invalid or missing date/year of birth"
    }

    # --------------------------------------------------------
    # Gender
    # --------------------------------------------------------

    gender_upper = str(
        gender
    ).upper().strip()

    gender_valid = gender_upper in [
        "M",
        "F",
        "MALE",
        "FEMALE"
    ]

    validation["gender"] = {
        "valid":
            gender_valid,

        "message":
            "Valid gender"
            if gender_valid
            else "Invalid or missing gender"
    }

    # --------------------------------------------------------
    # Mobile Number
    # --------------------------------------------------------

    mobile_number = str(
        mobile_number
    ).strip()

    mobile_valid = (
        not mobile_number
        or bool(
            re.fullmatch(
                r"[6-9]\d{9}",
                mobile_number
            )
        )
    )

    validation["mobile_number"] = {
        "valid":
            mobile_valid,

        "message":
            "Valid mobile number"
            if mobile_valid
            else "Invalid mobile number"
    }

    return validation


# ============================================================
# DRIVING LICENSE VALIDATION
# ============================================================

def validate_driving_license(fields):
    """
    Validate extracted Driving License fields.
    """

    validation = {}

    dl_number = fields.get("dl_number", "")
    name = fields.get("name", "")
    dob = fields.get("date_of_birth", "")
    issue_date = fields.get("issue_date", "")
    validity_nt = fields.get("validity_nt", "")
    validity_tr = fields.get("validity_tr", "")
    date_of_first_issue = fields.get("date_of_first_issue", "")

    # DL Number: e.g. MH01-1234567890
    dl_valid = bool(
        re.fullmatch(
            r"[A-Z]{2}\d{2}[\-]?\d{7,11}",
            str(dl_number).upper().strip()
        )
    )

    validation["dl_number"] = {
        "valid": dl_valid,
        "message": "Valid DL number format" if dl_valid else "Invalid DL number format"
    }

    name_valid = is_valid_name(name)

    validation["name"] = {
        "valid": name_valid,
        "message": "Valid name" if name_valid else "Invalid or missing name"
    }

    dob_valid = is_valid_date(dob)

    validation["date_of_birth"] = {
        "valid": dob_valid,
        "message": "Valid date of birth" if dob_valid else "Invalid or missing date of birth"
    }

    issue_valid = is_valid_date(issue_date)

    validation["issue_date"] = {
        "valid": issue_valid,
        "message": "Valid issue date" if issue_valid else "Invalid or missing issue date"
    }

    nt_valid = not validity_nt or is_valid_date(validity_nt)

    validation["validity_nt"] = {
        "valid": nt_valid,
        "message": "Valid NT validity" if nt_valid else "Invalid NT validity date"
    }

    tr_valid = not validity_tr or is_valid_date(validity_tr)

    validation["validity_tr"] = {
        "valid": tr_valid,
        "message": "Valid TR validity" if tr_valid else "Invalid TR validity date"
    }

    fi_valid = not date_of_first_issue or is_valid_date(date_of_first_issue)

    validation["date_of_first_issue"] = {
        "valid": fi_valid,
        "message": "Valid date of first issue" if fi_valid else "Invalid date of first issue"
    }

    return validation


# ============================================================
# DOCUMENT STRUCTURE VALIDATION
# ============================================================

def validate_document_structure(
    document_type,
    fields
):
    """
    Check whether expected fields for
    the detected document type are present.
    """

    if document_type == "passport":

        required_fields = [

            "passport_type",

            "country_code",

            "passport_number",

            "surname",

            "given_name",

            "nationality",

            "sex",

            "date_of_birth",

            "date_of_expiry"
        ]

    elif document_type == "aadhaar":

        required_fields = [

            "name",

            "aadhaar_number",

            "date_of_birth",

            "gender"
        ]

    elif document_type == "driving_license":

        required_fields = [

            "dl_number",

            "name",

            "date_of_birth",

            "issue_date"
        ]

    else:

        return {
            "valid":
                False,

            "missing_fields":
                [],

            "message":
                "Unknown document type"
        }

    missing_fields = []

    for field in required_fields:

        value = fields.get(
            field,
            ""
        )

        if not value:

            missing_fields.append(
                field
            )

    return {

        "valid":
            len(missing_fields) == 0,

        "missing_fields":
            missing_fields,

        "message":
            "Document structure is complete"
            if not missing_fields
            else "Required fields are missing"
    }


# ============================================================
# DOCUMENT VALIDATION SCORE
# ============================================================

def calculate_document_score(
    field_validation,
    structure_validation
):
    """
    Calculate document validation score
    from 0 to 100.
    """

    if not field_validation:

        return 0

    total_fields = len(
        field_validation
    )

    valid_fields = sum(
        1
        for result
        in field_validation.values()
        if result.get(
            "valid"
        ) is True
    )

    field_score = (
        valid_fields
        / total_fields
    ) * 100

    # Structure completeness
    if structure_validation.get(
        "valid"
    ):

        structure_score = 100

    else:

        missing_count = len(
            structure_validation.get(
                "missing_fields",
                []
            )
        )

        structure_score = max(
            0,
            100 - (
                missing_count * 15
            )
        )

    final_score = (
        field_score * 0.8
        +
        structure_score * 0.2
    )

    return round(
        min(
            100,
            max(
                0,
                final_score
            )
        ),
        2
    )


# ============================================================
# CROSS-DOCUMENT NORMALIZATION
# ============================================================

def normalize_comparison_value(
    value
):
    """
    Normalize values before comparing
    Passport and Aadhaar.
    """

    if value is None:

        return ""

    value = str(
        value
    ).upper().strip()

    value = re.sub(
        r"[^A-Z0-9]",
        "",
        value
    )

    return value


def normalize_gender(value):
    """
    Normalize gender:

        M / MALE -> M
        F / FEMALE -> F
        X / OTHER -> T
    """

    if not value:

        return ""

    value = str(
        value
    ).strip().upper()

    if value in [
        "M",
        "MALE"
    ]:

        return "M"

    if value in [
        "F",
        "FEMALE"
    ]:

        return "F"

    if value in [
        "T",
        "TRANSGENDER",
        "OTHER",
        "X"
    ]:

        return "T"

    return value


# ============================================================
# GENDER COMPARISON
# ============================================================

def compare_genders(
    passport_gender,
    aadhaar_gender
):
    """
    Compare Passport sex with Aadhaar gender.
    """

    g1 = normalize_gender(
        passport_gender
    )

    g2 = normalize_gender(
        aadhaar_gender
    )

    if not g1 or not g2:

        return {
            "status":
                "NOT_AVAILABLE",

            "match":
                False
        }

    if g1 == g2:

        return {
            "status":
                "MATCH",

            "match":
                True
        }

    return {
        "status":
            "MISMATCH",

        "match":
            False
    }


# ============================================================
# NAME COMPARISON
# ============================================================

def compare_names(
    passport_name,
    aadhaar_name
):
    """
    Compare names across documents.

    Supports:

    - Exact matches
    - Different order
    - Initials
    - Token subsets
    """

    if not passport_name or not aadhaar_name:

        return {
            "status":
                "NOT_AVAILABLE",

            "match":
                False
        }

    p_text = str(
        passport_name
    ).upper()

    a_text = str(
        aadhaar_name
    ).upper()

    # --------------------------------------------------------
    # Tokenize before removing spaces
    # --------------------------------------------------------

    p_tokens = [
        token
        for token in re.split(
            r"[^A-Z0-9]+",
            p_text
        )
        if token
    ]

    a_tokens = [
        token
        for token in re.split(
            r"[^A-Z0-9]+",
            a_text
        )
        if token
    ]

    if not p_tokens or not a_tokens:

        return {
            "status":
                "NOT_AVAILABLE",

            "match":
                False
        }

    # --------------------------------------------------------
    # Exact normalized comparison
    # --------------------------------------------------------

    p_norm = normalize_comparison_value(
        passport_name
    )

    a_norm = normalize_comparison_value(
        aadhaar_name
    )

    if p_norm == a_norm:

        return {
            "status":
                "MATCH",

            "match":
                True
        }

    # --------------------------------------------------------
    # Order-independent comparison
    # --------------------------------------------------------

    if sorted(p_tokens) == sorted(a_tokens):

        return {
            "status":
                "MATCH",

            "match":
                True
        }

    # --------------------------------------------------------
    # Initial-aware comparison
    # --------------------------------------------------------

    if len(a_tokens) <= len(p_tokens):

        short_tokens = a_tokens
        long_tokens = p_tokens

    else:

        short_tokens = p_tokens
        long_tokens = a_tokens

    matched_long = [
        False
        for _ in long_tokens
    ]

    short_matched = 0

    for short_token in short_tokens:

        for index, long_token in enumerate(
            long_tokens
        ):

            if matched_long[index]:

                continue

            # Exact token
            if short_token == long_token:

                matched_long[index] = True

                short_matched += 1

                break

            # Short token is an initial
            elif (
                len(short_token) == 1
                and
                long_token.startswith(
                    short_token
                )
            ):

                matched_long[index] = True

                short_matched += 1

                break

            # Long token is an initial
            elif (
                len(long_token) == 1
                and
                short_token.startswith(
                    long_token
                )
            ):

                matched_long[index] = True

                short_matched += 1

                break

    if short_matched == len(
        short_tokens
    ):

        return {
            "status":
                "MATCH",

            "match":
                True
        }

    return {
        "status":
            "MISMATCH",

        "match":
            False
    }


# ============================================================
# GENERIC FIELD COMPARISON
# ============================================================

def compare_fields(
    passport_value,
    aadhaar_value
):
    """
    Compare two identity fields.
    """

    passport_normalized = (
        normalize_comparison_value(
            passport_value
        )
    )

    aadhaar_normalized = (
        normalize_comparison_value(
            aadhaar_value
        )
    )

    if (
        not passport_normalized
        or not aadhaar_normalized
    ):

        return {
            "status":
                "NOT_AVAILABLE",

            "match":
                False
        }

    if (
        passport_normalized
        == aadhaar_normalized
    ):

        return {
            "status":
                "MATCH",

            "match":
                True
        }

    return {
        "status":
            "MISMATCH",

        "match":
            False
    }


# ============================================================
# CROSS-DOCUMENT VALIDATION
# ============================================================

def cross_document_validation(
    passport_fields,
    id_fields,
    id_type="aadhaar"
):
    """
    Compare common identity fields between:

        Passport
        Aadhaar  OR  Driving License

    Compared fields:

        Name
        Date of Birth
        Sex / Gender  (Aadhaar only)
    """

    # ========================================================
    # NAME
    # ========================================================

    passport_name = " ".join(
        filter(
            None,
            [
                passport_fields.get(
                    "surname",
                    ""
                ),

                passport_fields.get(
                    "given_name",
                    ""
                )
            ]
        )
    )

    id_name = id_fields.get("name", "")

    # ========================================================
    # DATE OF BIRTH
    # ========================================================

    passport_dob = passport_fields.get("date_of_birth", "")

    id_dob = id_fields.get("date_of_birth", "")

    # ========================================================
    # COMPARE NAME
    # ========================================================

    name_result = compare_names(
        passport_name,
        id_name
    )

    # ========================================================
    # COMPARE DOB
    # ========================================================

    dob_result = compare_fields(
        passport_dob,
        id_dob
    )

    results = {
        "name": name_result,
        "date_of_birth": dob_result
    }

    # ========================================================
    # GENDER (Aadhaar only)
    # ========================================================

    if id_type == "aadhaar":

        passport_sex = passport_fields.get("sex", "")
        aadhaar_gender = id_fields.get("gender", "")

        results["gender"] = compare_genders(
            passport_sex,
            aadhaar_gender
        )

    # ========================================================
    # OVERALL RESULT
    # ========================================================

    available_comparisons = [
        result
        for result
        in results.values()
        if result.get(
            "status"
        ) != "NOT_AVAILABLE"
    ]

    if not available_comparisons:

        overall_status = (
            "NOT_AVAILABLE"
        )

    elif all(
        result.get(
            "match"
        ) is True
        for result
        in available_comparisons
    ):

        overall_status = "MATCH"

    else:

        overall_status = "MISMATCH"

    return {

        "overall_status":
            overall_status,

        "fields":
            results
    }