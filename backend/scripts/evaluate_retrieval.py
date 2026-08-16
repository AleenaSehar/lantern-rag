import argparse
import asyncio
import json
from pathlib import Path

import httpx


async def evaluate(base_url: str) -> tuple[float, float]:
    fixture_path = Path(__file__).parents[1] / "evaluation" / "retrieval_cases.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    document_ids: list[str] = []

    async with httpx.AsyncClient(base_url=base_url, timeout=120) as client:
        for document in fixture["documents"]:
            response = await client.post(
                "/documents",
                files={
                    "file": (
                        document["filename"],
                        document["text"].encode(),
                        "text/plain",
                    )
                },
            )
            response.raise_for_status()
            document_ids.append(response.json()["id"])

        reciprocal_ranks: list[float] = []
        hits = 0
        for case in fixture["cases"]:
            response = await client.post(
                "/retrieval/search",
                json={"query": case["query"], "document_ids": document_ids, "top_k": 5},
            )
            response.raise_for_status()
            texts = [result["text"] for result in response.json()["results"]]
            rank = next(
                (
                    index
                    for index, text in enumerate(texts, start=1)
                    if case["expected"].lower() in text.lower()
                ),
                None,
            )
            if rank is not None:
                hits += 1
                reciprocal_ranks.append(1 / rank)
            else:
                reciprocal_ranks.append(0)
            print(f"rank={rank or '-'} query={case['query']}")

    recall_at_five = hits / len(fixture["cases"])
    mean_reciprocal_rank = sum(reciprocal_ranks) / len(reciprocal_ranks)
    return recall_at_five, mean_reciprocal_rank


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the local retrieval baseline")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--min-recall", type=float, default=1.0)
    parser.add_argument("--min-mrr", type=float, default=0.8)
    args = parser.parse_args()
    recall, mrr = await evaluate(args.base_url)
    print(f"Recall@5: {recall:.3f}")
    print(f"MRR:      {mrr:.3f}")
    if recall < args.min_recall or mrr < args.min_mrr:
        raise SystemExit("Retrieval quality fell below the configured baseline")


if __name__ == "__main__":
    asyncio.run(main())
