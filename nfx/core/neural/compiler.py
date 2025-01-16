"""NFX Neural Fabric Compiler

Metal shader compiler and optimizer for neural pathways.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

try:
    import Metal as mtl
    import MetalPerformanceShaders as mps
except ImportError:
    logging.warning("Metal libraries not available. Using CPU fallback.")
    mtl = None
    mps = None

@dataclass
class MetalKernel:
    """Compiled Metal kernel"""
    id: str
    pipeline_state: Any
    thread_execution_width: int
    max_total_threads_per_threadgroup: int
    static_threadgroup_memory_length: int

class MetalPathwayCompiler:
    """Compiles optimized Metal kernels for neural pathways"""

    def __init__(self, device: Any, optimization_level: int):
        self.device = device
        self.opt_level = optimization_level
        self._logger = logging.getLogger('pathway_compiler')

        # Pre-compile common kernels
        self.kernel_library = self._build_kernel_library()

        # Set up Metal compiler
        self.compiler = self._setup_compiler()

    def _setup_compiler(self) -> Optional[Any]:
        """Set up Metal compiler with optimization flags"""
        try:
            if self.device is None:
                return None

            # Create default library
            library = self.device.newDefaultLibrary()
            if library is None:
                raise RuntimeError("Failed to create Metal library")

            return library

        except Exception as e:
            self._logger.error(f"Failed to set up compiler: {e}")
            return None

    def _build_kernel_library(self) -> Dict[str, str]:
        """Build optimized kernel library"""
        return {
            'tensor_contract': self._get_tensor_contract_kernel(),
            'scaled_attention': self._get_attention_kernel(),
            'layer_norm': self._get_layer_norm_kernel(),
            'activation': self._get_activation_kernel(),
            'softmax': self._get_softmax_kernel()
        }

    def _get_tensor_contract_kernel(self) -> str:
        """Get optimized tensor contraction kernel"""
        return """
        #include <metal_stdlib>
        using namespace metal;

        kernel void tensor_contract(
            device const half* input [[ buffer(0) ]],
            device const half* weights [[ buffer(1) ]],
            device half* output [[ buffer(2) ]],
            constant uint4& dims [[ buffer(3) ]],
            uint3 tid [[ thread_position_in_threadgroup ]],
            uint3 gid [[ threadgroup_position_in_grid ]]
        ) {
            // Shared memory for tiling
            threadgroup half tile_input[32][32];
            threadgroup half tile_weights[32][32];

            // Register cache for output tile
            half acc[4][4] = {0.0h};

            // Main computation loop with aggressive unrolling
            #pragma unroll 8
            for (uint k = 0; k < dims.z; k += 32) {
                // Load tiles with vectorized loads
                {
                    uint4 input_idx = uint4(
                        gid.y * 32 + tid.y,
                        k + tid.x,
                        0, 0
                    );

                    uint4 weight_idx = uint4(
                        k + tid.y,
                        gid.x * 32 + tid.x,
                        0, 0
                    );

                    // Vector loads for better memory bandwidth
                    half4 input_vec = *reinterpret_cast<device const half4*>(
                        input + input_idx.x * dims.y + input_idx.y
                    );

                    half4 weight_vec = *reinterpret_cast<device const half4*>(
                        weights + weight_idx.x * dims.w + weight_idx.y
                    );

                    tile_input[tid.y][tid.x] = input_vec[0];
                    tile_weights[tid.y][tid.x] = weight_vec[0];
                }

                threadgroup_barrier(mem_flags::mem_threadgroup);

                // Compute tile product with SIMD operations
                #pragma unroll 4
                for (uint tk = 0; tk < 32; tk++) {
                    half4 input_vec = *reinterpret_cast<threadgroup const half4*>(
                        &tile_input[tid.y][tk]
                    );

                    half4 weight_vec = *reinterpret_cast<threadgroup const half4*>(
                        &tile_weights[tk][tid.x]
                    );

                    #pragma unroll 4
                    for (uint i = 0; i < 4; i++) {
                        #pragma unroll 4
                        for (uint j = 0; j < 4; j++) {
                            acc[i][j] = fma(input_vec[i], weight_vec[j], acc[i][j]);
                        }
                    }
                }

                threadgroup_barrier(mem_flags::mem_threadgroup);
            }

            // Store results with vectorized writes
            uint output_row = gid.y * 32 + tid.y;
            uint output_col = gid.x * 32 + tid.x;

            if (output_row < dims.x && output_col < dims.w) {
                half4 output_vec;
                #pragma unroll 4
                for (uint i = 0; i < 4; i++) {
                    output_vec[i] = acc[i][0];
                }

                *reinterpret_cast<device half4*>(
                    output + output_row * dims.w + output_col
                ) = output_vec;
            }
        }
        """

    def _get_attention_kernel(self) -> str:
        """Get optimized attention kernel"""
        return """
        #include <metal_stdlib>
        using namespace metal;

        kernel void scaled_attention(
            device const half* queries [[ buffer(0) ]],
            device const half* keys [[ buffer(1) ]],
            device const half* values [[ buffer(2) ]],
            device half* output [[ buffer(3) ]],
            constant uint4& dims [[ buffer(4) ]],
            uint3 tid [[ thread_position_in_threadgroup ]],
            uint3 gid [[ threadgroup_position_in_grid ]]
        ) {
            // Shared memory for attention tiles
            threadgroup half query_tile[32][32];
            threadgroup half key_tile[32][32];
            threadgroup half value_tile[32][32];

            // Load tiles with vectorized loads
            {
                uint4 query_idx = uint4(
                    gid.y * 32 + tid.y,
                    tid.x,
                    0, 0
                );

                uint4 key_idx = uint4(
                    tid.y,
                    gid.x * 32 + tid.x,
                    0, 0
                );

                // Vector loads
                half4 query_vec = *reinterpret_cast<device const half4*>(
                    queries + query_idx.x * dims.y + query_idx.y
                );

                half4 key_vec = *reinterpret_cast<device const half4*>(
                    keys + key_idx.x * dims.w + key_idx.y
                );

                query_tile[tid.y][tid.x] = query_vec[0];
                key_tile[tid.y][tid.x] = key_vec[0];
            }

            threadgroup_barrier(mem_flags::mem_threadgroup);

            // Compute attention scores
            half scores[4][4] = {0.0h};
            half scale = half(1.0) / sqrt(half(dims.y));

            #pragma unroll 4
            for (uint k = 0; k < 32; k++) {
                half4 query_vec = *reinterpret_cast<threadgroup const half4*>(
                    &query_tile[tid.y][k]
                );

                half4 key_vec = *reinterpret_cast<threadgroup const half4*>(
                    &key_tile[k][tid.x]
                );

                #pragma unroll 4
                for (uint i = 0; i < 4; i++) {
                    #pragma unroll 4
                    for (uint j = 0; j < 4; j++) {
                        scores[i][j] = fma(query_vec[i], key_vec[j], scores[i][j]);
                    }
                }
            }

            // Apply scaling and softmax
            half max_score = -INFINITY;
            #pragma unroll 4
            for (uint i = 0; i < 4; i++) {
                #pragma unroll 4
                for (uint j = 0; j < 4; j++) {
                    scores[i][j] *= scale;
                    max_score = max(max_score, scores[i][j]);
                }
            }

            half sum = 0.0h;
            #pragma unroll 4
            for (uint i = 0; i < 4; i++) {
                #pragma unroll 4
                for (uint j = 0; j < 4; j++) {
                    scores[i][j] = exp(scores[i][j] - max_score);
                    sum += scores[i][j];
                }
            }

            #pragma unroll 4
            for (uint i = 0; i < 4; i++) {
                #pragma unroll 4
                for (uint j = 0; j < 4; j++) {
                    scores[i][j] /= sum;
                }
            }

            // Load value tiles
            {
                uint4 value_idx = uint4(
                    tid.y,
                    gid.x * 32 + tid.x,
                    0, 0
                );

                half4 value_vec = *reinterpret_cast<device const half4*>(
                    values + value_idx.x * dims.w + value_idx.y
                );

                value_tile[tid.y][tid.x] = value_vec[0];
            }

            threadgroup_barrier(mem_flags::mem_threadgroup);

            // Compute weighted values
            half output_values[4][4] = {0.0h};

            #pragma unroll 4
            for (uint k = 0; k < 32; k++) {
                half4 score_vec = half4(scores[tid.y][k]);
                half4 value_vec = *reinterpret_cast<threadgroup const half4*>(
                    &value_tile[k][tid.x]
                );

                #pragma unroll 4
                for (uint i = 0; i < 4; i++) {
                    output_values[i][0] = fma(score_vec[i], value_vec[0], output_values[i][0]);
                }
            }

            // Store results
            uint output_row = gid.y * 32 + tid.y;
            uint output_col = gid.x * 32 + tid.x;

            if (output_row < dims.x && output_col < dims.w) {
                half4 output_vec;
                #pragma unroll 4
                for (uint i = 0; i < 4; i++) {
                    output_vec[i] = output_values[i][0];
                }

                *reinterpret_cast<device half4*>(
                    output + output_row * dims.w + output_col
                ) = output_vec;
            }
        }
        """

    def _get_layer_norm_kernel(self) -> str:
        """Get optimized layer normalization kernel"""
        return """
        #include <metal_stdlib>
        using namespace metal;

        kernel void layer_norm(
            device const half* input [[ buffer(0) ]],
            device const half* gamma [[ buffer(1) ]],
            device const half* beta [[ buffer(2) ]],
            device half* output [[ buffer(3) ]],
            constant uint& hidden_size [[ buffer(4) ]],
            uint tid [[ thread_position_in_threadgroup ]],
            uint bid [[ threadgroup_position_in_grid ]]
        ) {
            const uint offset = bid * hidden_size;

            // Calculate mean
            half sum = 0.0h;
            for (uint i = tid; i < hidden_size; i += 32) {
                sum += input[offset + i];
            }

            threadgroup half thread_sum[32];
            thread_sum[tid] = sum;
            threadgroup_barrier(mem_flags::mem_threadgroup);

            if (tid < 16) thread_sum[tid] += thread_sum[tid + 16];
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid < 8) thread_sum[tid] += thread_sum[tid + 8];
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid < 4) thread_sum[tid] += thread_sum[tid + 4];
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid < 2) thread_sum[tid] += thread_sum[tid + 2];
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid < 1) thread_sum[tid] += thread_sum[tid + 1];
            threadgroup_barrier(mem_flags::mem_threadgroup);

            const half mean = thread_sum[0] / half(hidden_size);

            // Calculate variance
            half var_sum = 0.0h;
            for (uint i = tid; i < hidden_size; i += 32) {
                half diff = input[offset + i] - mean;
                var_sum += diff * diff;
            }

            thread_sum[tid] = var_sum;
            threadgroup_barrier(mem_flags::mem_threadgroup);

            if (tid < 16) thread_sum[tid] += thread_sum[tid + 16];
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid < 8) thread_sum[tid] += thread_sum[tid + 8];
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid < 4) thread_sum[tid] += thread_sum[tid + 4];
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid < 2) thread_sum[tid] += thread_sum[tid + 2];
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid < 1) thread_sum[tid] += thread_sum[tid + 1];
            threadgroup_barrier(mem_flags::mem_threadgroup);

            const half variance = thread_sum[0] / half(hidden_size);
            const half inv_std = rsqrt(variance + 1e-5h);

            // Normalize and scale
            for (uint i = tid; i < hidden_size; i += 32) {
                const half norm = (input[offset + i] - mean) * inv_std;
                output[offset + i] = gamma[i] * norm + beta[i];
            }
        }
        """

    def _get_activation_kernel(self) -> str:
        """Get optimized activation kernel"""
        return """
        #include <metal_stdlib>
        using namespace metal;

        kernel void gelu(
            device const half* input [[ buffer(0) ]],
            device half* output [[ buffer(1) ]],
            constant uint& size [[ buffer(2) ]],
            uint tid [[ thread_position_in_threadgroup ]],
            uint gid [[ threadgroup_position_in_grid ]]
        ) {
            const uint idx = gid * 256 + tid;
            if (idx >= size) return;

            // Constants for GELU approximation
            constexpr half sqrt_2_over_pi = 0.7978845608028654h;
            constexpr half coef = 0.044715h;

            half x = input[idx];
            half cdf = 0.5h * (1.0h + tanh(
                sqrt_2_over_pi * x * (1.0h + coef * x * x)
            ));

            output[idx] = x * cdf;
        }
        """

    def _get_softmax_kernel(self) -> str:
        """Get optimized softmax kernel"""
        return """
        #include <metal_stdlib>
        using namespace metal;

        kernel void softmax(
            device const half* input [[ buffer(0) ]],
            device half* output [[ buffer(1) ]],
            constant uint2& dims [[ buffer(2) ]],
            uint2 tid [[ thread_position_in_threadgroup ]],
            uint2 gid [[ threadgroup_position_in_grid ]]
        ) {
            const uint row = gid.y;
            const uint offset = row * dims.x;

            // Find max value
            half max_val = -INFINITY;
            for (uint i = tid.x; i < dims.x; i += 32) {
                max_val = max(max_val, input[offset + i]);
            }

            threadgroup half thread_max[32];
            thread_max[tid.x] = max_val;
            threadgroup_barrier(mem_flags::mem_threadgroup);

            if (tid.x < 16) thread_max[tid.x] = max(thread_max[tid.x], thread_max[tid.x + 16]);
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid.x < 8) thread_max[tid.x] = max(thread_max[tid.x], thread_max[tid.x + 8]);
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid.x < 4) thread_max[tid.x] = max(thread_max[tid.x], thread_max[tid.x + 4]);
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid.x < 2) thread_max[tid.x] = max(thread_max[tid.x], thread_max[tid.x + 2]);
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid.x < 1) thread_max[tid.x] = max(thread_max[tid.x], thread_max[tid.x + 1]);
            threadgroup_barrier(mem_flags::mem_threadgroup);

            const half row_max = thread_max[0];

            // Calculate exp sum
            half exp_sum = 0.0h;
            for (uint i = tid.x; i < dims.x; i += 32) {
                exp_sum += exp(input[offset + i] - row_max);
            }

            threadgroup half thread_sum[32];
            thread_sum[tid.x] = exp_sum;
            threadgroup_barrier(mem_flags::mem_threadgroup);

            if (tid.x < 16) thread_sum[tid.x] += thread_sum[tid.x + 16];
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid.x < 8) thread_sum[tid.x] += thread_sum[tid.x + 8];
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid.x < 4) thread_sum[tid.x] += thread_sum[tid.x + 4];
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid.x < 2) thread_sum[tid.x] += thread_sum[tid.x + 2];
            threadgroup_barrier(mem_flags::mem_threadgroup);
            if (tid.x < 1) thread_sum[tid.x] += thread_sum[tid.x + 1];
            threadgroup_barrier(mem_flags::mem_threadgroup);

            const half inv_sum = 1.0h / thread_sum[0];

            // Calculate softmax
            for (uint i = tid.x; i < dims.x; i += 32) {
                output[offset + i] = exp(input[offset + i] - row_max) * inv_sum;
            }
        }
        """

    async def compile_kernel(self,
                           name: str,
                           source: str,
                           entry_point: str,
                           constants: Dict[str, Any]) -> MetalKernel:
        """Compile Metal kernel with optimizations"""
        try:
            if self.compiler is None:
                raise RuntimeError("Metal compiler not available")

            # Get kernel source
            kernel_source = source
            if name in self.kernel_library:
                kernel_source = self.kernel_library[name]

            # Create function constant values
            constant_values = mtl.MTLFunctionConstantValues.alloc().init()
            for key, value in constants.items():
                constant_values.setConstantValue_type_(value, mtl.MTLDataTypeFloat)

            # Create function
            function = self.compiler.newFunction_constantValues_error_(
                entry_point,
                constant_values,
                None
            )
            if function is None:
                raise RuntimeError(f"Failed to create function: {entry_point}")

            # Create compute pipeline
            pipeline_descriptor = mtl.MTLComputePipelineDescriptor.alloc().init()
            pipeline_descriptor.setComputeFunction_(function)

            # Set optimization options
            options = pipeline_descriptor.computePipelineState().options
            if self.opt_level >= 1:
                options |= mtl.MTLPipelineOptionArgumentInfo
            if self.opt_level >= 2:
                options |= mtl.MTLPipelineOptionBufferTypeInfo
            if self.opt_level >= 3:
                options |= mtl.MTLPipelineOptionFastMathEnabled

            pipeline_state = self.device.newComputePipelineStateWithDescriptor_options_reflection_error_(
                pipeline_descriptor,
                options,
                None,
                None
            )
            if pipeline_state is None:
                raise RuntimeError("Failed to create pipeline state")

            return MetalKernel(
                id=name,
                pipeline_state=pipeline_state,
                thread_execution_width=pipeline_state.threadExecutionWidth(),
                max_total_threads_per_threadgroup=pipeline_state.maxTotalThreadsPerThreadgroup(),
                static_threadgroup_memory_length=pipeline_state.staticThreadgroupMemoryLength()
            )

        except Exception as e:
            self._logger.error(f"Failed to compile kernel {name}: {e}")
            raise

    def get_kernel(self, name: str) -> Optional[Any]:
        """Get pre-compiled kernel from library"""
        return self.kernel_library.get(name)
