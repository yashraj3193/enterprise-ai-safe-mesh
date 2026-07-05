# ⚡ Enterprise AI Safe-Mesh: Resilient Multi-Agent Local Code Execution Engine

An asymmetric, production-grade multi-agent execution pipeline orchestrated via **FastAPI**, **LangGraph**, and **Docker Compose**. This system implements a self-correcting sandboxed compilation context utilizing a local, 4-bit quantized **Llama-3.2 (3B)** model running entirely on CPU/RAM infrastructure with zero third-party API dependencies.

---

## 🗺️ Architectural Topology & Core Flows
[Host Laptop Port:8000]
│
▼ (Ingress Edge)
┌────────────────────────────────────────────────────────┐
│ FastAPI Gateway Service (backend-mesh-service)        │
└──────┬─────────────────────────────────────────────────┘
│
▼ (State Tracking Init via SqliteSaver Room)
┌────────────────────────────────────────────────────────┐
│ LangGraph State Machine Memory Loop Matrix             │
│   ├── Node 1: llm_generator (Context Prompt Injection)│
│   └── Node 2: runtime_compiler (exec() Sandboxing)    │
└──────┬──────────────────┬──────────────────────────────┘
│                  ▲
│ (On Crash Error) │ (Self-Correction Loop Iterations)
└──────────────────┘
│
▼ (Validation Passed - Stateful Persistence Frozen)
⛔ [SAFETY GATE INTERRUPT WALL] -> Pending Admin Clearance Token Signatures
│
▼ (Admin Stamped: "APPROVED")
┌────────────────────────────────────────────────────────┐
│ Node 3: production_commit (Permanent Disk Sync)       │
└────────────────────────────────────────────────────────┘


---

## 📊 Automated System Performance Benchmarks

Engineered via a non-blocking asynchronous profiling harness (`asyncio.gather()`), evaluating token processing metrics on a local **AMD Ryzen 5 / 16GB System RAM** localized hardware layer.

| Scenario Layer | Tokens Generated | Compute Time (s) | Model Throughput (tokens/s) | Round Trip Latency (s) |
| :--- | :---: | :---: | :---: | :---: |
| **Lightweight Arithmetic Task** | 42 | 1.12 | 37.50 | 1.25 |
| **Medium Code Generation Logic** | 118 | 3.24 | 36.41 | 3.42 |
| **Heavy Structural Telemetry Logic** | 245 | 6.81 | 35.97 | 7.02 |

> 💡 **Cost Efficiency Factor:** By migrating computational logic from cloud-hosted inference layers down to localized multi-container edge structures, **inference operational pipeline budgets are compressed by >82%** while retaining complete internal data privacy pipelines.

---

