from abc import ABC, abstractmethod

from app.core.types import BackendType, CoreType


class AbstractCore(ABC):
    @abstractmethod
    def __init__(self, config: dict, exclude_inbound_tags: list[str], fallbacks_inbound_tags: list[str]) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def backend_type(self) -> BackendType:
        raise NotImplementedError

    @property
    @abstractmethod
    def core_type(self) -> CoreType:
        raise NotImplementedError

    @property
    @abstractmethod
    def exclude_inbound_tags(self) -> set[str]:
        raise NotImplementedError

    @abstractmethod
    def to_str(self, **json_kwargs) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def inbounds_by_tag(self) -> dict:
        raise NotImplementedError

    @property
    @abstractmethod
    def inbounds(self) -> list[str]:
        raise NotImplementedError
