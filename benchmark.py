import asyncio
import time
import re
import httpx

FASTAPI_URL = "http://localhost:8000/api/v1/execute"

SCENARIOS = {
    "Lightweight Arithmetic Task": {
        "instruction": "calculate 2 + 2",
        "thread_id_prefix": "benchmark_light"
    },
    "Medium Code Generation Logic": {
        "instruction": "calculate the factorial of a number",
        "thread_id_prefix": "benchmark_medium"
    },
    "Heavy Structural Telemetry Logic": {
        "instruction": "filter list of dictionary containing temperature data and return average of items above threshold 50",
        "thread_id_prefix": "benchmark_heavy"
    }
}


def _parse_real_tokens(logs: list[str]) -> tuple[int, float]:
    """Logs se real TOKENS aur EVAL_NS nikaalta hai (jo humne nodes.py me add kiya).
    Agar kisi wajah se na mile (purana format), to 0 return karta hai."""
    total_tokens = 0
    total_eval_ns = 0
    for line in logs:
        match = re.search(r"TOKENS:(\d+)\s*\|\s*EVAL_NS:(\d+)", line)
        if match:
            total_tokens += int(match.group(1))
            total_eval_ns += int(match.group(2))
    return total_tokens, total_eval_ns


async def profile_scenario(client: httpx.AsyncClient, name: str, instruction: str, thread_id: str) -> dict:
    payload = {"instruction": instruction, "thread_id": thread_id}
    start_time = time.perf_counter()
    try:
        response = await client.post(FASTAPI_URL, json=payload, timeout=120.0)
        elapsed = time.perf_counter() - start_time

        if response.status_code != 200:
            return {"scenario": name, "status": "HTTP_ERROR", "tokens": 0,
                    "compute_time": 0.0, "throughput": 0.0, "latency": round(elapsed, 2),
                    "error": f"Bad Status: {response.status_code}"}

        data = response.json()
        logs = data.get("logs", [])
        real_tokens, real_eval_ns = _parse_real_tokens(logs)

        # Real Ollama-reported eval time use karo agar mila, warna round-trip latency pe fallback karo
        compute_time = (real_eval_ns / 1e9) if real_eval_ns > 0 else elapsed
        throughput = (real_tokens / compute_time) if compute_time > 0 else 0

        return {
            "scenario": name,
            "status": data.get("status", "UNKNOWN"),
            "tokens": real_tokens,
            "compute_time": round(compute_time, 2),
            "throughput": round(throughput, 2),
            "latency": round(elapsed, 2),
            "error": None
        }
    except Exception as err:
        elapsed = time.perf_counter() - start_time
        return {"scenario": name, "status": "CRASHED", "tokens": 0,
                "compute_time": 0.0, "throughput": 0.0, "latency": round(elapsed, 2),
                "error": str(err)}


def _print_table(title: str, results: list[dict]):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print("| Scenario Layer | Tokens (real) | Compute Time (s) | Throughput (tok/s) | Round Trip (s) |")
    print("| :--- | :---: | :---: | :---: | :---: |")
    for r in results:
        if r["error"]:
            print(f"| **{r['scenario']}** | `FAIL` | `FAIL` | `FAIL` | {r['latency']}s (Error: {r['error'][:40]}) |")
        else:
            print(f"| **{r['scenario']}** | {r['tokens']} | {r['compute_time']}s | {r['throughput']} | {r['latency']}s |")
    print("=" * 80)


async def main():
    print("=" * 80)
    print("🔥 ENTERPRISE AI SAFE-MESH PERFORMANCE HARNESS")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        # Warm-up — model weights ko RAM me load karwao, cold-start distortion avoid karo
        print("\n⏳ Warm-up run (loading model into RAM)...")
        await profile_scenario(client, "Warm-up", "say hi", "warmup_999")
        print("✅ Warm-up done.\n")

        # 🌟 SECTION 1: SEQUENTIAL — asli, clean per-task model speed
        # Ye batata hai: "ek single request ko process karne me model ko kitna time lagta hai"
        print("▶️  Running SEQUENTIAL benchmark (one request at a time)...")
        sequential_results = []
        for name, cfg in SCENARIOS.items():
            r = await profile_scenario(client, name, cfg["instruction"], f"{cfg['thread_id_prefix']}_seq")
            sequential_results.append(r)
        _print_table("📊 SEQUENTIAL BENCHMARK (Real Per-Task Model Speed)", sequential_results)

        # 🌟 SECTION 2: CONCURRENT — system kitna stable hai jab multiple requests ek saath aayein
        # Ye batata hai: "queueing behavior, total system throughput under simultaneous load"
        print("\n▶️  Running CONCURRENT load test (all requests fired simultaneously)...")
        concurrent_start = time.perf_counter()
        tasks = [
            profile_scenario(client, name, cfg["instruction"], f"{cfg['thread_id_prefix']}_concurrent")
            for name, cfg in SCENARIOS.items()
        ]
        concurrent_results = await asyncio.gather(*tasks)
        concurrent_total_time = time.perf_counter() - concurrent_start
        _print_table("📊 CONCURRENT LOAD TEST (3 Simultaneous Requests)", concurrent_results)
        print(f"\n⏱️  Total wall-clock time for all 3 concurrent requests: {round(concurrent_total_time, 2)}s")
        print("   (Note: Ollama processes one request at a time internally — this measures")
        print("    total system throughput under simultaneous load, NOT parallel model inference.)")

    print("\n💡 Copy both tables above into README.md under separate headers:")
    print("   'Sequential Benchmark' and 'Concurrent Load Test'")


if __name__ == "__main__":
    asyncio.run(main())