"""SEC form parsers registry and factory."""

from typing import Type, Dict
from .base import BaseFormParser

# Registry will be populated as parsers are imported
_PARSER_REGISTRY: Dict[str, Type[BaseFormParser]] = {}


def register_parser(form_type: str, parser_class: Type[BaseFormParser]) -> None:
    """Register a parser for a specific form type."""
    _PARSER_REGISTRY[form_type] = parser_class


def get_parser(form_type: str) -> BaseFormParser:
    """Get a parser instance for the specified form type.
    
    Args:
        form_type: SEC form type (e.g., '144', '8-K', '4')
        
    Returns:
        Parser instance for the form type
        
    Raises:
        ValueError: If no parser is registered for the form type
    """
    parser_class = _PARSER_REGISTRY.get(form_type)
    if not parser_class:
        raise ValueError(f"No parser registered for form type: {form_type}")
    return parser_class()


def get_supported_forms() -> list[str]:
    """Get list of supported form types."""
    return list(_PARSER_REGISTRY.keys())
