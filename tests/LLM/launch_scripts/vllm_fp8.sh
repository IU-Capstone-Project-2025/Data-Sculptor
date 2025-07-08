#!/bin/bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate vllm

CUDA_VISIBLE_DEVICES=0,1 vllm serve Qwen/Qwen3-30B-A3B-FP8 \
  --host 0.0.0.0 \
  --port 9362 \
  --enable-prefix-caching \
  --max-model-len 32768 \
  --max-num-batched-tokens 2048 \
  --gpu_memory_utilization 0.90 \
  --enable-chunked-prefill \
  --reasoning-parser qwen3 \
  --tensor-parallel-size 2 \
  --disable-log-requests \
  >> vllm_server.log 2>&1
