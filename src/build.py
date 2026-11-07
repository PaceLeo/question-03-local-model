"""Build local llama.cpp and preserve configure/build output bytes."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timedelta, timezone


ROOT = Path(__file__).resolve().parents[1]
CMAKE = Path(r"C:\Program Files\CMake\bin\cmake.exe")
CUDA = Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.5")
VS = Path(r"C:\Program Files\Microsoft Visual Studio\18\Community")
SOURCE = ROOT / "vendor" / "llama.cpp"
BUILD = ROOT / "build" / "cuda"
STDOUT = ROOT / "build_log.txt"
STDERR = ROOT / "build_stderr.txt"
RECORD = ROOT / "docs" / "build_commands.json"
LOCAL_TZ = timezone(timedelta(hours=8))


def now():
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    for path in (CMAKE, CUDA / "bin" / "nvcc.exe", SOURCE / "CMakeLists.txt"):
        if not path.is_file():
            raise FileNotFoundError(path)
    if not VS.is_dir():
        raise FileNotFoundError(VS)
    for path in (STDOUT, STDERR, RECORD, BUILD):
        if path.exists():
            raise FileExistsError(f"Preserve the existing attempt before running again: {path}")

    env = os.environ.copy()
    overrides = {
        "GIT_CEILING_DIRECTORIES": str(ROOT / "vendor"),
        "CUDA_PATH": str(CUDA),
        "CUDA_PATH_V13_5": str(CUDA),
    }
    env.update(overrides)
    env["PATH"] = str(CUDA / "bin") + os.pathsep + env.get("PATH", "")
    configure = [
        str(CMAKE), "-S", "vendor/llama.cpp", "-B", "build/cuda",
        "-G", "Visual Studio 18 2026", "-A", "x64", "-T", "cuda=13.5",
        f"-DCMAKE_GENERATOR_INSTANCE={VS}",
        f"-DCUDAToolkit_ROOT={CUDA}",
        "-DCMAKE_CUDA_ARCHITECTURES=120a-real",
        "-DGGML_CUDA=ON", "-DLLAMA_OPENSSL=OFF",
        "-DLLAMA_BUILD_TESTS=OFF", "-DLLAMA_BUILD_EXAMPLES=OFF",
        "-DLLAMA_BUILD_APP=OFF", "-DLLAMA_BUILD_TOOLS=ON",
        "-DLLAMA_BUILD_SERVER=ON", "-DLLAMA_BUILD_UI=OFF",
        "-DLLAMA_USE_PREBUILT_UI=OFF", "-DLLAMA_CONNECT=OFF",
        "-DLLAMA_BUILD_NUMBER=0", "-DLLAMA_BUILD_COMMIT=unknown",
    ]
    build = [
        str(CMAKE), "--build", "build/cuda", "--config", "Release",
        "--target", "llama-cli", "llama-server", "llama-quantize", "--parallel", "8",
    ]
    record = {
        "started_at": now(), "working_directory": str(ROOT),
        "stdout": STDOUT.name, "stderr": STDERR.name,
        "capture": "Direct binary file handles; configure stdout followed by build stdout, with no inserted text.",
        "environment_overrides": overrides,
        "path_prefix": str(CUDA / "bin"),
        "upstream_revision": "unknown: user-provided source archive without .git",
        "source_cmakelists_sha256": sha256(SOURCE / "CMakeLists.txt"),
        "gpu_architecture": "120a-real (local RTX 5080, compute capability 12.0)",
        "stages": [],
    }
    RECORD.parent.mkdir(parents=True, exist_ok=True)

    def save():
        RECORD.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    save()
    exit_code = 0
    with STDOUT.open("xb", buffering=0) as stdout, STDERR.open("xb", buffering=0) as stderr:
        for stage, argv in (("configure", configure), ("build", build)):
            entry = {
                "stage": stage, "argv": argv,
                "command_windows": subprocess.list2cmdline(argv),
                "started_at": now(),
                "stdout_start_byte": STDOUT.stat().st_size,
                "stderr_start_byte": STDERR.stat().st_size,
            }
            record["stages"].append(entry)
            save()
            print(f"[{now()}] Starting {stage}; raw output -> {STDOUT.name}, {STDERR.name}", flush=True)
            try:
                result = subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, check=False)
                exit_code = result.returncode
                entry["exit_code"] = exit_code
            except OSError as error:
                entry["launch_error"] = str(error)
                exit_code = 1
            entry.update({
                "finished_at": now(),
                "stdout_end_byte": STDOUT.stat().st_size,
                "stderr_end_byte": STDERR.stat().st_size,
            })
            save()
            print(f"[{now()}] {stage}: exit {exit_code}, stdout {entry['stdout_end_byte']} bytes", flush=True)
            if exit_code != 0:
                break

    record["finished_at"] = now()
    record["exit_code"] = exit_code
    record["stdout_sha256"] = sha256(STDOUT)
    record["stderr_sha256"] = sha256(STDERR)
    record["artifacts"] = []
    if exit_code == 0:
        for name in ("llama-cli.exe", "llama-server.exe", "llama-quantize.exe"):
            artifact = BUILD / "bin" / "Release" / name
            record["artifacts"].append({
                "path": artifact.relative_to(ROOT).as_posix(),
                "bytes": artifact.stat().st_size,
                "sha256": sha256(artifact),
            })
    save()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
