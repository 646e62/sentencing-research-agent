"""
Data processing tools for the sentencing data analysis project.
"""

import re
import pandas as pd
from typing import Union, Optional

# UID string parsing tools

def parse_uid_string(uid_str: Union[str, float]) -> dict:
    """
    Parse a UID string into its components.
    
    The UID may have between 3 and 4 components:
    - First: case ID
    - Second: docket identifier
    - Third: count
    - Fourth (optional): defendant ID (defaults to "a" if not present)
    
    Args:
        uid_str: The UID string to parse (e.g., "2024abcj264_230980468P1_1" or "2024mbpc96_None_1_a")
        
    Returns:
        A dictionary with keys: 'case_id', 'docket', 'count', 'defendant'
        Returns None values if string is empty/invalid
    """
    # Handle NaN, None, or empty strings
    if pd.isna(uid_str) or uid_str == '' or uid_str is None:
        return {'case_id': None, 'docket': None, 'count': None, 'defendant': '1'}
    
    # Convert to string if not already
    uid_str = str(uid_str).strip()
    
    # Split by underscore
    parts = uid_str.split('_')
    
    # Initialize result with default defendant
    result = {'case_id': None, 'docket': None, 'count': None, 'defendant': '1'}
    
    # Handle different numbers of parts
    if len(parts) == 2:
        # 2 parts: case_id_count (no docket identifier)
        result['case_id'] = parts[0]
        result['docket'] = None
        result['count'] = parts[1]
        result['defendant'] = '1'

    elif len(parts) == 3:
        # 3 parts: case_id_docket_count
        result['case_id'] = parts[0]
        result['docket'] = parts[1]
        result['count'] = parts[2]
        result['defendant'] = '1'

    elif len(parts) == 4:
        # 4 parts: case_id_docket_count_defendant
        result['case_id'] = parts[0]
        result['docket'] = parts[1]
        result['count'] = parts[2]
        result['defendant'] = parts[3]

    else:
        # Unexpected format, try to extract what we can
        if len(parts) >= 1:
            result['case_id'] = parts[0]
        if len(parts) >= 2:
            result['docket'] = parts[1]
        if len(parts) >= 3:
            result['count'] = parts[2]
        if len(parts) >= 4:
            result['defendant'] = parts[3]
        else:
            result['defendant'] = '1'
    
    return result

def process_uid_string(uid_str: Union[str, float]) -> dict:
    """
    Process a UID string, parse it, and print the components to terminal.
    
    Args:
        uid_str: The UID string to process
        
    Returns:
        A dictionary with the parsed UID components
    """
    # Parse the string
    parsed = parse_uid_string(uid_str)
    
    # Print results
    print(f"UID string: {uid_str}")
    print(f"  Case ID: {parsed['case_id']}")
    print(f"  Docket: {parsed['docket']}")
    print(f"  Count: {parsed['count']}")
    print(f"  Defendant: {parsed['defendant']}")
    print("=" * 60)
    
    return parsed


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

