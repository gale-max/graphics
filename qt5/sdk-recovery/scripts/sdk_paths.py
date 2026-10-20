"""Keep Qt SDK host and target build products in separate directories."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SdkPaths:
    """Preserve the SDK layout from repository commit aeb13bf1."""

    build_root: Path

    @property
    def host_linux(self) -> Path:
        return self.build_root / "host-linux"

    @property
    def host_windows(self) -> Path:
        return self.build_root / "host-windows"

    @property
    def target(self) -> Path:
        return self.build_root / "target-armv8a-luna"

    @property
    def package_root(self) -> Path:
        return self.build_root / "package" / "qt5-luna-armv8a-5.15.19"
