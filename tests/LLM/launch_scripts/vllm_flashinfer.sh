#!/bin/bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate vllm2

NCCL_CUMEM_ENABLE=1 \
OMP_NUM_THREADS=4 \
CUDA_VISIBLE_DEVICES=0,1 \
vllm serve /home/developer/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ae659febe817e4b3ebd7355f47792725801204c9 \
  --host 0.0.0.0 \
  --port 9362 \
  --enable-prefix-caching \
  --max-model-len 32768 \
  --max-num-batched-tokens 8192 \
  --gpu_memory_utilization 0.90 \
  --enable-chunked-prefill \
  --reasoning-parser qwen3 \
  --tensor-parallel-size 1 \
  --disable-log-requests \
  >> vllm_server.log 2>&1