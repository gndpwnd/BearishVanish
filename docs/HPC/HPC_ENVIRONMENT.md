# HPC Environment Test Results

**Test Date:** December 20, 2025
**Tested By:** Automated testing via Claude Code

---

## Executive Summary

| Component | Status | Notes |
|-----------|--------|-------|
| SSH Connectivity | Working | Both login and GPU nodes accessible |
| GPU Hardware | Working | 4x NVIDIA H100 80GB operational |
| CUDA | Working | Version 12.2, Driver 535.129.03 |
| Vivado 2024.2 | Working | Fully installed and functional |
| MATLAB R2024b | Pending | Installer extracted, needs license |
| Ollama | Working | 20 models available, GPU-accelerated |

---

## Node Specifications

### Login Node: vegaln1.erau.edu

| Spec | Value |
|------|-------|
| Hostname | vegaln1 |
| OS | Linux 4.18.0-553.89.1.el8_10.x86_64 (RHEL 8) |
| CPU | 2x AMD EPYC 9654 96-Core Processor |
| Total Cores | 192 |
| RAM | 1.5 TB |
| Storage | 228 TB shared (PanFS), 153 TB available |
| Internet | Yes |
| GPUs | No |

### GPU Node: gpu02

| Spec | Value |
|------|-------|
| Hostname | gpu02 |
| OS | Linux 4.18.0-553.89.1.el8_10.x86_64 (RHEL 8) |
| CPU | 2x AMD EPYC 9654 96-Core Processor |
| Total Cores | 192 |
| RAM | 1.5 TB |
| Internet | No |
| GPUs | 4x NVIDIA H100 PCIe |

---

## GPU Hardware Details

**Driver Version:** 535.129.03
**CUDA Version:** 12.2

| GPU | UUID | Memory | Temp | Power |
|-----|------|--------|------|-------|
| 0 | GPU-d892d94d-d502-7e6c-2a97-d08d177b9e6a | 80 GB | 35°C | 50W/350W |
| 1 | GPU-3ef7c1c1-bd97-d22d-9726-44078651ca0c | 80 GB | 31°C | 45W/350W |
| 2 | GPU-4cefde4d-4332-d2ba-8886-90cd6e553907 | 80 GB | 35°C | 51W/350W |
| 3 | GPU-397f9662-625b-1c89-fdf1-929344193e97 | 80 GB | 33°C | 45W/350W |

**Total GPU Memory:** 320 GB VRAM

**CUDA Libraries Location:**
- `/usr/local/cuda-12.2/lib64/`
- `/usr/local/cuda-12/targets/x86_64-linux/lib/`

---

## Software Status

### Vivado 2024.2

**Status:** Fully Installed and Working

**Location:** `/home2/nelsg10/vivado/`

**Version Info:**
```
vivado v2024.2 (64-bit)
Tool Version Limit: 2024.11
SW Build 5239630 on Fri Nov 08 22:34:34 MST 2024
```

**Installed Components:**
- Vivado Design Suite: `/home2/nelsg10/vivado/Vivado/2024.2/`
- Vitis: `/home2/nelsg10/vivado/Vitis/2024.2/`
- Vitis HLS: `/home2/nelsg10/vivado/Vitis_HLS/2024.2/`
- Model Composer: `/home2/nelsg10/vivado/Model_Composer/2024.2/`
- DocNav: `/home2/nelsg10/vivado/DocNav/`

**Usage:**
```bash
source ~/vivado/Vivado/2024.2/settings64.sh
vivado -mode batch -source build.tcl
```

**License Status:** Not configured (needs XILINXD_LICENSE_FILE)

**GPU Acceleration:** NOT SUPPORTED (CPU-only for synthesis/implementation)

---

### MATLAB R2024b

**Status:** Installer Ready, Not Yet Installed

**Installer Location:** `/home2/nelsg10/outsourcing/matlab_installer/`

**Installer Type:** Online installer (requires internet during installation)

**Installation Requirements:**
1. File Installation Key (from MathWorks account)
2. Network license server OR license file
3. Internet access (on login node)

**Planned Installation Path:** `/home2/nelsg10/matlab/R2024b/`

**GPU Acceleration:** YES (via Parallel Computing Toolbox)
- Supports `gpuArray` for GPU computing
- CUDA 12.2 compatible with MATLAB R2024b
- H100 GPUs supported (may need CUDA forward compatibility mode)

