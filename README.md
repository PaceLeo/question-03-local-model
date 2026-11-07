# OpenLab 2026 第 3 题：本地模型部署

本仓库独立记录第 3 题的源码编译、GPU/CPU 模型推理、原始日志、截图和书面答案。所有结果均来自本机实际执行。

## 已完成内容

- [x] 为第 3 题建立独立 Git 仓库。
- [x] 将题目提供的 `gemma-4-E2B-it-Q4_0.gguf` 放入 `models/`；模型文件只在本地保留，不提交到 Git。
- [x] 使用 CUDA 13.5、Visual Studio 2026 和 CMake 从 `vendor/llama.cpp/` 完成 GPU 构建。
- [x] 使用自行编译的 `llama-cli` 完成 GPU 推理，生成速度为 `264.6 token/s`。
- [x] 使用同一模型和 prompt 完成 CPU 对照，生成速度为 `33.1 token/s`。
- [x] 保存完整构建日志、命令元数据、推理输出和真实截图。
- [x] 在 [`docs/answers.md`](docs/answers.md) 中回答命令参数、日志解释和 GPU/CPU 对比问题。

## 环境与结果

| 项目 | 实际值 |
| --- | --- |
| GPU | NVIDIA GeForce RTX 5080，约 16 GB VRAM，compute capability 12.0 |
| CPU | Intel Core Ultra 7 270K Plus |
| CUDA Toolkit | 13.5.37 |
| Visual Studio | 2026 Community 18.11.3，MSVC 19.51.36260.0 |
| CMake | 4.5.0-rc3 |
| CMake CUDA 架构 | `120a-real` |
| 模型格式 | Gemma 4 E2B Instruct，GGUF `Q4_0` |
| 模型 SHA-256 | `8e30dff3ac4c8434c49a7036fa15564bdbb6044e42bf04550bf1a096ad7e6a52` |

成功构建的主要产物位于 `build/cuda/bin/Release/`，包括 `llama-cli.exe`、`llama-server.exe` 和 `llama-quantize.exe`。构建本身的完整 stdout 保存在 [`build_log.txt`](build_log.txt)，stderr 保存在 [`build_stderr.txt`](build_stderr.txt)。

运行 GPU 可执行文件时，CUDA DLL 位于 Toolkit 的 `bin\x64`，因此运行时 PATH 必须包含以下前缀：

```text
build\cuda\bin\Release
C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.5\bin\x64
C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.5\bin
```

## 复现实验

GPU 推理使用的完整命令和退出码保存在 [`docs/gpu_q4_command.json`](docs/gpu_q4_command.json)，实际 stdout 保存在 [`docs/gpu_q4_stdout.txt`](docs/gpu_q4_stdout.txt)：

```powershell
build/cuda/bin/Release/llama-cli.exe `
  -m models/gemma-4-E2B-it-Q4_0.gguf `
  -f docs/prompt-baseline.txt `
  -n 96 -t 8 -tb 8 -ngl all -c 2048 `
  --single-turn --simple-io --offline --no-mmproj `
  --perf --show-timings --reasoning off --fit off `
  --temp 0 --seed 42 --color off --no-display-prompt
```

GPU 输出中的回答第一句是：

> 开源软件是指软件的源代码可以被任何人查看、修改和分发的软件，它通常遵循特定的开源许可协议。

GPU 实测为 `Prompt: 154.9 t/s`、`Generation: 264.6 t/s`。CPU 对照只把 `-ngl all` 改为 `-ngl 0`，实测为 `Generation: 33.1 t/s`，GPU 约为 CPU 的 `8.0x`。

真实截图见 [`res/gpu_q4_evidence.png`](res/gpu_q4_evidence.png)，截图对应的可读证据文本见 [`res/gpu_q4_evidence.txt`](res/gpu_q4_evidence.txt)。

## 构建记录

构建参数、时间、退出码、日志哈希和产物哈希保存在 [`docs/build_commands.json`](docs/build_commands.json)。构建脚本是 [`src/build.py`](src/build.py)。

第一次构建发生在中文路径 `Openlab纳新` 下，因 MSVC 报告 `MSB8084`（结构化输出中的无效 UTF-8）失败；完整日志和当时的脚本已归档于 [`docs/attempts/01-chinese-path/`](docs/attempts/01-chinese-path/)，没有覆盖。将工作目录改为英文名 `Openlab` 后，第二次构建成功。该记录只描述实际构建过程，不把环境问题包装成额外加分项。

上游源码是用户提供的源码目录，`vendor/llama.cpp/` 本身没有 `.git`，因此上游提交号记录为 `unknown`，不会冒充本仓库提交号。

## 目录说明

```text
question-03-local-model/
  src/                 可复用的构建脚本
  docs/                命令元数据、原始推理输出、答案和失败记录
  res/                 真实截图和截图对应的文字证据
  models/              本地模型权重（被 .gitignore 排除）
  vendor/llama.cpp/    第三方源码（被 .gitignore 排除）
  build/               本机编译产物（被 .gitignore 排除）
  build_log.txt        未删改、未截断的构建 stdout
```

Token、模型权重、第三方源码和编译产物均不会提交；原始日志和实验元数据保留用于复核.
