import hashlib
import io
from pathlib import Path
from typing import Tuple, Dict, Optional
from PIL import Image


class HashVerifiedVault:
    """
    Manages hash-verified file storage and computes exact SHA-256 checksums
    alongside advisory perceptual hashes (dHash) for cross-institution duplicate detection.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir is None:
            storage_dir = str(Path(__file__).parent.parent.parent / "data" / "vault")
        self.storage_path = Path(storage_dir)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._registry: Dict[str, str] = {}  # sha256 -> file_id

    @staticmethod
    def compute_sha256(file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    @staticmethod
    def compute_dhash(image_bytes: bytes, hash_size: int = 8) -> str:
        """
        Computes difference hash (dHash) as a lightweight advisory perceptual hash.
        """
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("L").resize(
                (hash_size + 1, hash_size), Image.Resampling.LANCZOS
            )
            pixels = list(image.getdata())
            diff = []
            for row in range(hash_size):
                for col in range(hash_size):
                    left = pixels[row * (hash_size + 1) + col]
                    right = pixels[row * (hash_size + 1) + col + 1]
                    diff.append(left > right)
            decimal_value = 0
            hex_string = []
            for index, value in enumerate(diff):
                if value:
                    decimal_value += 2 ** (index % 8)
                if (index % 8) == 7:
                    hex_string.append(hex(decimal_value)[2:].rjust(2, "0"))
                    decimal_value = 0
            return "".join(hex_string)
        except Exception:
            return ""

    def store_file(self, filename: str, file_bytes: bytes) -> Tuple[str, Path]:
        """
        Stores file verified by SHA-256 checksum.
        Returns (sha256_hash, stored_file_path).
        """
        file_hash = self.compute_sha256(file_bytes)
        file_path = self.storage_path / f"{file_hash}_{filename}"
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        self._registry[file_hash] = filename
        return file_hash, file_path

    def verify_integrity(self, file_path: Path, expected_sha256: str) -> bool:
        """Verifies that the stored file has not been altered or modified."""
        if not file_path.exists():
            return False
        with open(file_path, "rb") as f:
            current_hash = hashlib.sha256(f.read()).hexdigest()
        return current_hash == expected_sha256
