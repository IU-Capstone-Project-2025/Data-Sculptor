# LLM Inference Performance Benchmark

This benchmark suite is designed to tune and evaluate LLM inference performance across different configurations and frameworks.

## Overview

The benchmark tests various aspects of LLM inference including:
- Long output generation performance
- Long input processing performance  
- Copy operation performance
- Different thinking modes (enabled/disabled)

## Current Status

**⚠️ Limited Reproducibility**: This benchmark is currently not fully reproducible outside the main development server environment. The setup requires complex CUDA configurations and kernel installations that are specific to our infrastructure.

## Framework Support

The benchmark currently supports:
- **SGLang**: Base and FlashAttention configurations
- **vLLM**: FlashInfer configuration

## Usage

1) Ensure that you are on the main development server.
2) Run `./latency_bench.py` to run the benchmark.