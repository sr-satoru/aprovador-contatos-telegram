"""
Storage Layer - Repositórios de persistência JSON e buffer de logs
"""
from storage.json_repository import JsonStorageRepository
from storage.log_buffer import LogBufferRepository

__all__ = ["JsonStorageRepository", "LogBufferRepository"]
