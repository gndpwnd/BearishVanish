"""
Advanced Parallel Processor with Shared Memory
Minimizes serialization overhead for maximum performance
Supports CPU and GPU acceleration
"""

import numpy as np
import multiprocessing as mp
from multiprocessing import shared_memory
from multiprocessing.pool import ThreadPool
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional, Any, Callable, Union
from dataclasses import dataclass
import threading
import queue
import time
import warnings
from functools import partial
import ctypes
import numba
from numba import cuda
import os

# Check for GPU availability
HAS_GPU = False
try:
    import cupy as cp
    HAS_GPU = True
except ImportError:
    pass

# Type definitions
SharedArray = Any  # Can be numpy array or cupy array


@dataclass
class ParallelConfig:
    """Configuration for parallel processing"""
    # Processing mode
    mode: str = 'multiprocessing'  # 'multiprocessing', 'threading', 'gpu'
    max_workers: int = None  # Auto-detect if None
    
    # Shared memory
    use_shared_memory: bool = True
    shared_memory_size_mb: int = 1024  # 1GB shared memory
    
    # Chunking
    chunk_size: int = 100
    dynamic_chunking: bool = True
    
    # GPU settings
    gpu_device_id: int = 0
    gpu_memory_limit_mb: int = 4096  # 4GB GPU memory limit
    
    # Performance tuning
    prefetch_batches: int = 2
    worker_timeout: float = 300.0  # 5 minutes
    
    # Monitoring
    monitor_performance: bool = True
    performance_log_interval: float = 5.0
    
    # Fallback
    fallback_to_threads: bool = True
    fallback_to_sequential: bool = False


@dataclass
class WorkItem:
    """Represents a unit of work for parallel processing"""
    item_id: int
    data: Any
    metadata: Dict[str, Any]
    callback: Optional[Callable] = None


