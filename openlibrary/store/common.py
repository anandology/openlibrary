"""Library of common functions used by many views.
"""

TYPE_EDITION = "/type/edition"

OTHER_EDITION_IDS = "isbn_10 isbn_13 lccn oclc_numbers ia_box_id".split()

def get_edition_identifiers(doc):
    """Returns a dict all identifiers of the edition, including 'isbn_10', 'isbn_13' etc.
    """
    ids = doc.get('identifiers', {})
    for k in OTHER_EDITION_IDS:
        if k in doc:
            ids[k] = doc[k]
        
    # ocaid is the IA identifier. Call it as "ia" and treat it just like other identifiers
    if 'ocaid' in doc:
        ids['ia'] = [doc['ocaid']]
        
    return ids

def get_type(doc):
    return doc['type']['key']