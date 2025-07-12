#!/bin/bash

set -e  # Exit on any error

# Function to display usage
usage() {
    echo "Usage: $0 <input_dir> <output_dir>"
    echo "  input_dir: Directory containing test case folders with profile.ipynb and solution.ipynb"
    echo "  output_dir: Directory where results will be saved"
    exit 1
}

# Function to log messages with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if correct number of arguments provided
if [ $# -ne 2 ]; then
    echo "Error: Incorrect number of arguments."
    usage
fi

INPUT_DIR="$1"
OUTPUT_DIR="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEMANTIC_EVAL_DIR="$SCRIPT_DIR"

log "Starting semantic evaluation pipeline..."
log "Input directory: $INPUT_DIR"
log "Output directory: $OUTPUT_DIR"

# Step 1: Check if input directory exists
if [ ! -d "$INPUT_DIR" ]; then
    log "ERROR: Input directory '$INPUT_DIR' does not exist."
    exit 1
fi

# Step 2: Check if .env file exists
ENV_FILE="$SEMANTIC_EVAL_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    log "ERROR: .env file not found at '$ENV_FILE'"
    log "Please create a .env file with the required environment variables."
    log "Required variables:"
    log "  EVALUATOR_LLM_API_KEY=your_openai_api_key"
    log "Optional variables (with defaults):"
    log "  EVALUATOR_LLM_BASE_URL=https://openrouter.ai/api/v1"
    log "  EVALUATOR_LLM_MODEL=deepseek/deepseek-chat-v3-0324:free"
    log "  LOCAL_LLM_BASE_URL=http://10.100.30.239:9362/v1"
    log "  LOCAL_LLM_API_KEY=vllml"
    log "  LOCAL_LLM_MODEL=Qwen/Qwen3-30B-A3B"
    log "  LOCAL_ENABLE_THINKING=True"
    exit 1
fi

log "✓ Found .env file"

# Step 3: Check if conda is available
if ! command -v conda &> /dev/null; then
    log "ERROR: conda is not installed or not in PATH."
    log "Please install conda or miniconda first."
    exit 1
fi

# Step 4: Create or activate conda environment
CONDA_ENV_NAME="semantic_eval"
log "Setting up conda environment '$CONDA_ENV_NAME'..."

if conda env list | grep -q "^$CONDA_ENV_NAME "; then
    log "✓ Using existing conda environment"
else
    log "Creating conda environment..."
    conda create -n "$CONDA_ENV_NAME" python=3.11 -y -q
    log "✓ Created conda environment"
fi

# Step 5: Activate conda environment and install requirements
log "Activating conda environment..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$CONDA_ENV_NAME"

# Check if requirements.txt exists
REQUIREMENTS_FILE="$SEMANTIC_EVAL_DIR/requirements.txt"
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    log "ERROR: requirements.txt not found at '$REQUIREMENTS_FILE'"
    exit 1
fi

log "Installing requirements..."
pip install -q -r "$REQUIREMENTS_FILE"
log "✓ Requirements installed"

# Step 6: Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"
log "✓ Output directory ready"

# Step 7: Change to semantic_eval directory to run scripts
cd "$SEMANTIC_EVAL_DIR"

# Step 8: Run evaluate.py
log "==========================================  "
log "Running evaluation..."
log "=========================================="
python evaluate.py --input_dir "$INPUT_DIR" --output_dir "$OUTPUT_DIR"

if [ $? -eq 0 ]; then
    log "✓ Evaluation completed"
else
    log "ERROR: Evaluation failed"
    exit 1
fi

# Step 9: Run metrics_processing.py
log "=========================================="
log "Processing metrics..."
log "=========================================="
python metrics_processing.py --input_dir "$OUTPUT_DIR" --output_dir "$OUTPUT_DIR"

if [ $? -eq 0 ]; then
    log "✓ Metrics processing completed"
else
    log "ERROR: Metrics processing failed"
    exit 1
fi

# Step 10: Show final results
log "=========================================="
log "Pipeline completed successfully!"
log "=========================================="
log "Results saved to: '$OUTPUT_DIR'"

# Show key generated files
log "Key files generated:"
shopt -s nullglob
files=("$OUTPUT_DIR"/*.json "$OUTPUT_DIR"/*.md)
if [ ${#files[@]} -gt 0 ]; then
    for file in "${files[@]}"; do
        echo "  $(basename "$file")"
    done
else
    echo "  (no report files found)"
fi
shopt -u nullglob

log "✓ Semantic evaluation pipeline completed!"

# Deactivate conda environment
conda deactivate