class SharedMemoryManager:
    """Manages shared memory across processes"""
    
    def __init__(self, total_size_mb: int = 1024):
        self.total_size_mb = total_size_mb
        self.total_size_bytes = total_size_mb * 1024 * 1024
        
        # Track allocated blocks
        self.blocks = {}  # name -> (shm, shape, dtype, offset)
        self.free_space = [(0, self.total_size_bytes)]  # (start, end) tuples
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'allocations': 0,
            'deallocations': 0,
            'total_allocated_mb': 0.0,
            'fragmentation': 0.0
        }
    
    def allocate_array(self, name: str, shape: Tuple[int, ...], dtype: np.dtype) -> np.ndarray:
        """
        Allocate a numpy array in shared memory
        
        Args:
            name: Unique name for the array
            shape: Array shape
            dtype: NumPy data type
            
        Returns:
            numpy array backed by shared memory
        """
        with self.lock:
            if name in self.blocks:
                raise ValueError(f"Array '{name}' already exists")
            
            # Calculate required bytes
            dtype_obj = np.dtype(dtype)
            nbytes = int(np.prod(shape) * dtype_obj.itemsize)
            
            # Find suitable free space
            block_index = -1
            for i, (start, end) in enumerate(self.free_space):
                if end - start >= nbytes:
                    block_index = i
                    break
            
            if block_index == -1:
                # Try to defragment
                self._defragment()
                
                # Try again
                for i, (start, end) in enumerate(self.free_space):
                    if end - start >= nbytes:
                        block_index = i
                        break
                
                if block_index == -1:
                    raise MemoryError(f"Not enough shared memory. Need {nbytes} bytes")
            
            # Allocate from free space
            start, end = self.free_space[block_index]
            allocated_end = start + nbytes
            
            # Update free space
            if allocated_end == end:
                # Exact fit
                self.free_space.pop(block_index)
            else:
                self.free_space[block_index] = (allocated_end, end)
            
            # Create shared memory
            try:
                shm = shared_memory.SharedMemory(create=True, size=nbytes, name=f"{name}_{int(time.time())}")
            except Exception as e:
                # Return space to free pool
                self.free_space.insert(block_index, (start, end))
                raise MemoryError(f"Failed to create shared memory: {e}")
            
            # Create numpy array
            array = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
            
            # Store block info
            self.blocks[name] = {
                'shm': shm,
                'array': array,
                'shape': shape,
                'dtype': dtype,
                'offset': start,
                'nbytes': nbytes
            }
            
            # Update stats
            self.stats['allocations'] += 1
            self.stats['total_allocated_mb'] += nbytes / (1024 * 1024)
            
            return array
    
    def get_array(self, name: str) -> Optional[np.ndarray]:
        """Get array by name"""
        with self.lock:
            if name in self.blocks:
                return self.blocks[name]['array']
        return None
    
    def deallocate_array(self, name: str):
        """Deallocate array and free memory"""
        with self.lock:
            if name not in self.blocks:
                return
            
            block = self.blocks[name]
            
            # Close and unlink shared memory
            try:
                block['shm'].close()
                block['shm'].unlink()
            except Exception as e:
                print(f"Warning: Failed to unlink shared memory {name}: {e}")
            
            # Add space back to free pool
            start = block['offset']
            end = start + block['nbytes']
            self._add_free_space(start, end)
            
            # Remove block
            del self.blocks[name]
            
            # Update stats
            self.stats['deallocations'] += 1
            self.stats['total_allocated_mb'] -= block['nbytes'] / (1024 * 1024)
    
    def _add_free_space(self, start: int, end: int):
        """Add free space block, merging with adjacent blocks"""
        # Find insertion position
        insert_pos = 0
        for i, (fs_start, fs_end) in enumerate(self.free_space):
            if start < fs_start:
                insert_pos = i
                break
            insert_pos = i + 1
        
        # Insert new block
        self.free_space.insert(insert_pos, (start, end))
        
        # Merge with previous block if adjacent
        if insert_pos > 0:
            prev_start, prev_end = self.free_space[insert_pos - 1]
            if prev_end == start:
                # Merge
                self.free_space[insert_pos - 1] = (prev_start, end)
                self.free_space.pop(insert_pos)
                insert_pos -= 1
        
        # Merge with next block if adjacent
        if insert_pos < len(self.free_space) - 1:
            next_start, next_end = self.free_space[insert_pos + 1]
            if end == next_start:
                # Merge
                self.free_space[insert_pos] = (start, next_end)
                self.free_space.pop(insert_pos + 1)
    
    def _defragment(self):
        """Defragment free space (merge adjacent blocks)"""
        if len(self.free_space) <= 1:
            return
        
        # Sort by start position
        self.free_space.sort(key=lambda x: x[0])
        
        # Merge adjacent blocks
        i = 0
        while i < len(self.free_space) - 1:
            curr_start, curr_end = self.free_space[i]
            next_start, next_end = self.free_space[i + 1]
            
            if curr_end == next_start:
                # Merge
                self.free_space[i] = (curr_start, next_end)
                self.free_space.pop(i + 1)
            else:
                i += 1
        
        # Update fragmentation metric
        if len(self.free_space) > 1:
            total_free = sum(end - start for start, end in self.free_space)
            largest_block = max(end - start for start, end in self.free_space)
            self.stats['fragmentation'] = 1.0 - (largest_block / total_free)
        else:
            self.stats['fragmentation'] = 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get shared memory statistics"""
        with self.lock:
            used_mb = self.stats['total_allocated_mb']
            total_mb = self.total_size_mb
            free_mb = total_mb - used_mb
            
            return {
                **self.stats,
                'used_mb': used_mb,
                'free_mb': free_mb,
                'total_mb': total_mb,
                'utilization': used_mb / total_mb * 100,
                'block_count': len(self.blocks),
                'free_blocks': len(self.free_space)
            }
    
    def __del__(self):
        """Cleanup all shared memory on deletion"""
        for name in list(self.blocks.keys()):
            try:
                self.deallocate_array(name)
            except Exception:
                pass


class GPUManager:
    """Manages GPU resources for accelerated computation"""
    
    def __init__(self, device_id: int = 0, memory_limit_mb: int = 4096):
        self.device_id = device_id
        self.memory_limit_mb = memory_limit_mb
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        
        # Initialize GPU
        self.device = None
        self.context = None
        self.stream = None
        
        # Memory tracking
        self.allocated_memory = 0
        self.allocations = {}
        
        # Statistics
        self.stats = {
            'kernel_launches': 0,
            'memory_transfers': 0,
            'total_transfer_time': 0.0,
            'total_compute_time': 0.0
        }
        
        # Initialize if GPU available
        self._initialize_gpu()
    
    def _initialize_gpu(self):
        """Initialize GPU context"""
        if not HAS_GPU:
            self.available = False
            return
        
        try:
            # Select device
            cp.cuda.Device(self.device_id).use()
            
            # Create stream for async operations
            self.stream = cp.cuda.Stream(non_blocking=True)
            
            self.available = True
            print(f"✅ GPU {self.device_id} initialized: {cp.cuda.runtime.getDeviceProperties(self.device_id)['name']}")
            
        except Exception as e:
            self.available = False
            print(f"❌ GPU initialization failed: {e}")
    
    def allocate_gpu_array(self, shape: Tuple[int, ...], dtype: np.dtype) -> cp.ndarray:
        """Allocate array on GPU"""
        if not self.available:
            raise RuntimeError("GPU not available")
        
        # Calculate memory requirement
        dtype_obj = cp.dtype(dtype)
        nbytes = int(np.prod(shape) * dtype_obj.itemsize)
        
        # Check memory limit
        if self.allocated_memory + nbytes > self.memory_limit_bytes:
            self._cleanup_unused()
            
            if self.allocated_memory + nbytes > self.memory_limit_bytes:
                raise MemoryError(f"GPU memory limit exceeded. Need {nbytes} bytes, "
                                 f"have {self.memory_limit_bytes - self.allocated_memory} bytes free")
        
        # Allocate on GPU
        try:
            gpu_array = cp.zeros(shape, dtype=dtype)
            self.allocated_memory += nbytes
            
            # Generate unique ID
            array_id = id(gpu_array)
            self.allocations[array_id] = {
                'array': gpu_array,
                'nbytes': nbytes,
                'last_used': time.time()
            }
            
            return gpu_array
            
        except Exception as e:
            raise MemoryError(f"GPU allocation failed: {e}")
    
    def to_gpu(self, cpu_array: np.ndarray) -> cp.ndarray:
        """Transfer array from CPU to GPU"""
        if not self.available:
            raise RuntimeError("GPU not available")
        
        start_time = time.time()
        
        try:
            gpu_array = cp.asarray(cpu_array, stream=self.stream)
            self.stream.synchronize()
            
            transfer_time = time.time() - start_time
            self.stats['memory_transfers'] += 1
            self.stats['total_transfer_time'] += transfer_time
            
            # Track allocation
            nbytes = gpu_array.nbytes
            self.allocated_memory += nbytes
            
            array_id = id(gpu_array)
            self.allocations[array_id] = {
                'array': gpu_array,
                'nbytes': nbytes,
                'last_used': time.time()
            }
            
            return gpu_array
            
        except Exception as e:
            raise RuntimeError(f"CPU→GPU transfer failed: {e}")
    
    def to_cpu(self, gpu_array: cp.ndarray) -> np.ndarray:
        """Transfer array from GPU to CPU"""
        if not self.available:
            raise RuntimeError("GPU not available")
        
        start_time = time.time()
        
        try:
            # Synchronize stream first
            self.stream.synchronize()
            
            # Copy to CPU
            cpu_array = cp.asnumpy(gpu_array, stream=self.stream)
            self.stream.synchronize()
            
            transfer_time = time.time() - start_time
            self.stats['memory_transfers'] += 1
            self.stats['total_transfer_time'] += transfer_time
            
            return cpu_array
            
        except Exception as e:
            raise RuntimeError(f"GPU→CPU transfer failed: {e}")
    
    def run_kernel(self, kernel_func: Callable, *args, **kwargs):
        """Run a GPU kernel"""
        if not self.available:
            raise RuntimeError("GPU not available")
        
        start_time = time.time()
        
        try:
            # Execute kernel
            result = kernel_func(*args, **kwargs)
            self.stream.synchronize()
            
            compute_time = time.time() - start_time
            self.stats['kernel_launches'] += 1
            self.stats['total_compute_time'] += compute_time
            
            return result
            
        except Exception as e:
            raise RuntimeError(f"GPU kernel execution failed: {e}")
    
    def _cleanup_unused(self, max_age: float = 60.0):
        """Clean up arrays not used recently"""
        current_time = time.time()
        to_remove = []
        
        for array_id, info in self.allocations.items():
            if current_time - info['last_used'] > max_age:
                # Free memory
                info['array'].data.free()
                self.allocated_memory -= info['nbytes']
                to_remove.append(array_id)
        
        for array_id in to_remove:
            del self.allocations[array_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get GPU statistics"""
        if not self.available:
            return {'available': False}
        
        # Get GPU memory info
        mem_info = cp.cuda.runtime.memGetInfo()
        free_mem = mem_info[0] / 1024**2
        total_mem = mem_info[1] / 1024**2
        used_mem = total_mem - free_mem
        
        return {
            'available': True,
            'device_id': self.device_id,
            'total_memory_mb': total_mem,
            'used_memory_mb': used_mem,
            'free_memory_mb': free_mem,
            'allocated_memory_mb': self.allocated_memory / 1024**2,
            'allocation_count': len(self.allocations),
            **self.stats,
            'utilization': used_mem / total_mem * 100
        }
    
    def __del__(self):
        """Cleanup GPU resources"""
        if self.available:
            # Free all allocations
            for info in self.allocations.values():
                try:
                    info['array'].data.free()
                except Exception:
                    pass
            
            # Reset device
            try:
                cp.cuda.device.Device().synchronize()
            except Exception:
                pass


