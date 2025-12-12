# parser/__init__.py
from .base import BaseParser
from .habr import HabrNewsParser
from .newsvl import NewsVLParser
from .ixbt import IXBTParser
from .nakedscience import NakedScienceParser
from .interfax import InterfaxParser

__all__ = [
    'BaseParser',
    'HabrNewsParser',
    'NewsVLParser',
    'IXBTParser',
    'NakedScienceParser',
    'InterfaxParser',
]