**Next Steps for MATLAB:**
1. Obtain File Installation Key from MathWorks
2. Identify license server or get license file
3. Create `installer_input.txt` configuration
4. Run silent installation on login node
5. Test GPU functionality on gpu02

---

### Ollama

**Status:** Fully Working with GPU Acceleration

**Version:** 0.13.1

**Binary Location:** `/home2/nelsg10/.local/bin/ollama/bin/ollama`

**Models Directory:** `/home2/nelsg10/.ollama/models/`

**Running Instances:**
- Port 11434: Active (CUDA_VISIBLE_DEVICES=0)
- Port 11435: Active (All 4 GPUs)

**Available Models (20 total):**

| Model | Size | Parameters | Quantization |
|-------|------|------------|--------------|
| deepseek-r1:671b | 404 GB | 671B | Q4_K_M |
| qwen3-coder:480b | 290 GB | 480B | Q4_K_M |
| deepseek-coder-v2:236b | 133 GB | 236B | Q4_0 |
| llama3.3:70b-instruct-q5_K_M | 50 GB | 70.6B | Q5_K_M |
| llama3.1:70b | 43 GB | 70.6B | Q4_K_M |
| deepseek-r1:70b | 43 GB | 70.6B | Q4_K_M |
| qwen2.5-coder:32b | 20 GB | 32.8B | Q4_K_M |
| qwen3-coder:30b | 19 GB | 30.5B | Q4_K_M |
| codestral:22b | 13 GB | 22.2B | Q4_0 |
| deepseek-coder-v2:16b | 9 GB | 15.7B | Q4_0 |
| deepseek-r1:8b | 5.2 GB | 8.2B | Q4_K_M |
| deepseek-r1:7b | 4.7 GB | 7.6B | Q4_K_M |
| qwen2.5-coder:7b | 4.7 GB | 7.6B | Q4_K_M |
| llama3:8b | 4.7 GB | 8.0B | Q4_0 |
| llama3.2:3b-instruct-q5_K_M | 2.3 GB | 3.2B | Q5_K_M |
| gemma2:2b | 1.6 GB | 2.6B | Q4_0 |
| llama3.2:1b-instruct-q4_K_M | 0.8 GB | 1.2B | Q4_K_M |
| nomic-embed-text:latest | 0.3 GB | 137M | F16 |
| all-minilm:l6-v2 | 46 MB | 23M | F16 |
| kimi-k2-thinking:cloud | Remote | 1T | INT4 |

**API Test:**
```bash
curl http://127.0.0.1:11435/api/tags  # Returns model list successfully
```

**Inference Test (2025-12-20):**
- Model: deepseek-r1:7b
- Prompt: "What is 2+2? Answer in one word."
- Response: "4" (with full chain-of-thought reasoning)
- Total time: 24.2 seconds (including 20s model load)
- Inference time: ~3.3 seconds for 580 tokens
- Speed: ~175 tokens/second
- GPU Memory used: ~5.3 GB on GPU 0

---

## Filesystem Structure

```
/home2/nelsg10/
├── outsourcing/                    # Software installers
│   └── matlab_installer/           # Extracted MATLAB installer
├── vivado/                         # Vivado 2024.2 installation
│   ├── Vivado/2024.2/
│   ├── Vitis/2024.2/
│   ├── Vitis_HLS/2024.2/
│   └── Model_Composer/2024.2/
├── vivado_tmp/                     # Vivado installer files
├── .local/bin/ollama/              # Ollama binary
├── .ollama/                        # Ollama models and config
└── MJ/                             # Project directory
```

**Storage:**
- Filesystem: PanFS (10.14.0.111:/home2)
- Total: 228 TB
- Used: 75 TB
- Available: 153 TB
- Mount point: /home2

---

## Network Configuration

### SSH Access Pattern

```
Local Machine
     │
     │ SSH (Port 22)
     ▼
┌─────────────────────────────┐
│   vegaln1.erau.edu          │
│   (Login/Jump Node)         │
│   - Internet: YES           │
│   - GPUs: NO                │
└─────────────────────────────┘
     │
     │ SSH (internal)
     ▼
┌─────────────────────────────┐
│   gpu01 / gpu02             │
│   (GPU Compute Nodes)       │
│   - Internet: NO            │
│   - GPUs: 4x H100           │
└─────────────────────────────┘
```

### Connection Commands