class ParallelProcessor:
    """
    Main parallel processing engine with shared memory support
    """
    
    def __init__(self, config: ParallelConfig = None):
        self.config = config or ParallelConfig()
        
        # Auto-detect worker count
        if self.config.max_workers is None:
            cpu_count = mp.cpu_count()
            if self.config.mode == 'gpu':
                self.config.max_workers = 1  # GPU typically single process
            else:
                self.config.max_workers = max(1, cpu_count - 2)
        
        # Initialize managers based on mode
        self.shared_memory = None
        self.gpu_manager = None
        
        if self.config.use_shared_memory and self.config.mode == 'multiprocessing':
            self.shared_memory = SharedMemoryManager(self.config.shared_memory_size_mb)
        
        if self.config.mode == 'gpu':
            self.gpu_manager = GPUManager(
                device_id=self.config.gpu_device_id,
                memory_limit_mb=self.config.gpu_memory_limit_mb
            )
        
        # Work queue
        self.work_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        # Performance monitoring
        self.performance_stats = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_processing_time': 0.0,
            'avg_processing_time': 0.0,
            'throughput_tasks_per_second': 0.0
        }
        
        # Worker management
        self.workers = []
        self.is_running = False
        self.monitor_thread = None
        
        print(f"🚀 Parallel Processor Initialized")
        print(f"   Mode: {self.config.mode}")
        print(f"   Workers: {self.config.max_workers}")
        print(f"   Shared Memory: {self.config.use_shared_memory}")
        print(f"   GPU: {self.config.mode == 'gpu' and self.gpu_manager.available if self.gpu_manager else False}")
    
    def process_batch(self,
                     items: List[Any],
                     process_func: Callable,
                     chunk_size: Optional[int] = None,
                     progress_callback: Optional[Callable] = None) -> List[Any]:
        """
        Process batch of items in parallel
        
        Args:
            items: List of items to process
            process_func: Function to process each item
            chunk_size: Size of chunks (None = auto)
            progress_callback: Callback for progress updates
            
        Returns:
            List of results in same order as input
        """
        if not items:
            return []
        
        # Determine chunk size
        if chunk_size is None:
            if self.config.dynamic_chunking:
                # Dynamic chunking based on item count and workers
                chunk_size = max(1, len(items) // (self.config.max_workers * 4))
            else:
                chunk_size = self.config.chunk_size
        
        # Create chunks
        chunks = []
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            chunks.append((i // chunk_size, chunk))
        
        print(f"🧩 Processing {len(items)} items in {len(chunks)} chunks "
              f"(chunk size: {chunk_size})")
        
        # Choose processing method based on mode
        if self.config.mode == 'multiprocessing':
            results = self._process_multiprocessing(chunks, process_func, progress_callback)
        elif self.config.mode == 'threading':
            results = self._process_threading(chunks, process_func, progress_callback)
        elif self.config.mode == 'gpu':
            results = self._process_gpu(chunks, process_func, progress_callback)
        else:
            raise ValueError(f"Unknown processing mode: {self.config.mode}")
        
        # Flatten results
        flat_results = []
        for chunk_results in results:
            flat_results.extend(chunk_results)
        
        return flat_results
    
    def _process_multiprocessing(self,
                                chunks: List[Tuple[int, List]],
                                process_func: Callable,
                                progress_callback: Optional[Callable]) -> List[List]:
        """Process using multiprocessing with shared memory"""
        start_time = time.time()
        
        # Prepare shared data if needed
        shared_data = {}
        if self.shared_memory and hasattr(process_func, 'requires_shared_data'):
            # Get data that needs to be shared
            data_to_share = process_func.requires_shared_data()
            for name, data in data_to_share.items():
                if isinstance(data, np.ndarray):
                    shared_array = self.shared_memory.allocate_array(
                        name, data.shape, data.dtype
                    )
                    shared_array[:] = data[:]
                    shared_data[name] = shared_array
        
        # Create worker function with shared data access
        def worker_func(chunk_id, chunk_items):
            try:
                # Access shared data if available
                if shared_data:
                    # Reattach to shared memory
                    local_shared = {}
                    for name, shared_array in shared_data.items():
                        # In worker process, we need to open existing shared memory
                        # This is simplified - in real implementation would need proper handling
                        local_shared[name] = shared_array
                    
                    # Modify process function to use shared data
                    result = process_func(chunk_items, shared_data=local_shared)
                else:
                    result = process_func(chunk_items)
                
                return chunk_id, result, None
                
            except Exception as e:
                return chunk_id, None, str(e)
        
        # Process chunks in parallel
        results = [None] * len(chunks)
        
        with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all chunks
            future_to_chunk = {}
            for chunk_id, chunk_items in chunks:
                future = executor.submit(worker_func, chunk_id, chunk_items)
                future_to_chunk[future] = chunk_id
            
            # Process results as they complete
            with tqdm(total=len(chunks), desc="Processing") as pbar:
                for future in as_completed(future_to_chunk):
                    chunk_id = future_to_chunk[future]
                    
                    try:
                        chunk_id, chunk_results, error = future.result(timeout=self.config.worker_timeout)
                        
                        if error:
                            print(f"⚠️  Error in chunk {chunk_id}: {error}")
                            self.performance_stats['tasks_failed'] += 1
                        else:
                            results[chunk_id] = chunk_results
                            self.performance_stats['tasks_completed'] += len(chunk_items)
                        
                    except Exception as e:
                        print(f"❌ Failed chunk {chunk_id}: {e}")
                        self.performance_stats['tasks_failed'] += 1
                    
                    pbar.update(1)
                    
                    if progress_callback:
                        progress_callback(self.performance_stats['tasks_completed'])
        
        # Cleanup shared memory
        if shared_data:
            for name in list(shared_data.keys()):
                self.shared_memory.deallocate_array(name)
        
        # Update statistics
        processing_time = time.time() - start_time
        self.performance_stats['total_processing_time'] += processing_time
        self.performance_stats['avg_processing_time'] = (
            processing_time / max(1, self.performance_stats['tasks_completed'])
        )
        self.performance_stats['throughput_tasks_per_second'] = (
            self.performance_stats['tasks_completed'] / processing_time
        )
        
        return [r for r in results if r is not None]
    
    def _process_threading(self,
                          chunks: List[Tuple[int, List]],
                          process_func: Callable,
                          progress_callback: Optional[Callable]) -> List[List]:
        """Process using threading (good for I/O bound tasks)"""
        start_time = time.time()
        results = [None] * len(chunks)
        
        def process_chunk(chunk_id, chunk_items):
            try:
                result = process_func(chunk_items)
                return chunk_id, result, None
            except Exception as e:
                return chunk_id, None, str(e)
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all chunks
            future_to_chunk = {}
            for chunk_id, chunk_items in chunks:
                future = executor.submit(process_chunk, chunk_id, chunk_items)
                future_to_chunk[future] = chunk_id
            
            # Process results
            with tqdm(total=len(chunks), desc="Processing") as pbar:
                for future in as_completed(future_to_chunk):
                    chunk_id = future_to_chunk[future]
                    
                    try:
                        chunk_id, chunk_results, error = future.result(timeout=self.config.worker_timeout)
                        
                        if error:
                            print(f"⚠️  Error in chunk {chunk_id}: {error}")
                            self.performance_stats['tasks_failed'] += 1
                        else:
                            results[chunk_id] = chunk_results
                            self.performance_stats['tasks_completed'] += len(chunk_items)
                        
                    except Exception as e:
                        print(f"❌ Failed chunk {chunk_id}: {e}")
                        self.performance_stats['tasks_failed'] += 1
                    
                    pbar.update(1)
                    
                    if progress_callback:
                        progress_callback(self.performance_stats['tasks_completed'])
        
        # Update statistics
        processing_time = time.time() - start_time
        self.performance_stats['total_processing_time'] += processing_time
        self.performance_stats['avg_processing_time'] = (
            processing_time / max(1, self.performance_stats['tasks_completed'])
        )
        self.performance_stats['throughput_tasks_per_second'] = (
            self.performance_stats['tasks_completed'] / processing_time
        )
        
        return [r for r in results if r is not None]
    
    def _process_gpu(self,
                    chunks: List[Tuple[int, List]],
                    process_func: Callable,
                    progress_callback: Optional[Callable]) -> List[List]:
        """Process using GPU acceleration"""
        if not self.gpu_manager or not self.gpu_manager.available:
            if self.config.fallback_to_threads:
                print("⚠️  GPU not available, falling back to threading")
                self.config.mode = 'threading'
                return self._process_threading(chunks, process_func, progress_callback)
            else:
                raise RuntimeError("GPU processing requested but GPU not available")
        
        start_time = time.time()
        results = []
        
        # Process chunks sequentially on GPU (or small batch)
        with tqdm(total=len(chunks), desc="GPU Processing") as pbar:
            for chunk_id, chunk_items in chunks:
                try:
                    # Convert data to GPU
                    gpu_data = []
                    for item in chunk_items:
                        if isinstance(item, np.ndarray):
                            gpu_item = self.gpu_manager.to_gpu(item)
                            gpu_data.append(gpu_item)
                        else:
                            gpu_data.append(item)
                    
                    # Process on GPU
                    gpu_results = self.gpu_manager.run_kernel(process_func, gpu_data)
                    
                    # Convert results back to CPU
                    cpu_results = []
                    for result in gpu_results:
                        if isinstance(result, cp.ndarray):
                            cpu_result = self.gpu_manager.to_cpu(result)
                            cpu_results.append(cpu_result)
                        else:
                            cpu_results.append(result)
                    
                    results.append(cpu_results)
                    self.performance_stats['tasks_completed'] += len(chunk_items)
                    
                except Exception as e:
                    print(f"❌ GPU processing failed for chunk {chunk_id}: {e}")
                    self.performance_stats['tasks_failed'] += 1
                    results.append([])  # Empty results for failed chunk
                
                pbar.update(1)
                
                if progress_callback:
                    progress_callback(self.performance_stats['tasks_completed'])
        
        # Update statistics
        processing_time = time.time() - start_time
        self.performance_stats['total_processing_time'] += processing_time
        self.performance_stats['avg_processing_time'] = (
            processing_time / max(1, self.performance_stats['tasks_completed'])
        )
        self.performance_stats['throughput_tasks_per_second'] = (
            self.performance_stats['tasks_completed'] / processing_time
        )
        
        return results
    
    def map(self, func: Callable, iterable: List, chunk_size: int = None) -> List:
        """Map function over iterable in parallel (similar to multiprocessing.Pool.map)"""
        # Convert to list of single-item chunks
        items = [(i, [item]) for i, item in enumerate(iterable)]
        
        # Process
        results = self.process_batch(
            items,
            lambda chunk: [func(item) for item in chunk[0][1]],  # Extract and process
            chunk_size=chunk_size
        )
        
        # Ensure correct order
        return [r for r in results if r is not None]
    
    def starmap(self, func: Callable, iterable: List, chunk_size: int = None) -> List:
        """Like map but with multiple arguments"""
        items = [(i, [args]) for i, args in enumerate(iterable)]
        
        results = self.process_batch(
            items,
            lambda chunk: [func(*args) for args in chunk[0][1]],
            chunk_size=chunk_size
        )
        
        return [r for r in results if r is not None]
    
    def benchmark(self, 
                  test_func: Callable,
                  test_data: List,
                  modes: List[str] = None) -> Dict[str, Dict]:
        """
        Benchmark different parallelization modes
        
        Args:
            test_func: Function to benchmark
            test_data: Test data to process
            modes: List of modes to test
            
        Returns:
            Dictionary of benchmark results
        """
        if modes is None:
            modes = ['multiprocessing', 'threading']
            if HAS_GPU:
                modes.append('gpu')
        
        print(f"\n{'='*70}")
        print("PARALLEL PROCESSING BENCHMARK")
        print(f"{'='*70}")
        
        results = {}
        
        for mode in modes:
            print(f"\n🧪 Testing mode: {mode}")
            
            # Create processor with this mode
            config = ParallelConfig(
                mode=mode,
                max_workers=self.config.max_workers,
                use_shared_memory=(mode == 'multiprocessing')
            )
            
            processor = ParallelProcessor(config)
            
            # Time the processing
            start_time = time.time()
            
            try:
                processed = processor.process_batch(
                    test_data,
                    test_func,
                    chunk_size=len(test_data) // (self.config.max_workers * 2)
                )
                
                processing_time = time.time() - start_time
                
                results[mode] = {
                    'time_seconds': processing_time,
                    'throughput': len(test_data) / processing_time,
                    'success': True,
                    'items_processed': len(processed)
                }
                
                print(f"   Time: {processing_time:.2f}s")
                print(f"   Throughput: {len(test_data)/processing_time:.1f} items/sec")
                
            except Exception as e:
                results[mode] = {
                    'time_seconds': 0,
                    'throughput': 0,
                    'success': False,
                    'error': str(e)
                }
                print(f"   Failed: {e}")
        
        # Print comparison
        print(f"\n{'='*70}")
        print("BENCHMARK RESULTS")
        print(f"{'='*70}")
        
        best_mode = None
        best_throughput = 0
        
        for mode, result in results.items():
            if result['success']:
                throughput = result['throughput']
                print(f"{mode:20} {throughput:10.1f} items/sec")
                
                if throughput > best_throughput:
                    best_throughput = throughput
                    best_mode = mode
        
        if best_mode:
            print(f"\n🎯 Best mode: {best_mode} ({best_throughput:.1f} items/sec)")
        
        print(f"{'='*70}")
        
        return results
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = {
            **self.performance_stats,
            'config': {
                'mode': self.config.mode,
                'max_workers': self.config.max_workers,
                'use_shared_memory': self.config.use_shared_memory
            }
        }
        
        # Add shared memory stats if available
        if self.shared_memory:
            stats['shared_memory'] = self.shared_memory.get_stats()
        
        # Add GPU stats if available
        if self.gpu_manager:
            stats['gpu'] = self.gpu_manager.get_stats()
        
        return stats
    
    def print_performance_report(self):
        """Print performance report"""
        stats = self.get_performance_stats()
        
        print(f"\n{'='*70}")
        print("PARALLEL PROCESSING PERFORMANCE")
        print(f"{'='*70}")
        
        print(f"📊 Task Statistics:")
        print(f"   Completed: {stats['tasks_completed']:,}")
        print(f"   Failed: {stats['tasks_failed']:,}")
        print(f"   Success Rate: {stats['tasks_completed']/max(1, stats['tasks_completed'] + stats['tasks_failed'])*100:.1f}%")
        
        print(f"\n⏱️  Timing Statistics:")
        print(f"   Total Time: {stats['total_processing_time']:.2f}s")
        print(f"   Avg Time per Task: {stats['avg_processing_time']*1000:.1f}ms")
        print(f"   Throughput: {stats['throughput_tasks_per_second']:.1f} tasks/sec")
        
        if 'shared_memory' in stats:
            sm_stats = stats['shared_memory']
            print(f"\n🧺 Shared Memory:")
            print(f"   Used: {sm_stats['used_mb']:.1f} MB")
            print(f"   Free: {sm_stats['free_mb']:.1f} MB")
            print(f"   Utilization: {sm_stats['utilization']:.1f}%")
            print(f"   Fragmentation: {sm_stats['fragmentation']*100:.1f}%")
        
        if 'gpu' in stats and stats['gpu']['available']:
            gpu_stats = stats['gpu']
            print(f"\n🎮 GPU Statistics:")
            print(f"   Used Memory: {gpu_stats['used_memory_mb']:.1f} MB")
            print(f"   Free Memory: {gpu_stats['free_memory_mb']:.1f} MB")
            print(f"   Kernel Launches: {gpu_stats['kernel_launches']:,}")
            print(f"   Memory Transfers: {gpu_stats['memory_transfers']:,}")
            print(f"   Compute Time: {gpu_stats['total_compute_time']:.2f}s")
            print(f"   Transfer Time: {gpu_stats['total_transfer_time']:.2f}s")
        
        print(f"\n⚡ Recommendations:")
        
        if stats['throughput_tasks_per_second'] < 100:
            print(f"   ⚠️  Low throughput - Consider:")
            print(f"     • Increasing chunk size")
            print(f"     • Using shared memory for multiprocessing")
            print(f"     • Optimizing processing function")
        
        elif stats['throughput_tasks_per_second'] < 1000:
            print(f"   ✅ Good performance")
            print(f"     • Try GPU acceleration for compute-intensive tasks")
            print(f"     • Consider increasing worker count")
        
        else:
            print(f"   🚀 Excellent performance!")
            print(f"     • You're maximizing CPU/GPU resources")
            print(f"     • Consider distributed computing for even larger scales")
        
        print(f"{'='*70}\n")
    
    def __del__(self):
        """Cleanup resources"""
        if self.shared_memory:
            del self.shared_memory
        
        if self.gpu_manager:
            del self.gpu_manager


# Factory function and global instance

_parallel_processor = None

def get_parallel_processor(config: ParallelConfig = None) -> ParallelProcessor:
    """Get or create global parallel processor"""
    global _parallel_processor
    if _parallel_processor is None:
        _parallel_processor = ParallelProcessor(config)
    return _parallel_processor


# GPU-accelerated functions (examples)

@numba.cuda.jit
def gpu_add_arrays(a, b, result):
    """GPU kernel for adding arrays"""
    i = numba.cuda.grid(1)
    if i < a.shape[0]:
        result[i] = a[i] + b[i]

@numba.cuda.jit
def gpu_matrix_multiply(a, b, result):
    """GPU kernel for matrix multiplication"""
    i, j = numba.cuda.grid(2)
    if i < result.shape[0] and j < result.shape[1]:
        tmp = 0.0
        for k in range(a.shape[1]):
            tmp += a[i, k] * b[k, j]
        result[i, j] = tmp

# Example usage
if __name__ == "__main__":
    print("🧪 Testing Parallel Processor")
    
    # Test data
    test_data = [np.random.randn(1000, 1000) for _ in range(100)]
    
    # Test function
    def process_matrix(matrix):
        return np.linalg.eigvals(matrix)
    
    # Create processor
    processor = get_parallel_processor()
    
    # Run benchmark
    results = processor.benchmark(process_matrix, test_data[:10])
    
    # Process full dataset with best mode
    print(f"\n📊 Processing full dataset...")
    processed = processor.process_batch(test_data, process_matrix)
    
    print(f"✅ Processed {len(processed)} matrices")
    
    # Print performance report
    processor.print_performance_report()