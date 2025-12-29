# HPC Cluster Outsourcing Guide

## Overview

This guide documents how to outsource computational workloads to your HPC cluster with the following architecture:

```
Local Machine
     |
     | SSH
     v
+------------------+
| vegaln1.erau.edu |  <-- Login/Jump Node (Internet, NO GPUs)
+------------------+
     |
     | SSH (internal)
     v
+------------------+
| gpu01 / gpu02    |  <-- GPU Nodes (NO Internet, 4x NVIDIA H100 80GB each)
+------------------+
```

**Key Constraints:**
- No `sudo` access on any node
- GPU nodes have no internet access
- Shared filesystem (`/home2/nelsg10/`) across all nodes
- Must download software on login node, run on GPU nodes

---

## Current Installation Status

| Software | Status | Location | Notes |
|----------|--------|----------|-------|
| Ollama | Installed | `~/.local/bin/ollama/` | Working with GPU support |
| Vivado 2024.2 | Installed | `~/vivado/` | Full installation including Vitis |
| MATLAB R2024b | Installer Only | `~/outsourcing/matlab_R2024b_Linux.zip` | Needs installation |

---

## GPU Hardware

Each GPU node has **4x NVIDIA H100 PCIe** GPUs with **80GB VRAM each**:

| GPU | UUID | Memory |
|-----|------|--------|
| 0 | GPU-d892d94d-d502-7e6c-2a97-d08d177b9e6a | 80GB |
| 1 | GPU-3ef7c1c1-bd97-d22d-9726-44078651ca0c | 80GB |
| 2 | GPU-4cefde4d-4332-d2ba-8886-90cd6e553907 | 80GB |
| 3 | GPU-397f9662-625b-1c89-fdf1-929344193e97 | 80GB |

---

## MATLAB Installation & Usage

### Installation Steps

1. **Extract the installer** (on login node):
   ```bash
   cd ~/outsourcing
   unzip matlab_R2024b_Linux.zip -d matlab_installer
   cd matlab_installer
   ```

2. **Create installer configuration file** (`~/outsourcing/matlab_installer_input.txt`):
   ```
   destinationFolder=/home2/nelsg10/matlab/R2024b
   fileInstallationKey=YOUR_FILE_INSTALLATION_KEY
   agreeToLicense=yes
   outputFile=/home2/nelsg10/matlab_install.log
   mode=silent

   # Products (add/remove as needed)
   product.MATLAB
   product.Parallel_Computing_Toolbox
   product.Deep_Learning_Toolbox
   product.GPU_Coder
   product.Image_Processing_Toolbox
   product.Signal_Processing_Toolbox
   ```

3. **Run silent installation**:
   ```bash
   ./install -inputFile ~/outsourcing/matlab_installer_input.txt
   ```

4. **Activate license** (if using network license):
   ```bash
   export MLM_LICENSE_FILE=27000@license.server.edu
   # Or create license file at ~/matlab/R2024b/licenses/network.lic
   ```

### Running MATLAB

**On Login Node (no GPU, for testing only):**
```bash
# Add to ~/.bashrc
export PATH="/home2/nelsg10/matlab/R2024b/bin:$PATH"
export MLM_LICENSE_FILE=27000@license.server.edu

# Run headless (single-threaded to not overload login node)
matlab -nodisplay -nosplash -singleCompThread -r "your_script; exit"
```

**On GPU Node (with GPU acceleration):**
```bash
# SSH to GPU node first
ssh gpu02

# Run with full GPU support
matlab -nodisplay -nosplash -r "gpu_script; exit"
```

### MATLAB GPU Computing

MATLAB **DOES support GPU acceleration** via the Parallel Computing Toolbox:

```matlab
% Check GPU availability
gpuDeviceCount()
gpu = gpuDevice(1);
disp(gpu.Name)  % Should show "NVIDIA H100 PCIe"

% Use gpuArray for GPU computation
A = gpuArray(rand(10000, 10000, 'single'));
B = gpuArray(rand(10000, 10000, 'single'));
C = A * B;  % Runs on GPU
result = gather(C);  % Transfer back to CPU

% Multi-GPU with parfor
parpool('local', 4);  % One worker per GPU
parfor i = 1:4
    gpu = gpuDevice(i);
    % Each worker uses different GPU
end
```

### X11 Forwarding vs Headless

| Method | Pros | Cons | Use When |
|--------|------|------|----------|
| X11 Forwarding | Interactive GUI | Very slow over network | Quick debugging only |
| Headless (`-nodisplay`) | Fast, scriptable | No interactive plots | Production runs |

**Recommendation:** Develop locally with GUI, run on HPC in headless mode.

---

## Vivado Installation & Usage

### Current Installation

Vivado 2024.2 is already installed at `~/vivado/`:
- Vivado: `~/vivado/Vivado/2024.2/`
- Vitis HLS: `~/vivado/Vitis_HLS/2024.2/`
- Vitis: `~/vivado/Vitis/2024.2/`

### Environment Setup

