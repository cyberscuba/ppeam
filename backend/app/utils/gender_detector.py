"""
Gender detection utility for Spanish names
Detects if a name is typically male (Hermano) or female (Hermana)
"""
import re

# Common Spanish name endings and patterns
FEMALE_ENDINGS = [
    'a', 'ia', 'ina', 'ana', 'ela', 'ela', 'ila', 'ola', 'ula',
    'ella', 'illa', 'ella', 'ella', 'ella', 'ella'
]

FEMALE_NAMES = {
    'maria', 'maría', 'ana', 'luz', 'dora', 'rosa', 'carmen', 'laura',
    'patricia', 'gloria', 'sandra', 'carolina', 'diana', 'claudia',
    'liliana', 'jackeline', 'yuliana', 'yamelis', 'lady', 'daniela',
    'lina', 'luz', 'adriana', 'guendy', 'yesenia', 'sarah', 'liyang'
}

MALE_NAMES = {
    'juan', 'carlos', 'luis', 'jose', 'jhon', 'jairo', 'gustavo',
    'gerardo', 'ivan', 'isaias', 'francedy', 'yeison', 'ricardo'
}

def detect_gender_from_name(full_name: str) -> str:
    """
    Detect gender from full name
    Returns: 'hermano' or 'hermana'
    """
    if not full_name or not isinstance(full_name, str):
        return 'hermano'  # Default
    
    # Normalize: lowercase, remove extra spaces
    name_clean = re.sub(r'\s+', ' ', full_name.lower().strip())
    
    # Split into words
    name_parts = name_clean.split()
    
    if not name_parts:
        return 'hermano'
    
    # Check first name (most reliable indicator)
    first_name = name_parts[0]
    
    # Remove common prefixes
    first_name = re.sub(r'^(doña|don|sr|sra|srta|dr|dra)\.?\s*', '', first_name)
    
    # Check against known name lists
    if first_name in FEMALE_NAMES:
        return 'hermana'
    
    if first_name in MALE_NAMES:
        return 'hermano'
    
    # Check ending patterns (Spanish names often end in 'a' for female)
    # But be careful with names like "José", "Luis", etc.
    if len(first_name) > 2:
        # Female endings
        for ending in FEMALE_ENDINGS:
            if first_name.endswith(ending) and len(first_name) > len(ending):
                # Exceptions: names that end in 'a' but are male
                if first_name not in ['jose', 'josé', 'juan', 'jhon', 'jairo']:
                    return 'hermana'
    
    # Check for compound names like "Maria Jose" -> likely female
    if len(name_parts) > 1:
        if any(part in FEMALE_NAMES for part in name_parts[:2]):
            return 'hermana'
        if any(part in MALE_NAMES for part in name_parts[:2]):
            return 'hermano'
    
    # Default to 'hermano' if uncertain
    return 'hermano'

def get_gender_label(full_name: str) -> str:
    """
    Get the appropriate label: 'Hermano' or 'Hermana'
    """
    gender = detect_gender_from_name(full_name)
    return 'Hermana' if gender == 'hermana' else 'Hermano'

