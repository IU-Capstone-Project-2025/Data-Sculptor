"""
latency_bench.py

Benchmark LLM API latency for different token sizes and enable_thinking values.

Usage:
    python latency_bench.py --api-url <API_URL> --model <MODEL_PATH>

Public API:
    main()
"""

import uuid
import subprocess
import psutil
import time
import logging
import signal
import os
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

import requests
from requests.exceptions import RequestException
from tabulate import tabulate

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CONFIG_PATH = Path(__file__).with_name("bench_config.json")
if not CONFIG_PATH.exists():
    raise FileNotFoundError(f"Benchmark configuration not found at {CONFIG_PATH}")

with CONFIG_PATH.open("r", encoding="utf-8") as _cfg_file:
    _CONFIG = json.load(_cfg_file)

GLOBAL_CFG = _CONFIG.get("global", {})

API_TIMEOUT: int = GLOBAL_CFG.get("api_timeout", 300)
REQUEST_TIMEOUT: int = GLOBAL_CFG.get("request_timeout", 60)
N_REQUESTS: int = GLOBAL_CFG.get("n_requests", 5)
SIZES: List[int] = GLOBAL_CFG.get("sizes", [100, 5000])
PROMPT_TEMPLATE: str = GLOBAL_CFG.get(
    "prompt_template",
    "Generate an arbitrary text of {max_tokens} tokens. Use any topic you want. Don't ask any questions just generate the text.",
)
INPUT_PROMPT_TEMPLATE: str = GLOBAL_CFG.get(
    "input_prompt_template",
    "Please provide a concise summary (4-5 sentences) of the following text:\n\n{text}\n\nSummary:",
)
COPY_PROMPT_TEMPLATE: str = GLOBAL_CFG.get(
    "copy_prompt_template",
    "Repeat the following text verbatim:\n\n{text}\n\nOutput:",
)


def wait_for_api(
    api_url: str, proc: subprocess.Popen, timeout: int = API_TIMEOUT
) -> None:
    """Block until the API is reachable or the server process exits.

    Args:
        api_url: Endpoint to poll (POST).
        proc: Handle of the running server process.
        timeout: Seconds to wait before raising ``TimeoutError``.

    Raises:
        RuntimeError: If the underlying launch script terminates before the API is ready.
        TimeoutError: If the timeout is reached without readiness.
    """

    logging.debug(f"Waiting for API to be ready at {api_url} ...")
    start = time.time()

    while time.time() - start < timeout:
        # 1) Poll the server process – if it died, surface stderr and abort early
        retcode = proc.poll()
        if retcode is not None:
            stderr_output = (
                proc.stderr.read().decode("utf-8", errors="ignore")
                if proc.stderr
                else ""
            )
            raise RuntimeError(
                f"Launch script exited with code {retcode} before API became ready.\nLast stderr:\n{stderr_output}"
            )

        # 2) Ping the endpoint; treat 200/400 as readiness (400 for malformed request)
        try:
            response = requests.post(api_url, timeout=5)
            # If we get *any* HTTP response below 500, assume the server is up.
            # 5xx typically means not ready or internal failure during startup.
            if response.status_code < 500:
                logging.debug("API is ready (status %s).", response.status_code)
                return
        except Exception:
            pass  # server not up yet

        time.sleep(1)

    raise TimeoutError(f"API not ready after {timeout} seconds.")


