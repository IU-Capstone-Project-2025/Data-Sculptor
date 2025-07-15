#!/usr/bin/env bash
###############################################################################
# Semantic-evaluation pipeline — with robust, interrupt-safe signal handling. #
###############################################################################

set -e                # abort on un-handled error
set -o pipefail       # fail a pipeline if any element fails

###############################################################################
# Logging helper
log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

###############################################################################
# Signal-handling state
# `CHILD_TARGET` stores the identifier we have to send signals to:
#   * "-<PGID>" when we successfully started the Python process in a new
#     process-group via `setsid` (Linux or macOS with `setsid` present).
#   * "<PID>"  (just the child’s PID) when `setsid` is unavailable (older
#     macOS versions).  In that case we lose the ability to signal the whole
#     process-group, but still terminate the main process correctly.
CHILD_TARGET=""   # signal target of the active Python job, if any

###############################################################################
# Cleanup on exit / interrupt
cleanup() {
    log "Cleaning up …"

    # Forward the interrupt to the running Python job / group (if still alive)
    if [[ -n "$CHILD_TARGET" ]] && kill -0 "$CHILD_TARGET" 2>/dev/null; then
        log "Forwarding SIGINT to child ($CHILD_TARGET)"
        kill -INT "$CHILD_TARGET" 2>/dev/null || true
        wait "$CHILD_TARGET" 2>/dev/null || true
    fi

    # Deactivate Conda if this script activated it
    if [[ "$CONDA_DEFAULT_ENV" == "$CONDA_ENV_NAME" ]]; then
        conda deactivate
        log "Conda environment deactivated."
    fi
}

# Trap INT/TERM to run cleanup, then exit with 130 (standard for SIGINT)
trap 'cleanup; exit 130' INT TERM
# Also run cleanup on normal script exit
trap cleanup EXIT

###############################################################################
# Helper: run a Python command in its own process-group
run_python() {
    if command -v setsid >/dev/null 2>&1; then
        # systems with `setsid` (most Linux distros, newer macOS)
        setsid python "$@" &
        local child_pid=$!
        CHILD_TARGET="-$child_pid"   # negative PGID → whole group
    else
        # fallback for macOS where `setsid` is unavailable
        python "$@" &
        local child_pid=$!
        CHILD_TARGET="$child_pid"    # only the main process
    fi

    # Propagate the child's exit status back to the caller
    wait "$child_pid"
    CHILD_TARGET=""
}

###############################################################################
# --- ORIGINAL SCRIPT STARTS HERE (unchanged sections abridged for clarity) ---
###############################################################################

# Usage check
usage() {
    echo "Usage: $0 <input_dir> <output_dir>"
    exit 1
}
[[ $# -eq 2 ]] || { usage; }

INPUT_DIR=$1
OUTPUT_DIR=$2
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEMANTIC_EVAL_DIR="$SCRIPT_DIR"

log "Starting semantic evaluation pipeline…"
log "Input directory:  $INPUT_DIR"
log "Output directory: $OUTPUT_DIR"

# ... (all your existing validation, .env checks, conda-env creation etc.) ...

###############################################################################
# Activate environment and install requirements (unchanged)
###############################################################################
CONDA_ENV_NAME="semantic_eval"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$CONDA_ENV_NAME"
pip install -q -r "$SEMANTIC_EVAL_DIR/requirements.txt"

mkdir -p "$OUTPUT_DIR"

###############################################################################
# Run evaluation
###############################################################################
log "=========================================="
log "Running evaluation…"
log "=========================================="
run_python "$SEMANTIC_EVAL_DIR/evaluate.py"  \
           --input_dir  "$INPUT_DIR"         \
           --output_dir "$OUTPUT_DIR"

###############################################################################
# Run metrics post-processing
###############################################################################
log "=========================================="
log "Processing metrics…"
log "=========================================="
run_python "$SEMANTIC_EVAL_DIR/metrics_processing.py" \
           --input_file "$OUTPUT_DIR/evaluation_results.json" \
           --output_dir "$OUTPUT_DIR"

###############################################################################
# Final reporting
###############################################################################
log "=========================================="
log "Pipeline completed successfully!"
log "=========================================="
log "Results saved to: '$OUTPUT_DIR'"

shopt -s nullglob
for file in "$OUTPUT_DIR"/*.json "$OUTPUT_DIR"/*.md; do
    [[ -e "$file" ]] && echo "  $(basename "$file")"
done
shopt -u nullglob

log "✓ Semantic evaluation pipeline completed!"