def normalize_offence_code(offence_code: str) -> list:
    """
    Generate possible variations of an offence code for matching.
    
    Handles variations like:
    - "cc_101" -> ["cc_101"]
    - "101" -> ["101", "cc_101"]
    - "cc344(1)(b)" -> ["cc344(1)(b)", "cc_344(1)(b)"]
    
    Args:
        offence_code: The offence code to normalize
        
    Returns:
        A list of possible code variations to try matching
    """
    variations = [offence_code]
    
    # If it doesn't start with "cc", try adding "cc_"
    if not offence_code.startswith('cc'):
        variations.append('cc_' + offence_code)
    
    # If it starts with "cc" but not "cc_", try adding underscore
    elif offence_code.startswith('cc') and not offence_code.startswith('cc_'):
        variations.append('cc_' + offence_code[2:])
    
    # If it starts with "cc_", also try without underscore
    elif offence_code.startswith('cc_'):
        variations.append('cc' + offence_code[3:])
    
    return variations

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
    if pd.isna(offence_str) or offence_str == '' or offence_str is None:
        return {'offence_code': None, 'offence_name': None}
    
    # Convert to string if not already
    offence_code = str(offence_str).strip()
    
    # Strip common suffixes like "_ycja" before matching
    # Store original for return value
    original_code = offence_code
    if '_ycja' in offence_code:
        offence_code = offence_code.replace('_ycja', '')
    
    # Load offences lookup if not provided
    if offences_df is None:
        offences_df = load_offences_lookup(offences_file)
    
    # Check if original code has _ycja suffix
    has_ycja = '_ycja' in original_code
    
    # Try to match the offence code (using normalized version)
    # First try exact match
    match = offences_df[offences_df['section'] == offence_code]
    
    if len(match) > 0:
        matched_code = offence_code  # The code that matched
        offence_name = match.iloc[0]['offence_name']
        # Append " (YCJA)" if _ycja suffix was present
        if has_ycja and offence_name:
            offence_name = offence_name + ' (YCJA)'
        return {
            'offence_code': matched_code,  # Return the matched code from lookup table
            'offence_name': offence_name
        }
    
    # Try variations
    variations = normalize_offence_code(offence_code)
    for variation in variations:
        if variation != offence_code:  # Skip the one we already tried
            match = offences_df[offences_df['section'] == variation]
            if len(match) > 0:
                matched_code = variation  # The variation that matched
                offence_name = match.iloc[0]['offence_name']
                # Append " (YCJA)" if _ycja suffix was present
                if has_ycja and offence_name:
                    offence_name = offence_name + ' (YCJA)'
                return {
                    'offence_code': matched_code,  # Return the matched code from lookup table
                    'offence_name': offence_name
                }
    
    # No match found
    return {'offence_code': offence_code, 'offence_name': None}

def process_offence_string(offence_str: Union[str, float],
                          offences_file: str = 'data/offence/all-criminal-offences-current.csv') -> dict:
    """
    Process an offence string, parse it, match against lookup table, and print results.
    
    Args:
        offence_str: The offence string to process
        offences_file: Path to the offences CSV file
        
    Returns:
        A dictionary with the parsed offence components
    """
    # Parse the string
    parsed = parse_offence_string(offence_str, offences_file=offences_file)
    
    # Print results
    print(f"Offence string: {offence_str}")
    print(f"  Offence code: {parsed['offence_code']}")
    print(f"  Offence name: {parsed['offence_name']}")
    print("=" * 60)
    
    return parsed


# Date string parsing tools

def parse_date_string(date_str: Union[str, float]) -> dict:
    """
    Parse a date string into its components.
    
    If there is no ampersand, returns the value as "offence_date".
    If there is an ampersand, returns "offence_start_date" and "offence_end_date".
    
    Args:
        date_str: The date string to parse (e.g., "2024-12-18" or "1970-09-01&1981-07-01")
        
    Returns:
        A dictionary with keys:
        - "offence_date" (if no ampersand)
        - "offence_start_date" and "offence_end_date" (if ampersand present)
        Returns None values if string is empty/invalid
    """
    # Handle NaN, None, or empty strings
    if pd.isna(date_str) or date_str == '' or date_str is None:
        return {'offence_date': None, 'offence_start_date': None, 'offence_end_date': None}
    
    # Convert to string if not already
    date_str = str(date_str).strip()
    
    # Initialize result
    result = {'offence_date': None, 'offence_start_date': None, 'offence_end_date': None}
    
    # Check if ampersand is present
    if '&' in date_str:
        # Split by ampersand
        parts = date_str.split('&', 1)
        result['offence_start_date'] = parts[0].strip()
        result['offence_end_date'] = parts[1].strip()
    else:
        # No ampersand, single date
        result['offence_date'] = date_str
    
    return result

def process_date_string(date_str: Union[str, float]) -> dict:
    """
    Process a date string, parse it, and print the components to terminal.
    
    Args:
        date_str: The date string to process
        
    Returns:
        A dictionary with the parsed date components
    """
    # Parse the string
    parsed = parse_date_string(date_str)
    
    # Print results
    print(f"Date string: {date_str}")
    if parsed['offence_date'] is not None:
        print(f"  Offence date: {parsed['offence_date']}")
    elif parsed['offence_start_date'] is not None:
        print(f"  Offence start date: {parsed['offence_start_date']}")
        print(f"  Offence end date: {parsed['offence_end_date']}")
    else:
        print(f"  Offence date: {parsed['offence_date']}")
    print("=" * 60)
    
    return parsed


