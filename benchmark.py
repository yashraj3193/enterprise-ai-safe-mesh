import asyncio
import time
import httpx

FASTAPI_URL = "http://localhost:8000/api/v1/execute"

# Test scenarios representing our three target layers
SCENARIOS = {
    "Lightweight Arithmetic Task": {
        "instruction": "calculate 2 + 2",
        "thread_id": "benchmark_light_101"
    },
    "Medium Code Generation Logic": {
        "instruction": "calculate the factorial of a number",
        "thread_id": "benchmark_medium_102"
    },
    "Heavy Structural Telemetry Logic": {
        "instruction": "filter list of dictionary containing temperature data and return average of items above threshold 50",
        "thread_id": "benchmark_heavy_103"
    }
}

def estimate_tokens(text: str) -> int:
    """Helper to estimate token count based on standard code character-to-token ratio."""
    if not text:
        return 0
    # Average of 4 characters per token is standard for code tokenizers
    return max(1, len(text) // 4)

async def profile_scenario(name: str, payload: dict) -> dict:
    print(f"🚀 Profiling pipeline for: '{name}'...")
    start_time = time.perf_counter()
    
    # Large timeout to allow local CPU quantized Llama 3.2 to think
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(FASTAPI_URL, json=payload)
            end_time = time.perf_counter()
            
            round_trip_latency = end_time - start_time
            
            if response.status_code == 200:
                data = response.json()
                generated_code = data.get("current_code", "") or ""
                
                # Approximate output tokens
                tokens_count = estimate_tokens(generated_code)
                
                # Rough model compute time estimation (ignoring network trip variance)
                # Usually network overhead is minimal on localhost (~2-5ms)
                compute_time = max(0.1, round_trip_latency - 0.05) 
                throughput = tokens_count / compute_time
                
                return {
                    "scenario": name,
                    "status": data.get("status", "UNKNOWN"),
                    "tokens": tokens_count,
                    "compute_time": round(compute_time, 2),
                    "throughput": round(throughput, 2),
                    "latency": round(round_trip_latency, 2),
                    "error": None
                }
            else:
                return {
                    "scenario": name,
                    "status": "HTTP_ERROR",
                    "tokens": 0,
                    "compute_time": 0.0,
                    "throughput": 0.0,
                    "latency": round(round_trip_latency, 2),
                    "error": f"Bad Status: {response.status_code}"
                }
                
        except Exception as err:
            end_time = time.perf_counter()
            return {
                "scenario": name,
                "status": "CRASHED",
                "tokens": 0,
                "compute_time": 0.0,
                "throughput": 0.0,
                "latency": round(end_time - start_time, 2),
                "error": str(err)
            }

async def main():
    print("=========================================================================")
    print("🔥 STARTING AUTOMATED ENTERPRISE AI SAFE-MESH PERFORMANCE HARNESS 🔥")
    print("=========================================================================\n")
    
    # Warm-up run to load Llama weights into RAM and prevent cold-start anomalies
    print("⏳ Running cold-start warm-up task (this might take a few seconds)...")
    await profile_scenario("Warm-up Task", {"instruction": "say hi", "thread_id": "warmup_999"})
    print("✅ System warm-up completed! Initiating parallel stress-test...\n")
    
    # Execute scenarios asynchronously using asyncio.gather()
    tasks = [profile_scenario(name, data) for name, data in SCENARIOS.items()]
    results = await asyncio.gather(*tasks)
    
    print("\n" + "="*80)
    print("📊 DYNAMIC TELEMETRY REPORT (Markdown Format for README.md)")
    print("="*80)
    
    print("| Scenario Layer | Tokens Generated | Compute Time (s) | Model Throughput (tokens/s) | Round Trip Latency (s) |")
    print("| :--- | :---: | :---: | :---: | :---: |")
    
    for r in results:
        if r["error"]:
            print(f"| **{r['scenario']}** | `FAIL` | `FAIL` | `FAIL` | {r['latency']}s (Error: {r['error'][:25]}...) |")
        else:
            print(f"| **{r['scenario']}** | {r['tokens']} | {r['compute_time']}s | {r['throughput']} | {r['latency']}s |")
            
    print("="*80 + "\n")
    print("💡 Copy the table above and paste it directly into your README.md to keep your portfolio live!")

if __name__ == "__main__":
    asyncio.run(main())