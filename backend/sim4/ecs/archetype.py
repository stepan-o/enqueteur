# archetype.py
def signature_of(components):
    """
    Components = tuple of component classes.
    Signature = tuple(sorted(component types)).
    """
    return tuple(sorted(components, key=lambda c: c.__name__))