# Jail string parsing tools

def parse_jail_string(jail_str: Union[str, float]) -> Union[pd.DataFrame, str]:
    """
    Parse a jail sentence string into a dataframe with quantity and unit columns.
    
    If the string contains "&", it splits by "&" and parses each component.
    If the string is "indeterminate", returns the string "indeterminate".
    
    Args:
        jail_str: The jail sentence string to parse (e.g., "1y&6m&3d" or "12m")
        
    Returns:
        A pandas DataFrame with 'quantity' and 'unit' columns, or the string "indeterminate"
    """
    # Handle NaN, None, or empty strings
    if pd.isna(jail_str) or jail_str == '' or jail_str is None:
        return pd.DataFrame(columns=['quantity', 'unit'])
    
    # Convert to string if not already
    jail_str = str(jail_str).strip()
    
    # Handle special case: "indeterminate"
    if jail_str.lower() == 'indeterminate':
        return "indeterminate"
    
    # Split by "&" if present
    if '&' in jail_str:
        parts = jail_str.split('&')
    else:
        # If no "&", parse the whole string for all units
        parts = [jail_str]
    
    # Parse each part
    data = []
    for part in parts:
        part = part.strip()
        # Find all matches of number followed by letter (y, m, or d) in this part
        matches = re.findall(r'(\d+(?:\.\d+)?)\s*([ymd])', part, re.IGNORECASE)
        for match in matches:
            quantity = float(match[0])
            unit = match[1].lower()
            data.append({'quantity': quantity, 'unit': unit})
    
    # Create dataframe
    df = pd.DataFrame(data)
    
    return df

def calculate_total_days(df: Union[pd.DataFrame, str]) -> Optional[int]:
    """
    Calculate total days from a dataframe of jail components.
    
    Conversion rates:
    - 1 year (y) = 365 days
    - 12 months (m) = 365 days
    - 1 month (m) = 30 days
    - 1 day (d) = 1 day

    The code can be adapted to return a more verbose output that includes the 
    years, months, and days and their conversions.
    
    Args:
        df: A pandas DataFrame with 'quantity' and 'unit' columns, or 
        "indeterminate"
        
    Returns:
        Total number of days as an integer, or None if indeterminate
    """
    if isinstance(df, str) and df == "indeterminate":
        return None
    
    if df.empty:
        return 0
    
    total_days = 0
    
    for _, row in df.iterrows():
        quantity = row['quantity']
        unit = row['unit'].lower()
        
        if unit == 'y':
            total_days += int(quantity * 365)
        # Special case for 12 months = 1 year
        elif unit == 'm' and quantity == 12:
            total_days += 365
        elif unit == 'm':
            total_days += int(quantity * 30)
        elif unit == 'd':
            total_days += int(quantity)
    
    return total_days

def process_jail_string(jail_str: Union[str, float]) -> None:
    """
    Process a jail string, create a dataframe, calculate total days, and print results.
    
    This is the main function for testing purposes.
    
    Args:
        jail_str: The jail sentence string to process
    """
    # Parse the string
    df = parse_jail_string(jail_str)
    
    # Calculate total days# Calculate and print total days
    if isinstance(df, str):
        total_days = "indeterminate sentence"
    else:
        total_days = calculate_total_days(df)
    
    # Print the dataframe
    print(f"{jail_str} -> {total_days} days")

    return total_days


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

def process_mode_string(mode_str: Union[str, float]) -> tuple:
    """
    Process a mode string, parse it, and return the two parts.
    
    Args:
        mode_str: The mode string to process
        
    Returns:
        A tuple with two parts: (part1, part2)
    """
    # Parse the string
    jail_type, sentence_mode = parse_mode_string(mode_str)
    
    # Print results
    return jail_type, sentence_mode


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

def process_conditions_string(conditions_str: Union[str, float]) -> None:
    """
    Process a conditions string, parse it, and print the components to terminal.
    
    Args:
        conditions_str: The conditions string to process
    """
    # Parse the string
    parsed = parse_conditions_string(conditions_str)
    
    # Format output
    time = parsed['time']
    unit = parsed['unit']
    cond_type = parsed['type']

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
    if time != 1:
        unit += 's'
    
    # Special case for discharge: 0 length = absolute discharge, otherwise conditional discharge
    if cond_type == 'discharge':
        if time == 0:
            cond_type = 'absolute discharge'
        else:
            cond_type = 'conditional discharge'
    
    # Return results
    return time, unit, cond_type


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

