"""Data-access adapters for the enhanced dashboard."""

from .base import AnimalRepository
from .csv_repository import CsvAnimalRepository
from .mongo_repository import MongoAnimalRepository

__all__ = ["AnimalRepository", "CsvAnimalRepository", "MongoAnimalRepository"]