def run_launch_script(script_path: str) -> subprocess.Popen:
    """Launch the LLM server via the provided shell script.

    Args:
        script_path (str): Path to the ``.sh`` launch script to execute.

    Returns:
        subprocess.Popen: Handle of the started server process (session leader).
    """

    # Resolve possible script locations
    provided = Path(script_path).expanduser()
    repo_root = CONFIG_PATH.parent.parent.parent.resolve()

    candidates = []
    # 1. If provided is absolute, try as-is
    if provided.is_absolute():
        candidates.append(provided)
        # If starts with /launch_scripts/, also try inside tests/LLM/
        if provided.parts[1] == "launch_scripts":
            candidates.append(
                CONFIG_PATH.parent / "launch_scripts" / Path(*provided.parts[2:])
            )
            candidates.append(
                repo_root
                / "tests"
                / "LLM"
                / "launch_scripts"
                / Path(*provided.parts[2:])
            )
            candidates.append(repo_root / "launch_scripts" / Path(*provided.parts[2:]))
    else:
        # Relative path - first relative to config dir
        candidates.append(CONFIG_PATH.parent / provided)
        # Then relative to repo root
        candidates.append(repo_root / provided)

    resolved = None
    for cand in candidates:
        if cand.exists():
            resolved = cand.resolve()
            break

    if resolved is None:
        raise FileNotFoundError(
            "Launch script not found. Tried:\n" + "\n".join(str(c) for c in candidates)
        )

    logging.debug(f"Launching server using script: {resolved} …")

    proc = subprocess.Popen(
        ["bash", str(resolved)],
        cwd=str(resolved.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,  # Start new session so we can terminate entire group
    )
    return proc


def _kill_process_on_port(port: int) -> None:
    """Force-kill any process that is currently bound to *port* using psutil."""

    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr.port == port and conn.pid:
            try:
                os.kill(conn.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                continue


def stop_serve_command(proc: subprocess.Popen, port: int) -> None:
    """Terminate the API server process tree and free the benchmark port.

    The function makes *best effort* to ensure no leftover child processes are
    alive after return, so that the next benchmark can start its own server on
    the same port.
    """
    if proc.poll() is not None:
        # Process already finished – still run cleanup in case orphans remain.
        logging.debug("Server process already exited; running orphan cleanup …")
    else:
        logging.debug("Terminating API server (pid=%s) …", proc.pid)

        # 1. Graceful SIGTERM to the original process group.
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass  # Group gone
        except Exception as exc:
            logging.warning("Failed to SIGTERM process group: %s", exc)

        # 2. Wait up to 10 s for clean exit, then escalate.
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logging.warning("Graceful termination timed out; sending SIGKILL …")
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except Exception as exc:
                logging.error("Failed to SIGKILL process group: %s", exc)

    def _terminate(proc_: "psutil.Process") -> None:
        try:
            proc_.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return

    # Collect all candidate processes whose cmdline references sglang.
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = " ".join(p.info["cmdline"] or [])
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
        if "sglang.launch_server" in cmdline:
            _terminate(p)

    # Kill any process still bound to the benchmark port (9362) – this
    # covers detached uvicorn workers or CUDA procs that listen via gRPC.
    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr.port == port and conn.pid:
            try:
                _terminate(psutil.Process(conn.pid))
            except psutil.NoSuchProcess:
                pass

    # Give processes time to exit, then hard-kill if necessary.
    try:
        descendants = psutil.Process(proc.pid).children(recursive=True)
    except psutil.NoSuchProcess:
        descendants = []

    if descendants:
        gone, alive = psutil.wait_procs(descendants, timeout=5)
        for p in alive:
            try:
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    # Final safeguard: ensure nothing is still listening on the target port.
    _kill_process_on_port(port)

    logging.debug("API server cleanup completed.")


def send_request(
    api_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    enable_thinking: bool,
) -> Tuple[float, int]:
    """Send a single request to the LLM API and measure latency.

    Args:
        api_url (str): The API endpoint URL.
        model (str): Model path or name.
        prompt (str): The prompt to send to the API.
        max_tokens (int): Number of tokens to generate.
        enable_thinking (bool): Value for chat_template_kwargs.enable_thinking.

    Returns:
        Tuple[float, int]: (latency in seconds, tokens generated)
    """
    payload = {
        "model": model,
        # Add a unique identifier to the prompt to avoid caching
        "messages": [{"role": "user", "content": str(uuid.uuid4()) + " " + prompt}],
        "chat_template_kwargs": {"enable_thinking": enable_thinking},
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    start = time.time()
    try:
        response = requests.post(api_url, json=payload, timeout=REQUEST_TIMEOUT)
        latency = time.time() - start
        response.raise_for_status()
        data = response.json()
        # Try to get the number of tokens generated from the response
        tokens = max_tokens
        if "usage" in data and "completion_tokens" in data["usage"]:
            tokens = data["usage"]["completion_tokens"]
        elif "choices" in data and data["choices"] and "text" in data["choices"][0]:
            tokens = len(data["choices"][0]["text"].split())
        return latency, tokens
    except RequestException as e:
        logging.warning(f"Request failed: {e}")
        return float("inf"), 0
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return float("inf"), 0


def benchmark_long_output(
    api_url: str,
    model: str,
    enable_thinking: bool,
) -> List[Dict[str, Any]]:
    """Run benchmarks for varying *output* sizes while keeping input prompt short.

    Args:
        api_url (str): The API endpoint URL.
        model (str): Model path or name.
        enable_thinking (bool): Value for chat_template_kwargs.enable_thinking.

    Returns:
        List[Dict[str, Any]]: List of results per token size.
    """
    results = []
    for output_tokens in SIZES:
        latencies: List[float] = []
        toks_per_sec: List[float] = []
        logging.debug(
            f"Benchmarking (long output): enable_thinking={enable_thinking}, output_tokens={output_tokens}"
        )
        for _ in range(N_REQUESTS):
            prompt = PROMPT_TEMPLATE.format(max_tokens=output_tokens)
            latency, tokens_generated = send_request(
                api_url, model, prompt, output_tokens, enable_thinking
            )
            if latency == float("inf") or tokens_generated == 0:
                continue
            latencies.append(latency)
            toks_per_sec.append(tokens_generated / latency if latency > 0 else 0)
        if latencies:
            mean_lat = sum(latencies) / len(latencies)
            median_lat = sorted(latencies)[len(latencies) // 2]
            mean_tps = sum(toks_per_sec) / len(toks_per_sec)
            median_tps = sorted(toks_per_sec)[len(toks_per_sec) // 2]
        else:
            mean_lat = median_lat = mean_tps = median_tps = float("nan")
        results.append(
            {
                "output_tokens": output_tokens,
                "mean_latency": mean_lat,
                "median_latency": median_lat,
                "mean_tok/s": mean_tps,
                "median_tok/s": median_tps,
            }
        )
    return results


def print_table_long_output(
    results: List[Dict[str, Any]],
    enable_thinking: bool,
) -> None:
    """Pretty-print results for the *long-output* benchmark."""

    _print_table_generic(
        results,
        token_key="output_tokens",
        title=f"Long Output – Enable Thinking: {enable_thinking}",
    )


def _make_long_input_prompt(num_tokens: int) -> str:
    """Construct a realistic long-input prompt for summarization.

    A block of pseudo-natural language text (repeated Lorem Ipsum paragraphs) is
    generated until it reaches roughly ``num_tokens`` space-separated tokens.
    This text is then inserted into ``INPUT_PROMPT_TEMPLATE`` via the
    ``{text}`` placeholder.

    Args:
        num_tokens: Target token length for the *input* article text.

    Returns:
        Full prompt string to send to the model.
    """

    lorem_paragraph = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus."
        " Suspendisse lectus tortor, dignissim sit amet, adipiscing nec, ultricies sed, dolor."
        " Cras elementum ultrices diam. Maecenas ligula massa, varius a, semper congue, euismod non, mi."
    )

    words: List[str] = []
    while len(words) < num_tokens:
        words.extend(lorem_paragraph.split())

    article_text = " ".join(words[:num_tokens])
    return INPUT_PROMPT_TEMPLATE.format(text=article_text)


def benchmark_long_input(
    api_url: str,
    model: str,
    enable_thinking: bool,
    completion_tokens: int = 1,
) -> List[Dict[str, Any]]:
    """Benchmark latency when *input* prompt length is large and output length is
    relatively small.

    Args:
        api_url (str): The API endpoint URL.
        model (str): Model path or name.
        enable_thinking (bool): Value for ``chat_template_kwargs.enable_thinking``.
        completion_tokens (int, optional): Number of tokens to generate for the
            completion. Defaults to ``1``.

    Returns:
        List[Dict[str, Any]]: Benchmark results keyed by ``input_tokens``.
    """

    results: List[Dict[str, Any]] = []
    for input_tokens in SIZES:
        latencies: List[float] = []
        toks_per_sec: List[float] = []
        logging.debug(
            f"Benchmarking (long input): enable_thinking={enable_thinking}, input_tokens={input_tokens}"
        )

        prompt = _make_long_input_prompt(input_tokens)
        for _ in range(N_REQUESTS):
            latency, output_tokens = send_request(
                api_url,
                model,
                prompt,
                completion_tokens,
                enable_thinking,
            )
            if latency == float("inf"):
                continue

            # Total tokens processed = input + output
            total_tokens = input_tokens + output_tokens
            latencies.append(latency)
            toks_per_sec.append(total_tokens / latency if latency > 0 else 0)

        if latencies:
            mean_lat = sum(latencies) / len(latencies)
            median_lat = sorted(latencies)[len(latencies) // 2]
            mean_tps = sum(toks_per_sec) / len(toks_per_sec)
            median_tps = sorted(toks_per_sec)[len(toks_per_sec) // 2]
        else:
            mean_lat = median_lat = mean_tps = median_tps = float("nan")

        results.append(
            {
                "input_tokens": input_tokens,
                "mean_latency": mean_lat,
                "median_latency": median_lat,
                "mean_tok/s": mean_tps,
                "median_tok/s": median_tps,
            }
        )

    return results


def _print_table_generic(
    results: List[Dict[str, Any]],
    token_key: str,
    title: str,
) -> None:
    """Generic helper to pretty-print a result table.

    Args:
        results: Benchmark records.
        token_key: The column key that represents token counts (e.g. ``"max_tokens"``
            for long-output bench or ``"input_tokens"`` for long-input bench).
        title: Section title to display above the table.
    """

    headers = [
        token_key,
        "mean_latency",
        "median_latency",
        "mean_tok/s",
        "median_tok/s",
    ]
    table = [[r[h] for h in headers] for r in results]
    logging.info("\n" + title + "\n" + tabulate(table, headers=headers, floatfmt=".3f"))


def print_table_long_input(
    results: List[Dict[str, Any]], enable_thinking: bool
) -> None:
    """Pretty-print results for the long-input benchmark."""

    _print_table_generic(
        results,
        token_key="input_tokens",
        title=f"Long Input – Enable Thinking: {enable_thinking}",
    )


def _make_copy_prompt(token_count: int) -> Tuple[str, int]:
    """Generate a prompt that asks the model to repeat a text of *token_count* words.

    Returns both the prompt string and the expected output token length (== token_count).
    """

    lorem_paragraph = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus. "
        "Suspendisse lectus tortor, dignissim sit amet, adipiscing nec, ultricies sed, dolor. "
        "Cras elementum ultrices diam. Maecenas ligula massa, varius a, semper congue, euismod non, mi."
    )
    words: List[str] = []
    while len(words) < token_count:
        words.extend(lorem_paragraph.split())
    text_block = " ".join(words[:token_count])
    prompt = COPY_PROMPT_TEMPLATE.format(text=text_block)
    return prompt, token_count


def benchmark_copy(
    api_url: str,
    model: str,
    enable_thinking: bool,
) -> List[Dict[str, Any]]:
    """Benchmark where input and expected output token lengths are identical.

    Args:
        api_url: API endpoint.
        model: Model name/path.
        enable_thinking: Flag for chat template options.

    Returns:
        List of result dicts keyed by ``copy_tokens``.
    """

    results: List[Dict[str, Any]] = []
    for copy_tokens in SIZES:
        latencies: List[float] = []
        toks_per_sec: List[float] = []
        logging.debug(
            f"Benchmarking (copy) enable_thinking={enable_thinking}, copy_tokens={copy_tokens}"
        )
        prompt, expected_output = _make_copy_prompt(copy_tokens)
        for _ in range(N_REQUESTS):
            latency, generated = send_request(
                api_url,
                model,
                prompt,
                expected_output,
                enable_thinking,
            )
            if latency == float("inf"):
                continue
            total_tokens = copy_tokens + generated  # in theory ~2*copy_tokens
            latencies.append(latency)
            toks_per_sec.append(total_tokens / latency if latency > 0 else 0)

        if latencies:
            mean_lat = sum(latencies) / len(latencies)
            median_lat = sorted(latencies)[len(latencies) // 2]
            mean_tps = sum(toks_per_sec) / len(toks_per_sec)
            median_tps = sorted(toks_per_sec)[len(toks_per_sec) // 2]
        else:
            mean_lat = median_lat = mean_tps = median_tps = float("nan")

        results.append(
            {
                "copy_tokens": copy_tokens,
                "mean_latency": mean_lat,
                "median_latency": median_lat,
                "mean_tok/s": mean_tps,
                "median_tok/s": median_tps,
            }
        )
    return results


def print_table_copy(results: List[Dict[str, Any]], enable_thinking: bool) -> None:
    """Pretty-print copy benchmark results."""
    _print_table_generic(
        results,
        token_key="copy_tokens",
        title="Copy Benchmark – Enable Thinking: False",
    )


def main() -> None:
    """Main entry point.

    Iterates over each benchmark definition found in *bench_config.json*, starts the
    corresponding launch script, executes both long-output and long-input latency
    tests, prints the results, and finally terminates the server process group so
    that GPU resources are released before moving on to the next configuration.
    """

    global_api_url = GLOBAL_CFG.get("api_url", "http://localhost:9362/v1/completions")

    for bench in _CONFIG.get("benchmarks", []):
        name: str = bench.get("name", Path(bench.get("script", "")).stem)
        model_path: str = bench["model"]
        script_path: str = bench["script"]
        api_url = bench.get("api_url", global_api_url)

        logging.info("\n" + "=" * 60)
        logging.info(f"Starting benchmark for configuration: {name}")

        proc = run_launch_script(script_path)
        try:
            wait_for_api(api_url, proc)

            results_out = benchmark_long_output(
                api_url, model_path, enable_thinking=False
            )
            results_in = benchmark_long_input(
                api_url, model_path, enable_thinking=False
            )
            results_copy = benchmark_copy(api_url, model_path, enable_thinking=False)

            # Output results
            print_table_long_output(results_out, enable_thinking=False)
            print_table_long_input(results_in, enable_thinking=False)
            print_table_copy(results_copy, enable_thinking=False)
        except Exception as e:
            logging.error(f"Benchmark failed for {name}: {e}")
        finally:
            parsed = urlparse(api_url)
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            stop_serve_command(proc, port)
            logging.debug(f"Completed benchmark for {name}")


if __name__ == "__main__":
    main()
