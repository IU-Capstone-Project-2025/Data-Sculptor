#!/bin/bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate base

MKL_THREADING_LAYER=GNU \
CUDA_VISIBLE_DEVICES=0,1 \
python -m sglang.launch_server \
  --model-path /home/developer/.cache/huggingface/hub/models--Qwen--Qwen3-30B-A3B/snapshots/ae659febe817e4b3ebd7355f47792725801204c9 \
  --host 0.0.0.0 \
  --port 9362 \
  --mem-fraction-static 0.85 \
  --context-length 32768 \
  --chunked-prefill-size 8192 \
  --reasoning-parser qwen3 \
  --enable-mixed-chunk \
  --attention-backend fa3 \
  --enable-p2p-check \
  --cuda-graph-max-bs 512 \
  --tp 2 \
  >> sglang_server.log 2>&1 