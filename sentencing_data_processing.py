"""
Data processing tools for the sentencing data analysis project.
"""

import argparse
import re
import sys
import logging
import pandas as pd
from typing import Any, Dict, Union, Optional, List

logger = logging.getLogger(__name__)

# Type aliases
ParsedDate = Dict[str, Optional[str]]
JailParseResult = Union[pd.DataFrame, str, None]

# Regular expressions and constants
_JAIL_RE = re.compile(r'(\d+(?:\.\d+)?)\s*([ymd])', re.IGNORECASE)
_JAIL_COLUMNS = ['quantity', 'unit']
_EMPTY_RESULT: ParsedDate = {
    'offence_date': None,
    'offence_start_date': None,
    'offence_end_date': None,
}

EXPECTED_MASTER_COLUMNS = [
    "uid",
    "offence",
    "date",
    "jail",
    "mode",
    "conditions",
    "fine",
    "appeal",
]

# Map all accepted unit variants to canonical codes
UNIT_MAP = {
    'y': 'y',   # years
    'm': 'm',   # months
    'd': 'd',   # days
}

# Unit → day factor for the "default" conversion
_UNIT_DAY_FACTORS = {
    'y': 365,
    'm': 30,   # overridden for quantity == 12
    'd': 1,
}


# UID string parsing tools

def parse_uid_string(uid_str: Union[str, float]) -> Dict[str, Optional[str]]:
    """
    Parse a UID string into its components.

    The UID may have between 3 and 4 components:
    - First: case ID
    - Second: docket identifier
    - Third: count
    - Fourth (optional): defendant ID (defaults to "a" if not present)

    If more than four underscore-separated parts are present, only the first
    four are used and the rest are ignored.

    Args:
        uid_str: The UID string to parse (e.g., "2024abcj264_230980468P1_1"
            or "2024mbpc96_None_1_a").

    Returns:
        A dictionary with keys: 'case_id', 'docket', 'count', 'defendant'.
        Returns None values if the string is empty/invalid.
    """

    # Handle NaN, None, or empty strings
    if uid_str is None or pd.isna(uid_str):
        return {
            "case_id": None,
            "docket": None,
            "count": None,
            "defendant": "a",
        }

    uid_str = str(uid_str).strip()
    if uid_str == "":
        return {
            "case_id": None,
            "docket": None,
            "count": None,
            "defendant": "a",
        }

    # Split the string by underscores and extract the components
    parts = uid_str.split("_")

    case_id = parts[0] if len(parts) >= 1 else None
    docket = parts[1] if len(parts) >= 2 else None
    count = parts[2] if len(parts) >= 3 else None
    defendant = parts[3] if len(parts) >= 4 else "a"

    return {
        "case_id": case_id,
        "docket": docket,
        "count": count,
        "defendant": defendant,
    }


def process_uid_string(
    uid_str: Union[str, float],
    log: bool = False,
    log_level: int = logging.INFO,
    logger_override: Optional[logging.Logger] = None,
) -> Dict[str, Optional[str]]:
    """
    Process a UID string, parse it, and optionally log the components.

    Args:
        uid_str: The UID string (or NaN-like value) to process.
        log: If True, log parsed components using the module logger.
        log_level: Logging level to use when log is True.
        logger_override: Optional logger instance to use instead of module logger.

    Returns:
        A dictionary with the parsed UID components.
    """

    parsed = parse_uid_string(uid_str)

    if log:
        active_logger = logger_override or logger
        active_logger.log(
            log_level,
            "Parsed UID string %r -> case_id=%r, docket=%r, count=%r, "
            "defendant=%r",
            uid_str,
            parsed["case_id"],
            parsed["docket"],
            parsed["count"],
            parsed["defendant"],
        )

    return parsed


# Master CSV schema validation
def validate_master_schema(
    df: pd.DataFrame,
    required_columns: Optional[list[str]] = None,
    strict: bool = False,
) -> dict:
    """
    Validate the expected schema for master.csv.

    Args:
        df: DataFrame to validate
        required_columns: Optional list of required column names
        strict: If True, raise ValueError on missing columns

    Returns:
        A dict with keys: 'missing', 'extra', 'required'
    """

    required = list(required_columns or EXPECTED_MASTER_COLUMNS)

    required_set = set(required)
    columns_set = set(df.columns)
    
    missing = sorted(required_set - columns_set)
    extra = sorted(columns_set - required_set)

    if strict and missing:
        raise ValueError(f"Missing required columns: {missing}")

    return {"missing": missing, "extra": extra, "required": required}


