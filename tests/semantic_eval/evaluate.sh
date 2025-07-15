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
# `CHILD_SIG_TARGET` holds the identifier we must send signals to:
#   * "-<PGID>" when the child was started in its own process-group via `setsid`.
#   * "<PID>"   (positive) when `setsid` is unavailable and the child runs in
#     the same group as the script.
#
# We also track `CHILD_PID` separately because `wait` only accepts *PIDs*,
# not negative PGIDs.  Mixing the two caused broken Ctrl-C handling before.
CHILD_PID=""         # PID of the active Python job, if any
CHILD_SIG_TARGET=""  # Target (PID or -PGID) for signal forwarding

###############################################################################
# Cleanup on exit / interrupt
cleanup() {
    log "Cleaning up …"

    # Forward the interrupt (and, if necessary, escalate) to the running
    # Python job / group so that the pipeline reliably stops.
    if [[ -n "$CHILD_PID" ]] && kill -0 "$CHILD_PID" 2>/dev/null; then
        log "Forwarding SIGINT to child ($CHILD_SIG_TARGET)"
        kill -INT "$CHILD_SIG_TARGET" 2>/dev/null || true

        # Give the child a moment to exit gracefully.
        sleep 1

        # If it is still alive, escalate to SIGTERM and finally SIGKILL.
        if kill -0 "$CHILD_PID" 2>/dev/null; then
            log "Child still running — sending SIGTERM…"
            kill -TERM "$CHILD_SIG_TARGET" 2>/dev/null || true
            sleep 1
        fi

        if kill -0 "$CHILD_PID" 2>/dev/null; then
            log "Child stubborn — sending SIGKILL!"
            kill -KILL "$CHILD_SIG_TARGET" 2>/dev/null || true
        fi

        # Reap the child; use PID (positive) because `wait` dislikes -PGID.
        wait "$CHILD_PID" 2>/dev/null || true
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
        # Systems with `setsid` (most Linux distros, newer macOS)
        setsid python "$@" &
        CHILD_PID=$!
        CHILD_SIG_TARGET="-$CHILD_PID"   # negative PGID → whole group
    else
        # Fallback for macOS where `setsid` is unavailable
        python "$@" &
        CHILD_PID=$!
        CHILD_SIG_TARGET="$CHILD_PID"    # only the main process
    fi

    # Propagate the child's exit status back to the caller.  `wait` accepts
    # only PIDs, so we use `CHILD_PID` (positive) here.
    wait "$CHILD_PID"

    # Clear tracking variables once the child has finished.
    CHILD_PID=""
    CHILD_SIG_TARGET=""
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
