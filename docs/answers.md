# 第 3 题书面答案

## 1. 编译命令与结果

本题在英文路径 `C:\Users\Administrator\Documents\Openlab\question-03-local-model` 中完成。配置阶段使用 Visual Studio 2026 生成器和 CUDA 13.5：

```powershell
cmake -S vendor/llama.cpp -B build/cuda -G "Visual Studio 18 2026" -A x64 -T cuda=13.5 `
  "-DCMAKE_GENERATOR_INSTANCE=C:\Program Files\Microsoft Visual Studio\18\Community" `
  "-DCUDAToolkit_ROOT=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.5" `
  -DCMAKE_CUDA_ARCHITECTURES=120a-real `
  -DGGML_CUDA=ON -DLLAMA_OPENSSL=OFF `
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF `
  -DLLAMA_BUILD_APP=OFF -DLLAMA_BUILD_TOOLS=ON `
  -DLLAMA_BUILD_SERVER=ON -DLLAMA_BUILD_UI=OFF `
  -DLLAMA_USE_PREBUILT_UI=OFF -DLLAMA_CONNECT=OFF `
  -DLLAMA_BUILD_NUMBER=0 -DLLAMA_BUILD_COMMIT=unknown

cmake --build build/cuda --config Release `
  --target llama-cli llama-server llama-quantize --parallel 8
```

两阶段退出码都是 `0`。完整原始 stdout 在 [`../build_log.txt`](../build_log.txt)，stderr 在 [`../build_stderr.txt`](../build_stderr.txt)，机器可读记录在 [`build_commands.json`](build_commands.json)。

第一次在中文目录中构建时出现：

```text
MSB8084: “CL.exe”的结构化输出无效: Cannot transcode invalid UTF-8 JSON text to UTF-16 string.
```

这次失败的日志、命令和脚本保存在 [`attempts/01-chinese-path/`](attempts/01-chinese-path/)。改用英文目录后成功；失败记录没有被覆盖。

## 2. GPU 推理命令与回答

提示词文件是 [`prompt-baseline.txt`](prompt-baseline.txt)：

```text
请用三句话向大学新生解释什么是开源软件，并给出一个例子。
```

完整 GPU 命令如下：

```powershell
build/cuda/bin/Release/llama-cli.exe `
  -m models/gemma-4-E2B-it-Q4_0.gguf -f docs/prompt-baseline.txt `
  -n 96 -t 8 -tb 8 -ngl all -c 2048 `
  --single-turn --simple-io --offline --no-mmproj `
  --perf --show-timings --reasoning off --fit off `
  --temp 0 --seed 42 --color off --no-display-prompt
```

命令的 JSON 记录和实际输出分别在 [`gpu_q4_command.json`](gpu_q4_command.json) 与 [`gpu_q4_stdout.txt`](gpu_q4_stdout.txt)。运行时 PATH 需要把 `build/cuda/bin/Release`、CUDA `bin\x64` 和 CUDA `bin` 放在前面。

回答第一句是：

> 开源软件是指软件的源代码可以被任何人查看、修改和分发的软件，它通常遵循特定的开源许可协议。

实际 timing 为：

```text
[ Prompt: 154.9 t/s | Generation: 264.6 t/s ]
```

因此本题报告的 GPU 生成速度是 **264.6 token/s**。真实截图是 [`../res/gpu_q4_evidence.png`](../res/gpu_q4_evidence.png)。

## 3. 从构建日志中选三行解释

以下三行直接来自 [`../build_log.txt`](../build_log.txt)：

1. `-- The CUDA compiler identification is NVIDIA 13.5.37 with host compiler MSVC 19.51.36260.0`

   CMake 已识别 CUDA 编译器版本为 13.5.37，并确认 CUDA 使用的宿主 C++ 编译器是 MSVC 19.51.36260.0。这说明配置阶段确实走的是本机安装的 CUDA + Visual Studio 工具链。

2. `-- Using CMAKE_CUDA_ARCHITECTURES=120a-real CMAKE_CUDA_ARCHITECTURES_NATIVE=120a-real`

   生成的 CUDA 代码针对本机 RTX 5080 的 compute capability 12.0。 `120a-real` 是实际生成并编译的目标架构，而不是只在运行时依赖 JIT 的通用设置。

3. `ggml-cuda.vcxproj -> C:\Users\Administrator\Documents\Openlab\question-03-local-model\build\cuda\bin\Release\ggml-cuda.dll`

   MSBuild 已经把 CUDA 后端项目链接成 Release 配置的 `ggml-cuda.dll`。它是运行 `llama-cli` 时负责 GPU 张量计算的动态库之一；最终可执行文件和依赖 DLL 位于同一个 Release 目录。

## 4. 参数解释

- `-n 96`（`--n-predict`）限制本次最多生成 96 个 token。它控制生成上限，不保证一定生成满 96 个 token。
- `-t 8`（`--threads`）设置生成阶段使用的 CPU 线程数；`-tb 8` 设置 prompt/batch 阶段的 CPU 线程数。本实验固定两者为 8，便于 GPU 与 CPU 对照。
- `-ngl all`（`--n-gpu-layers`）要求尽可能把模型层放进 GPU。这里同时使用 `--fit off`，所以显式指定的 GPU 层数不会被自动降低；显存不足时会加载失败。若使用默认的自动适配策略，`--fit` 只能调整用户没有显式指定的参数。

### `-t 1` 会发生什么

把 `-t 8` 改为 `-t 1` 只会把生成阶段的 CPU 线程并行度降为一个，不会关闭 CUDA，也不会自动把 `-ngl all` 改成 CPU。GPU 层仍可继续放在 VRAM 中，但 CPU 侧工作并行度降低，通常会让整体速度变慢；prompt 阶段还由 `-tb` 单独控制。

### 请求的 GPU 层数超过显存时

如果没有显式指定不适合当前显存的层数，默认自动适配/`--fit on` 可以尝试减少未显式设置的 GPU 层数或调整相关参数。如果用户明确写了 `-ngl`，源码会把它视为用户请求；在 `--fit off` 下不会替用户降层，而是在加载时报告显存不足并退出。 `-ngl all` 也属于“尽可能全放 GPU”的显式请求，因此本实验选择记录真实成功结果，不把自动降级假设写成结果。

## 5. GPU 与 CPU 对照

CPU 对照命令与 GPU 命令相同，只把 `-ngl all` 改为 `-ngl 0`，仍使用 `-t 8 -tb 8`、相同模型、prompt、seed 和温度。记录在 [`cpu_q4_t8_command.json`](cpu_q4_t8_command.json)，输出在 [`cpu_q4_t8_stdout.txt`](cpu_q4_t8_stdout.txt)。

| 模式 | GPU 层数 | Generation |
| --- | ---: | ---: |
| RTX 5080 GPU | `all` | **264.6 token/s** |
| CPU 对照 | `0` | **33.1 token/s** |

本次 GPU 速度约为 CPU 的 `264.6 / 33.1 ≈ 8.0x`。两次回答都完成了题目要求；由于模型采样参数固定为 `temperature=0`、`seed=42`，输出可复核但不要求 GPU 和 CPU 的措辞完全相同。

## 6. 已构建但未宣称完成的项目

`llama-server.exe` 和 `llama-quantize.exe` 已随构建目标生成，并未在本次记录中冒充已完成的 server API 或量化加分实验。仓库只报告已经实际运行并保存证据的 GPU 推理、CPU 对照和构建过程。