# Offence string parsing tools

def load_offences_lookup(offences_file: str = 'data/offence/all-criminal-offences-current.csv') -> pd.DataFrame:
    """
    Load the offences lookup table from CSV.
    
    Args:
        offences_file: Path to the offences CSV file
        
    Returns:
        A pandas DataFrame with the offences data
    """
    return pd.read_csv(offences_file, on_bad_lines='skip', engine='python')

def normalize_offence_code(offence_code: str) -> List[str]:
    """
    Generate possible variations of an offence code for matching.

    Handles variations like:
    - "cc_101"      -> ["cc_101", "cc101"]
    - "cc101"       -> ["cc101", "cc_101"]
    - "101"         -> ["101", "cc_101"]
    - "cc344(1)(b)" -> ["cc344(1)(b)", "cc_344(1)(b)"]

    The input string is always the first element in the returned list.
    Variants are ordered from most to least similar and are deduplicated.
    """

    # Normalize simple whitespace
    code = offence_code.strip()

    candidates: List[str] = []
    candidates.append(code)  # always include original as first

    # 1. If it doesn't start with "cc" at all, add "cc_" + code
    if not code.startswith('cc'):
        candidates.append('cc_' + code)

    # 2. If it starts with "cc" but not with "cc_", add a version with underscore
    elif code.startswith('cc') and not code.startswith('cc_'):
        # "cc344(1)(b)" -> "cc_344(1)(b)"
        candidates.append('cc_' + code[2:])

    # 3. If it starts with "cc_", also try without underscore
    elif code.startswith('cc_'):
        # "cc_344(1)(b)" -> "cc344(1)(b)"
        candidates.append('cc' + code[3:])

    # 4. Deduplicate while preserving order
    seen = set()
    unique_candidates: List[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique_candidates.append(c)

    return unique_candidates
    

def parse_offence_string(offence_str: Union[str, float], 
                         offences_df: Optional[pd.DataFrame] = None,
                         offences_file: str = 'data/offence/all-criminal-offences-current.csv') -> dict:
    """
    Parse an offence string and match it against the offences lookup table.
    
    Args:
        offence_str: The offence string to parse (e.g., "cc_101" or "145(5)")
        offences_df: Optional pre-loaded offences DataFrame. If None, loads from file.
        offences_file: Path to the offences CSV file (used if offences_df is None)
        
    Returns:
        A dictionary with keys: 'offence_code', 'offence_name'
        Returns None values if string is empty/invalid or no match found
    """

    # Handle NaN, None, or empty strings
    if offence_str is None or (isinstance(offence_str, float) and pd.isna(offence_str)):
        return {'offence_code': None, 'offence_name': None}

    offence_code = str(offence_str).strip()
    if offence_code == '':
        return {'offence_code': None, 'offence_name': None}
    
    # Save the original code for later return if no match is found
    original_code = offence_code

    # Check if the code has a _ycja suffix and remove it if it does
    has_ycja = '_ycja' in offence_code
    normalized_code = offence_code.replace('_ycja', '') if has_ycja else offence_code
    
    # Load offences lookup if not provided
    if offences_df is None:
        offences_df = load_offences_lookup(offences_file)

    # First try exact (normalized) match
    match = offences_df.loc[offences_df['section'] == normalized_code]
    if not match.empty:
        offence_name = match['offence_name'].iat[0]
        if has_ycja and offence_name:
            offence_name += ' (YCJA)'
        return {
            'offence_code': normalized_code,
            'offence_name': offence_name
        }

    # Next try variations to see if we can find a match from imperfect input
    variations = normalize_offence_code(normalized_code)
    for variation in variations:
        if variation == normalized_code:
            continue
        match = offences_df.loc[offences_df['section'] == variation]
        if not match.empty:
            offence_name = match['offence_name'].iat[0]
            if has_ycja and offence_name:
                offence_name += ' (YCJA)'
            return {
                'offence_code': variation,
                'offence_name': offence_name
            }

    # Return the original code and no name if no match is found
    return {'offence_code': original_code, 'offence_name': None}


# Date string parsing tools
def parse_date_string(date_str: Any) -> ParsedDate:
    """
    Parse a date string into its components.

    - If no '&', returns "offence_date".
    - If '&' present, returns "offence_start_date" and "offence_end_date".
    - Returns None values if input is empty/invalid-like.
    """

    if pd.isna(date_str) or date_str is None:
        return _EMPTY_RESULT.copy()

    # Normalize to string
    s = str(date_str).strip()
    if not s:
        return _EMPTY_RESULT.copy()

    result = _EMPTY_RESULT.copy()

    # Split by '&' if present
    if '&' in s:
        start, end = (part.strip() for part in s.split('&', 1))
        result['offence_start_date'] = start or None
        result['offence_end_date'] = end or None
    else:
        result['offence_date'] = s

    return result


# Jail string parsing tools
def parse_jail_string(jail_str: Any) -> JailParseResult:
    """
    Parse a jail sentence string into a dataframe with quantity and unit columns.

    - "1y&6m&3d" -> rows for 1y, 6m, 3d
    - "indeterminate" -> "indeterminate"
    - empty/NaN -> empty DataFrame with ['quantity', 'unit']
    - non-empty but with no valid matches -> None
    """
    if pd.isna(jail_str):
        return pd.DataFrame(columns=_JAIL_COLUMNS)

    s = str(jail_str).strip()
    if not s:
        return pd.DataFrame(columns=_JAIL_COLUMNS)

    if s.lower() == 'indeterminate':
        return "indeterminate"

    parts = s.split('&') if '&' in s else [s]

    data = []
    for part in parts:
        for q, u in _JAIL_RE.findall(part.strip()):
            unit = UNIT_MAP.get(u.lower())
            if unit is None:
                # Option A: silently skip unknown units
                continue

                # Option B (stricter): treat the whole string as unparseable
                # return None

            data.append({'quantity': float(q), 'unit': unit})

    if not data:
        return None

    return pd.DataFrame(data, columns=_JAIL_COLUMNS)


def calculate_total_days(
    df: Union[pd.DataFrame, str, None]
) -> Optional[int]:
    """
    Calculate total days from a dataframe of jail components.

    Rules:
    - 1y = 365 days
    - 1m = 30 days 
    - 12m = 365 days
    - 1d = 1 day

    df may be:
    - DataFrame with 'quantity' (float/int) and 'unit' ('y'/'m'/'d')
    - the string "indeterminate"
    - None
    """

    if df is None:
        return None

    if isinstance(df, str) and df.lower() == "indeterminate":
        return None

    if not isinstance(df, pd.DataFrame) or df.empty:
        return 0

    units = df['unit'].str.lower()

    # Special-case: 12 months = 365 days
    is_12_months = (units == 'm') & (df['quantity'] == 12)

    # Compute factors for the usual & 12m cases
    factors = units.map(_UNIT_DAY_FACTORS).fillna(0)
    factors = factors.where(~is_12_months, other=365 / df['quantity'])

    total_days = (df['quantity'] * factors).sum()

    return int(total_days)


# Mode string parsing tools

def parse_mode_string(mode_str: Union[str, float]) -> tuple:
    """
    Parse a mode string by splitting at the hyphen.
    
    Args:
        mode_str: The mode string to parse (e.g., "jail-consecutive")
        
    Returns:
        A tuple with two parts: (part1, part2)
        Returns (None, None) if string is empty/invalid
    """
    # Handle NaN, None, or empty strings
    if pd.isna(mode_str) or mode_str == '' or mode_str is None:
        return (None, None)
    
    # Convert to string if not already
    mode_str = str(mode_str).strip()
    
    # Split at the first hyphen
    if '-' in mode_str:
        parts = mode_str.split('-', 1)  # Split only on first hyphen
        return (parts[0], parts[1])
    else:
        # No hyphen found, return the whole string as part1
        return (mode_str, None)

# Conditions string parsing tools

def parse_conditions_string(conditions_str: Union[str, float]) -> dict:
    """
    Parse a conditions string into its components: time length, unit, and type.
    
    Handles formats:
    - "18m-probation" (time-unit-type)
    - "ltso-10y" (type-time-unit)
    - "18m" (time-unit only, no type)
    
    Args:
        conditions_str: The conditions string to parse
        
    Returns:
        A dictionary with keys 'time', 'unit', and 'type'
        Returns empty dict or None values if string is empty/invalid
    """
    # Handle NaN, None, or empty strings
    if pd.isna(conditions_str) or conditions_str == '' or conditions_str is None:
        return {'time': None, 'unit': None, 'type': None}
    
    # Convert to string if not already
    conditions_str = str(conditions_str).strip()
    
    # Initialize result
    result = {'time': None, 'unit': None, 'type': None}
    
    # Pattern to match time-unit (e.g., "18m", "2y", "10y")
    time_unit_pattern = r'(\d+(?:\.\d+)?)\s*([ymd])'
    
    # Pattern to match type (probation, discharge, ltso, ircs, parole, etc.)
    type_pattern = r'(probation|discharge|ltso|ircs|parole)'
    
    # Try format 1: time-unit-type (e.g., "18m-probation")
    match1 = re.match(rf'^{time_unit_pattern}-{type_pattern}$', conditions_str, re.IGNORECASE)
    if match1:
        result['time'] = float(match1.group(1))
        result['unit'] = match1.group(2).lower()
        result['type'] = match1.group(3).lower()
        return result
    
    # Try format 2: type-time-unit (e.g., "ltso-10y")
    match2 = re.match(rf'^{type_pattern}-{time_unit_pattern}$', conditions_str, re.IGNORECASE)
    if match2:
        result['type'] = match2.group(1).lower()
        result['time'] = float(match2.group(2))
        result['unit'] = match2.group(3).lower()
        return result
    
    # Try format 3: time-unit only (e.g., "18m")
    match3 = re.match(rf'^{time_unit_pattern}$', conditions_str, re.IGNORECASE)
    if match3:
        result['time'] = float(match3.group(1))
        result['unit'] = match3.group(2).lower()
        result['type'] = None
        return result
    
    # If no pattern matches, return None values
    return result

# Fine string parsing tools

def parse_fine_string(fine_str: Union[str, float, int]) -> Optional[str]:
    """
    Parse a fine string and format it as currency with two decimal places.
    
    Args:
        fine_str: The fine value (can be string, float, or int)
        
    Returns:
        A formatted string with dollar sign and two decimal places (e.g., "$1000.00")
        Returns None if fine is empty/invalid
    """
    # Handle NaN, None, or empty strings
    if pd.isna(fine_str) or fine_str == '' or fine_str is None:
        return None
    
    # Convert to string if not already
    fine_str = str(fine_str).strip()
    
    # Remove any existing dollar signs or commas
    fine_str = fine_str.replace('$', '').replace(',', '').strip()
    
    # Try to convert to float
    try:
        fine_value = float(fine_str)
        # Format to two decimal places with dollar sign
        return f"${fine_value:.2f}"
    except (ValueError, TypeError):
        # If conversion fails, return None
        return None

# Appeal string parsing tools

def parse_appeal_string(appeal_str: Union[str, float]) -> dict:
    """
    Parse an appeal string into its components: court appealed to and result.
    
    The appeal string consists of two parts separated by an underscore:
    - First part: court appealed to
    - Second part: result
    
    Args:
        appeal_str: The appeal string to parse (e.g., "2024skca79_upheld")
        
    Returns:
        A dictionary with keys: 'court', 'result'
        Returns None values if string is empty/invalid
    """
    # Handle NaN, None, or empty strings
    if pd.isna(appeal_str) or appeal_str == '' or appeal_str is None:
        return {'court': None, 'result': None}
    
    # Convert to string if not already
    appeal_str = str(appeal_str).strip()
    
    # Split by underscore
    parts = appeal_str.split('_', 1)  # Split only on first underscore
    
    if len(parts) == 2:
        return {
            'court': parts[0].strip(),
            'result': parts[1].strip()
        }
    else:
        # If no underscore found or only one part, return what we have
        return {
            'court': parts[0].strip() if len(parts) > 0 else None,
            'result': None
        }

# Full row processing function

def process_master_row(
    row_data: Union[pd.Series, dict, tuple, list],
    offences_file: str = 'data/offence/all-criminal-offences-current.csv',
    verbose: bool = True,
) -> dict:
    """
    Process a full row from master.csv and parse all fields.
    
    Expected column order: uid, offence, date, jail, mode, conditions, fine, appeal
    
    Args:
        row_data: Can be:
            - pandas Series (row from dataframe)
            - dict with column names as keys
            - tuple/list with values in order: (uid, offence, date, jail, mode, conditions, fine, appeal)
        offences_file: Path to the offences CSV file
        
    Returns:
        A dictionary with all parsed components
    """
    # Extract values based on input type
    if isinstance(row_data, pd.Series):
        uid = row_data.get('uid', '')
        offence = row_data.get('offence', '')
        date = row_data.get('date', '')
        jail = row_data.get('jail', '')
        mode = row_data.get('mode', '')
        conditions = row_data.get('conditions', '')
        fine = row_data.get('fine', '')
        appeal = row_data.get('appeal', '')
    elif isinstance(row_data, dict):
        uid = row_data.get('uid', '')
        offence = row_data.get('offence', '')
        date = row_data.get('date', '')
        jail = row_data.get('jail', '')
        mode = row_data.get('mode', '')
        conditions = row_data.get('conditions', '')
        fine = row_data.get('fine', '')
        appeal = row_data.get('appeal', '')
    elif isinstance(row_data, (tuple, list)):
        # Assume order: uid, offence, date, jail, mode, conditions, fine, appeal
        uid = row_data[0] if len(row_data) > 0 else ''
        offence = row_data[1] if len(row_data) > 1 else ''
        date = row_data[2] if len(row_data) > 2 else ''
        jail = row_data[3] if len(row_data) > 3 else ''
        mode = row_data[4] if len(row_data) > 4 else ''
        conditions = row_data[5] if len(row_data) > 5 else ''
        fine = row_data[6] if len(row_data) > 6 else ''
        appeal = row_data[7] if len(row_data) > 7 else ''
    else:
        raise ValueError("row_data must be a pandas Series, dict, tuple, or list")
    
    # Parse all fields
    printer = print if verbose else (lambda *args, **kwargs: None)

    printer("=" * 80)
    printer("PROCESSING MASTER CSV ROW")
    printer("=" * 80)
    printer()
    
    # UID
    printer("UID:")
    uid_parsed = parse_uid_string(uid)
    printer(f"  Case ID: {uid_parsed['case_id']}")
    printer(f"  Docket: {uid_parsed['docket']}")
    printer(f"  Count: {uid_parsed['count']}")
    printer(f"  Defendant: {uid_parsed['defendant']}")
    printer()
    
    # Offence
    printer("OFFENCE:")
    offence_parsed = parse_offence_string(offence, offences_file=offences_file)
    printer(f"  Offence code: {offence_parsed['offence_code']}")
    printer(f"  Offence name: {offence_parsed['offence_name']}")
    printer()
    
    # Date
    printer("DATE:")
    date_parsed = parse_date_string(date)
    if date_parsed['offence_date'] is not None:
        printer(f"  Offence date: {date_parsed['offence_date']}")
    else:
        printer(f"  Offence start date: {date_parsed['offence_start_date']}")
        printer(f"  Offence end date: {date_parsed['offence_end_date']}")
    printer()
    
    # Jail
    printer("JAIL:")
    jail_df = parse_jail_string(jail)
    if jail_df is None:
        printer("  Sentence: unrecognized format")
        jail_total_days = None
    elif isinstance(jail_df, str) and jail_df == "indeterminate":
        printer("  Sentence: indeterminate")
        jail_total_days = None
    else:
        printer("  Sentence components:")
        if not jail_df.empty:
            printer(jail_df.to_string(index=False))
        else:
            printer("  (no jail sentence)")
        jail_total_days = calculate_total_days(jail_df)
        printer(f"  Total days: {jail_total_days}")
    printer()
    
    # Mode
    printer("MODE:")
    mode_parsed = parse_mode_string(mode)
    printer(f"  Jail type: {mode_parsed[0]}")
    printer(f"  Sentence mode: {mode_parsed[1]}")
    printer()
    
    # Conditions
    printer("CONDITIONS:")
    conditions_parsed = parse_conditions_string(conditions)
    time = conditions_parsed['time']
    unit = conditions_parsed['unit']
    cond_type = conditions_parsed['type']
    
    # Convert unit to human readable format
    if unit == 'y':
        unit = 'year'
    elif unit == 'm':
        unit = 'month'
    elif unit == 'd':
        unit = 'day'
    else:
        unit = 'unknown'
    
    # Add pluralization to unit if time is not 1
    if time is not None and time != 1:
        unit += 's'
    
    # Special case for discharge: 0 length = absolute discharge, otherwise conditional discharge
    if cond_type == 'discharge':
        if time == 0:
            cond_type = 'absolute discharge'
        else:
            cond_type = 'conditional discharge'
    
    if time is not None:
        printer(f"  Time length: {time} {unit}")
    else:
        printer(f"  Time length: None")
    printer(f"  Type: {cond_type}")
    printer()
    
    # Fine
    printer("FINE:")
    fine_formatted = parse_fine_string(fine)
    printer(f"  Formatted fine: {fine_formatted}")
    printer()
    
    # Appeal
    printer("APPEAL:")
    appeal_parsed = parse_appeal_string(appeal)
    printer(f"  Court: {appeal_parsed['court']}")
    printer(f"  Result: {appeal_parsed['result']}")
    printer()
    
    printer("=" * 80)
    
    # Return all parsed data
    return {
        'uid': uid_parsed,
        'offence': offence_parsed,
        'date': date_parsed,
        'jail': {
            'components': jail_df if not isinstance(jail_df, str) else None,
            'total_days': jail_total_days,
            'is_indeterminate': isinstance(jail_df, str) and jail_df == "indeterminate",
            'is_unrecognized': jail_df is None
        },
        'mode': {
            'jail_type': mode_parsed[0],
            'sentence_mode': mode_parsed[1]
        },
        'conditions': {
            'time': conditions_parsed['time'],
            'unit': unit,  # Use processed unit (with pluralization)
            'type': cond_type  # Use processed type (absolute/conditional discharge)
        },
        'fine': fine_formatted,
        'appeal': appeal_parsed
    }


def load_master_csv(master_file: str = 'data/case/master.csv') -> pd.DataFrame:
    """
    Load the master CSV into a DataFrame.

    Args:
        master_file: Path to the master CSV file

    Returns:
        A pandas DataFrame
    """
    return pd.read_csv(master_file, on_bad_lines='skip', engine='python')


def run_cli() -> int:
    """
    Minimal CLI for validating and sampling master.csv parsing.
    """
    parser = argparse.ArgumentParser(description="Sentencing data processing helpers")
    parser.add_argument(
        "--master",
        default="data/case/master.csv",
        help="Path to master CSV",
    )
    parser.add_argument(
        "--offences",
        default="data/offence/all-criminal-offences-current.csv",
        help="Path to offences CSV",
    )
    parser.add_argument(
        "--row-index",
        type=int,
        default=0,
        help="Row index to parse from master CSV",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate schema, do not parse rows",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress printing during row parsing",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO)
    df = load_master_csv(args.master)
    schema = validate_master_schema(df)
    if schema["missing"]:
        print(f"Missing columns: {schema['missing']}")
        return 1
    if schema["extra"]:
        print(f"Extra columns: {schema['extra']}")

    if args.validate_only:
        print("Schema validation passed.")
        return 0

    if df.empty:
        print("Master CSV is empty.")
        return 1

    row_index = max(0, min(args.row_index, len(df) - 1))
    row = df.iloc[row_index]
    process_master_row(row, offences_file=args.offences, verbose=not args.quiet)
    return 0


if __name__ == "__main__":
    sys.exit(run_cli())
