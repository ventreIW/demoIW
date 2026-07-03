from abc import ABC, abstractmethod

from app.domain.value_objects.raw_dataset import RawDataset


class IDatasetPort(ABC):
    """Abstract port for synthetic dataset generation.

    Synchronous by design: generation is CPU-bound (numeric sampling), not I/O,
    so it does not follow the async convention of the persistence repository ports.
    """

    @abstractmethod
    def generate(self) -> RawDataset:
        """Produce a RawDataset of clients, invoices, and payments."""
        ...