def process_fine_string(fine_str: Union[str, float, int]) -> Optional[str]:
    """
    Process a fine string, parse it, format it, and print the result to terminal.
    
    Args:
        fine_str: The fine value to process
        
    Returns:
        A formatted string with dollar sign and two decimal places, or None
    """
    # Parse the string
    formatted_fine = parse_fine_string(fine_str)
    
    # Print results
    print(f"Fine string: {fine_str}")
    print(f"  Formatted fine: {formatted_fine}")
    print("=" * 60)
    
    return formatted_fine


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

def process_appeal_string(appeal_str: Union[str, float]) -> dict:
    """
    Process an appeal string, parse it, and print the components to terminal.
    
    Args:
        appeal_str: The appeal string to process
        
    Returns:
        A dictionary with the parsed appeal components
    """
    # Parse the string
    parsed = parse_appeal_string(appeal_str)
    
    # Print results
    print(f"Appeal string: {appeal_str}")
    print(f"  Court: {parsed['court']}")
    print(f"  Result: {parsed['result']}")
    print("=" * 60)
    
    return parsed

# Full row processing function

def process_master_row(row_data: Union[pd.Series, dict, tuple, list],
                       offences_file: str = 'data/offence/all-criminal-offences-current.csv') -> dict:
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
    print("=" * 80)
    print("PROCESSING MASTER CSV ROW")
    print("=" * 80)
    print()
    
    # UID
    print("UID:")
    uid_parsed = parse_uid_string(uid)
    print(f"  Case ID: {uid_parsed['case_id']}")
    print(f"  Docket: {uid_parsed['docket']}")
    print(f"  Count: {uid_parsed['count']}")
    print(f"  Defendant: {uid_parsed['defendant']}")
    print()
    
    # Offence
    print("OFFENCE:")
    offence_parsed = parse_offence_string(offence, offences_file=offences_file)
    print(f"  Offence code: {offence_parsed['offence_code']}")
    print(f"  Offence name: {offence_parsed['offence_name']}")
    print()
    
    # Date
    print("DATE:")
    date_parsed = parse_date_string(date)
    if date_parsed['offence_date'] is not None:
        print(f"  Offence date: {date_parsed['offence_date']}")
    else:
        print(f"  Offence start date: {date_parsed['offence_start_date']}")
        print(f"  Offence end date: {date_parsed['offence_end_date']}")
    print()
    
    # Jail
    print("JAIL:")
    jail_df = parse_jail_string(jail)
    if isinstance(jail_df, str) and jail_df == "indeterminate":
        print("  Sentence: indeterminate")
        jail_total_days = None
    else:
        print("  Sentence components:")
        if not jail_df.empty:
            print(jail_df.to_string(index=False))
        else:
            print("  (no jail sentence)")
        jail_total_days = calculate_total_days(jail_df)
        print(f"  Total days: {jail_total_days}")
    print()
    
    # Mode
    print("MODE:")
    mode_parsed = parse_mode_string(mode)
    print(f"  Jail type: {mode_parsed[0]}")
    print(f"  Sentence mode: {mode_parsed[1]}")
    print()
    
    # Conditions
    print("CONDITIONS:")
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
        print(f"  Time length: {time} {unit}")
    else:
        print(f"  Time length: None")
    print(f"  Type: {cond_type}")
    print()
    
    # Fine
    print("FINE:")
    fine_formatted = parse_fine_string(fine)
    print(f"  Formatted fine: {fine_formatted}")
    print()
    
    # Appeal
    print("APPEAL:")
    appeal_parsed = parse_appeal_string(appeal)
    print(f"  Court: {appeal_parsed['court']}")
    print(f"  Result: {appeal_parsed['result']}")
    print()
    
    print("=" * 80)
    
    # Return all parsed data
    return {
        'uid': uid_parsed,
        'offence': offence_parsed,
        'date': date_parsed,
        'jail': {
            'components': jail_df if not isinstance(jail_df, str) else None,
            'total_days': jail_total_days,
            'is_indeterminate': isinstance(jail_df, str) and jail_df == "indeterminate"
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
