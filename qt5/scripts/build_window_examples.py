"""使用 Windows SDK 的 qmake 构建原版 Qt 多窗口验收示例。"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
GRAPHICS = ROOT.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk", type=Path, default=Path(os.environ.get("LUNA_GRAPHICS_SDK", str(ROOT.parent.parent / "luna-sdk/qt5-5.15.19/staging"))).parent)
    parser.add_argument("--make", type=Path, required=True)
    args = parser.parse_args()
    qmake = args.sdk / "bin/qmake.exe"
    if not qmake.is_file() or not args.make.is_file():
        raise RuntimeError("必须提供已部署的 Windows Qt SDK 和 GNU make")
    environment = os.environ.copy()
    environment["PATH"] = str(args.make.parent) + os.pathsep + "C:/Program Files/Git/usr/bin" + os.pathsep + environment["PATH"]
    include_dirs = [GRAPHICS / "mesa/upstream/include", GRAPHICS / "mesa/upstream/src/gbm/main",
                    GRAPHICS / "libdrm/upstream", GRAPHICS / "libdrm/upstream/include/drm"]
    overrides = ["QMAKE_INCDIR=" + " ".join(path.as_posix() for path in include_dirs)]
    for variable in ("QMAKE_INCDIR_OPENGL", "QMAKE_INCDIR_OPENGL_ES2", "QMAKE_INCDIR_EGL"):
        overrides.append(variable + "=" + include_dirs[0].as_posix())
    overrides.append("QMAKE_INCDIR_DRM=" + " ".join(path.as_posix() for path in include_dirs[2:]))
    overrides.append("QMAKE_INCDIR_GBM=" + include_dirs[1].as_posix())
    artifacts = []
    for name in ("analogclock", "calculator"):
        source = ROOT / "upstream/qtbase-everywhere-src-5.15.19/examples/widgets/widgets" / name
        project = source / (name + ".pro")
        build = ROOT / "build/window-examples" / name
        output = ROOT / "output/window-examples" / (name + ".elf")
        if not project.is_file():
            raise RuntimeError(f"缺少固定的 Qt 上游示例：{project}")
        build.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(qmake), str(project), "CONFIG+=release", "CONFIG-=debug",
                        "TARGET=" + name + ".elf", *overrides], cwd=build,
                       env=environment, check=True)
        # 旧 SDK 的模块元数据仍带构建树路径，只重定位本次生成文件，
        # 不修改共享 SDK，也不让副本读取原 OS 的源码或历史库产物。
        makefile = build / "Makefile"
        text = makefile.read_text(encoding="utf-8")
        original = "D:/workspace/luna-workspace/os"
        text = text.replace(original + "/graphics/qt5/build/qt5-armv8a/staging/lib",
                            (args.sdk / "staging/lib").as_posix())
        # Relocate source metadata only; the explicit SDK may live under original.
        text = text.replace(original + "/graphics/", GRAPHICS.as_posix() + "/")
        non_sdk_text = text.replace(args.sdk.as_posix().rstrip("/") + "/", "")
        if original in non_sdk_text:
            raise RuntimeError("生成的 Makefile 仍依赖原 OS")
        makefile.write_text(text, encoding="utf-8")
        subprocess.run([str(args.make), "-s", "clean"], cwd=build,
                       env=environment, check=True)
        subprocess.run([str(args.make), "-s", "-j4"], cwd=build, env=environment, check=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(build / (name + ".elf"), output)
        artifacts.append({"example": name, "project": str(project.relative_to(ROOT)),
                          "artifact": output.name, "bytes": output.stat().st_size,
                          "sha256": hashlib.sha256(output.read_bytes()).hexdigest()})
    (ROOT / "output/window-examples/manifest.json").write_text(
        json.dumps({"qt": "5.15.19", "sdk": str(args.sdk), "artifacts": artifacts},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(artifacts, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
