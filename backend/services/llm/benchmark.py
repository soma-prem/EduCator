import json
import os
import statistics
import time
from typing import Dict, List

from services.llm.factory import create_provider, get_supported_providers
from services.llm.config import get_env_provider, get_active_provider_name

SAMPLE_PROMPTS = {
    "qa": "Explain the concept of photosynthesis in simple terms.",
    "summary": "Summarize the following text: Plants convert light energy into chemical energy through photosynthesis.",
    "mcq": "Generate a single multiple-choice question about photosynthesis with 4 options.",
}


def measure_provider(provider_name: str, model: str, prompt: str, iterations: int = 2) -> Dict[str, object]:
    provider = create_provider(provider_name=provider_name, model=model)
    results: List[Dict[str, object]] = []
    for index in range(iterations):
        start = time.perf_counter()
        output = provider.generate(prompt, max_output_tokens=200, response_mime_type="text/plain")
        elapsed_ms = (time.perf_counter() - start) * 1000
        prompt_size = len(prompt.encode("utf-8"))
        completion_size = len(str(output or "").encode("utf-8"))
        results.append({
            "latency_ms": elapsed_ms,
            "prompt_size_bytes": prompt_size,
            "completion_size_bytes": completion_size,
            "text": str(output or ""),
        })
    average_latency = statistics.mean([item["latency_ms"] for item in results])
    total_prompt = sum(item["prompt_size_bytes"] for item in results)
    total_completion = sum(item["completion_size_bytes"] for item in results)
    return {
        "provider": provider_name,
        "model": model,
        "prompt": prompt,
        "average_latency_ms": average_latency,
        "prompt_size_bytes": total_prompt / iterations,
        "completion_size_bytes": total_completion / iterations,
        "responses": [item["text"] for item in results],
    }


def benchmark_all_models(samples: Dict[str, str], iterations: int = 2) -> Dict[str, object]:
    active = get_active_provider_name()
    supported = get_supported_providers()
    selected_provider = get_env_provider("LLM_PROVIDER") or active
    report: Dict[str, object] = {
        "selected_provider": selected_provider,
        "active_provider": active,
        "supported_providers": supported,
        "benchmarks": [],
    }
    for provider_name in supported:
        if provider_name != selected_provider:
            continue
        model = os.getenv(f"{provider_name.upper()}_MODEL") or os.getenv("LLM_MODEL", "")
        if not model:
            continue
        for sample_name, prompt in samples.items():
            try:
                measurement = measure_provider(provider_name, model, prompt, iterations=iterations)
                measurement["sample"] = sample_name
                report["benchmarks"].append(measurement)
            except Exception as exc:
                report["benchmarks"].append(
                    {
                        "provider": provider_name,
                        "model": model,
                        "sample": sample_name,
                        "error": str(exc),
                    }
                )
    return report


if __name__ == "__main__":
    iterations = int(os.getenv("LLM_BENCH_ITERATIONS", "2"))
    report = benchmark_all_models(SAMPLE_PROMPTS, iterations=iterations)
    print(json.dumps(report, indent=2, ensure_ascii=False))