```bash
# Direct to login node
ssh nelsg10@vegaln1.erau.edu

# To GPU node via jump host
ssh -J nelsg10@vegaln1.erau.edu nelsg10@gpu02

# Port forwarding (e.g., for Ollama)
ssh -L 11434:localhost:11434 -J nelsg10@vegaln1.erau.edu nelsg10@gpu02
```

---

## Constraints and Workarounds

### No Sudo Access
- All software must be installed to user directories
- Cannot modify system PATH or libraries
- Use `~/.local/bin/` for user binaries
- Source settings scripts manually

### GPU Nodes Have No Internet
- Download all software on login node
- Use shared filesystem to transfer to GPU nodes
- For Ollama: Pull models on login node (but can't use GPU there)
- **Workaround for Ollama models:** Use `scp` or download on internet-connected machine and upload

### Software Requiring Internet During Installation
- MATLAB online installer needs internet
- Solution: Run installer on login node, install to shared path
- GPU node can then access the installation

### License Servers
- Vivado: Needs XILINXD_LICENSE_FILE configured
- MATLAB: Needs MLM_LICENSE_FILE or network.lic

---

## Recommendations

### Immediate Actions
1. **Configure Vivado license** - Set XILINXD_LICENSE_FILE in ~/.bashrc
2. **Install MATLAB** - Get license key and run silent install
3. **Set up environment** - Create ~/.bashrc aliases for common operations

### ~/.bashrc Additions
```bash
# Vivado
source ~/vivado/Vivado/2024.2/settings64.sh
export XILINXD_LICENSE_FILE=2100@license.erau.edu  # Update with actual server

# MATLAB (after installation)
export PATH="~/matlab/R2024b/bin:$PATH"
export MLM_LICENSE_FILE=27000@license.erau.edu  # Update with actual server

# Ollama
export PATH="~/.local/bin/ollama/bin:$PATH"

# CUDA
export PATH="/usr/local/cuda-12.2/bin:$PATH"
export LD_LIBRARY_PATH="/usr/local/cuda-12.2/lib64:$LD_LIBRARY_PATH"
```

### Performance Optimization
- **Vivado:** Use 8 threads max (`set_param general.maxThreads 8`)
- **MATLAB:** Use `parpool('local', 4)` for 4 GPU workers
- **Ollama:** Large models (>70B) automatically span multiple GPUs

---

## Test Commands Reference

```bash
# Check GPU status
ssh -J nelsg10@vegaln1.erau.edu nelsg10@gpu02 "nvidia-smi"

# Test Vivado
ssh nelsg10@vegaln1.erau.edu "source ~/vivado/Vivado/2024.2/settings64.sh && vivado -version"

# Test Ollama API
ssh -J nelsg10@vegaln1.erau.edu nelsg10@gpu02 "curl -s http://127.0.0.1:11435/api/tags | jq '.models[].name'"

# Check disk space
ssh nelsg10@vegaln1.erau.edu "df -h /home2"

# Monitor GPU usage
ssh -J nelsg10@vegaln1.erau.edu nelsg10@gpu02 "watch -n 1 nvidia-smi"
```

---

## Appendix: Raw Test Output

### nvidia-smi Output (2025-12-20)
```
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 535.129.03             Driver Version: 535.129.03   CUDA Version: 12.2      |
|-----------------------------------------+------------------------+---------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC|
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M.|
|=========================================+========================+=====================|
|   0  NVIDIA H100 PCIe               On  | 00000000:02:00.0 Off  |                    0|
| N/A   35C    P0              50W / 350W |        4MiB / 81559MiB |      0%      Default|
+-----------------------------------------+------------------------+---------------------+
|   1  NVIDIA H100 PCIe               On  | 00000000:64:00.0 Off  |                    0|
| N/A   31C    P0              45W / 350W |        4MiB / 81559MiB |      0%      Default|
+-----------------------------------------+------------------------+---------------------+
|   2  NVIDIA H100 PCIe               On  | 00000000:82:00.0 Off  |                    0|
| N/A   35C    P0              51W / 350W |        4MiB / 81559MiB |      0%      Default|
+-----------------------------------------+------------------------+---------------------+
|   3  NVIDIA H100 PCIe               On  | 00000000:E3:00.0 Off  |                    0|
| N/A   33C    P0              45W / 350W |        4MiB / 81559MiB |      0%      Default|
+-----------------------------------------+------------------------+---------------------+
```
