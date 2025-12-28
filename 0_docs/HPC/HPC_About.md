
## HPC Environment: Key Constraints & Characteristics

### 1. Access & Topology

* **SSH-based access only**
* **Multi-tier architecture**:

  * **Login / Head node**

    * Has Internet access
    * No GPUs
  * **GPU compute nodes (Node 1 & Node 2)**

    * Each has **4 high-end NVIDIA GPUs**
    * No Internet access
* **Login node acts as a jump host** to reach GPU nodes

---

### 2. Network Constraints

* **Asymmetric connectivity**:

  * Login node: outbound Internet allowed
  * GPU nodes: completely offline (no Internet)
* **No direct external access to GPU nodes**
* Any external communication (downloads, license checks, updates) must be staged via:

  * Login node
  * Shared filesystem

---

### 3. Filesystem Model

* **Shared filesystem across all nodes**

  * Home directory is visible from:

    * Login node
    * All GPU nodes
* This enables:

  * Building environments once (on login node)
  * Executing them anywhere (including GPU nodes)
* No need for per-node duplication of files or environments

---

### 4. Privilege & System Control

* **No sudo / root privileges**
* User-space only:

  * No system-wide installs
  * No kernel, driver, or OS-level changes
* All software must be:

  * Installed in `$HOME` or project directories
  * Self-contained and relocatable

---

### 5. GPU Availability Constraints

* GPUs are:

  * **Only present on GPU nodes**
  * NVIDIA-based (CUDA-capable)
* Login node:

  * Cannot run or test GPU workloads
* GPU workloads must:

  * Be launched after SSH’ing into a GPU node
  * Rely on pre-staged binaries, environments, or scripts

---

### 6. Software Execution Model

* **Binary execution is allowed**
* **User-space runtimes are allowed**, including:

  * Python virtual environments
  * Conda-style environments
  * Precompiled binaries
* Software must not require:

  * Online activation at runtime (unless already cached)
  * Root access
  * System-wide dependencies unavailable on the cluster

---

### 7. Licensing Constraints

* Commercial software (e.g., MATLAB, Vivado):

  * Cannot assume Internet-based license validation from GPU nodes
  * Must support:

    * Offline license files, or
    * License servers reachable from the cluster network
* License configuration must function:

  * Without sudo
  * Without modifying `/etc` or system services

---

### 8. Compute Workflow Implications

* **Two-phase workflow is implied**:

  1. **Preparation phase (login node)**

     * Download artifacts
     * Stage environments
     * Configure licenses
  2. **Execution phase (GPU node)**

     * Run compute-heavy workloads
     * No external dependencies allowed during runtime
* Debugging GPU issues is harder because:

  * No Internet on GPU nodes
  * No package installation on-demand

---

### 9. Interactive vs Batch Limitations

* GUI-based workflows are constrained:

  * No native desktop environment
  * Any GUI interaction must rely on:

    * X11 forwarding
    * Port forwarding
    * Or purely headless execution
* Long-running jobs should assume:

  * Non-interactive execution
  * Script-driven workflows

---

### 10. System State & Hygiene Challenges

* Without central package management:

  * Drift and duplication are easy
  * Manual documentation becomes essential
* Cleanup and structure are entirely the user’s responsibility

---

## Summary (One-Line Mental Model)

> This HPC system is a **shared-filesystem, user-space-only, offline-GPU compute environment** where **Internet access, GPU access, and privilege do not coexist on the same node**, forcing a **staged, script-driven, headless execution model**.