Add to `~/.bashrc`:
```bash
# Vivado environment
source ~/vivado/Vivado/2024.2/settings64.sh
```

### GPU Acceleration for Vivado

**IMPORTANT: Vivado does NOT support GPU acceleration for synthesis/implementation.**

Vivado's synthesis and P&R algorithms are CPU-only. The GPUs cannot speed up FPGA compilation.

### Speeding Up Vivado Compilation

Since GPUs don't help, use these CPU-based optimizations:

1. **Multi-threading** (max ~8 effective threads):
   ```tcl
   set_param general.maxThreads 8
   ```

2. **Parallel jobs** for OOC modules:
   ```tcl
   launch_runs synth_1 -jobs 4
   launch_runs impl_1 -to_step write_bitstream -jobs 4
   ```

3. **Incremental compilation** (for small changes <5%):
   ```tcl
   set_property incremental_checkpoint previous.dcp [get_runs impl_1]
   ```

### Running Vivado in Batch Mode

**Basic batch execution:**
```bash
vivado -mode batch -source build.tcl -log build.log -nojournal
```

**Example TCL build script** (`build.tcl`):
```tcl
# Set threading
set_param general.maxThreads 8

# Create project or open existing
open_project myproject.xpr

# Run synthesis
launch_runs synth_1 -jobs 4
wait_on_run synth_1

# Run implementation
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1

# Generate reports
open_run impl_1
report_timing_summary -file timing_summary.rpt
report_utilization -file utilization.rpt

puts "Build complete!"
exit
```

### Workflow: Local Development, HPC Compilation

1. **Develop on local machine** with Vivado GUI
2. **Sync project to HPC**:
   ```bash
   rsync -avz --exclude '.Xil' myproject/ nelsg10@vegaln1.erau.edu:~/projects/myproject/
   ```
3. **Run batch compilation on HPC**:
   ```bash
   ssh nelsg10@vegaln1.erau.edu
   cd ~/projects/myproject
   vivado -mode batch -source build.tcl
   ```
4. **Download results**:
   ```bash
   scp nelsg10@vegaln1.erau.edu:~/projects/myproject/output/*.bit ./
   ```

---

## Port Forwarding Patterns

### General Pattern for Services on GPU Nodes

Since GPU nodes don't have direct internet access, use SSH tunneling:

```bash
# From local machine: Forward local port to GPU node service
ssh -L LOCAL_PORT:localhost:REMOTE_PORT -J nelsg10@vegaln1.erau.edu nelsg10@gpu02
```

### Example: MATLAB Parallel Server (if configured)

```bash
# Forward MATLAB cluster ports
ssh -L 27370:localhost:27370 -J nelsg10@vegaln1.erau.edu nelsg10@gpu02
```

---

## Directory Structure Recommendation

```
~/
├── outsourcing/           # Software installers
│   ├── matlab_R2024b_Linux.zip
│   └── other_installers/
├── matlab/                # MATLAB installation (after install)
│   └── R2024b/
├── vivado/                # Vivado installation (already exists)
│   └── Vivado/2024.2/
├── projects/              # Your work projects
│   ├── matlab_projects/
│   └── fpga_projects/
└── .local/bin/            # User-installed binaries
    └── ollama/
```

---

## Quick Reference Commands

### SSH Connections
```bash
# Login node
ssh nelsg10@vegaln1.erau.edu

# GPU node (via jump host)
ssh -J nelsg10@vegaln1.erau.edu nelsg10@gpu02
```

### Check GPU Status
```bash
ssh -J nelsg10@vegaln1.erau.edu nelsg10@gpu02 "nvidia-smi"
```

### Run MATLAB Script on GPU Node
```bash
ssh -J nelsg10@vegaln1.erau.edu nelsg10@gpu02 \
    "matlab -nodisplay -nosplash -r 'run_gpu_computation; exit'"
```

### Run Vivado Build
```bash
ssh nelsg10@vegaln1.erau.edu \
    "source ~/vivado/Vivado/2024.2/settings64.sh && \
     cd ~/projects/myproject && \
     vivado -mode batch -source build.tcl"
```

---

## Troubleshooting

### MATLAB License Issues
```bash
# Check license server connectivity
ping license.server.edu
telnet license.server.edu 27000

# Set license explicitly
export MLM_LICENSE_FILE=27000@license.server.edu
```

### Vivado Can't Find License
```bash
# Check Xilinx license
export XILINXD_LICENSE_FILE=2100@license.server.edu
# Or for local license file:
export XILINXD_LICENSE_FILE=~/vivado/license.lic
```

### GPU Not Visible in MATLAB
```matlab
% Enable CUDA forward compatibility for newer GPUs
parallel.gpu.enableCUDAForwardCompatibility(true);
% Or set before starting MATLAB:
% export MW_CUDA_FORWARD_COMPATIBILITY=1
```

---

## Next Steps

1. [ ] Complete MATLAB installation with your license key
2. [ ] Test MATLAB GPU functionality on gpu02
3. [ ] Create project-specific build scripts for Vivado
4. [ ] Set up automated sync scripts for local-to-HPC workflow
