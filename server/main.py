"""
EXPERIMENTAL CLI entrypoint for Docify.

Production Q&A runs through FastAPI `POST /chat` → `stream_question`.
This REPL uses the experimental planner + evidence gatherer path.
"""

from app.agent.agentic_qa import ask_agentic_question


def main():

    print("\nDocify CLI (experimental agentic path)")
    print("Production chat uses HTTP /chat — this REPL is for local research.\n")

    while True:

        question = input("\nAsk Question: ")

        if question.lower() in ["exit", "quit"]:
            break

        result = ask_agentic_question(question)

        print("\n====================\n")

        print("\n========== SEARCH QUERIES ==========\n")

        for q in result["queries"]:

            print("-", q)
        print(
            f"\nRewritten Query: "
            f"{result['rewritten_question']}"
        )
        print(result["answer"])

        print("\n\n========== SOURCES ==========\n")

        for chunk in result["retrieved_chunks"]:

            # Handle None values in scores
            vector = chunk.get("vector_score")
            if vector is None:
                vector = chunk.get("score", 0)
            if vector is None:
                vector = 0

            bm25 = chunk.get("bm25_score")
            if bm25 is None:
                bm25 = 0

            rerank = chunk.get("rerank_score")
            if rerank is None:
                rerank = 0

            print(
                f"""
        CHUNK: {chunk.get("chunk_id", chunk.get("id", "N/A"))}

        FILE: {chunk.get("source_file", "N/A")}

        PAGE: {chunk.get("page", "N/A")}

        VECTOR: {vector:.4f}

        BM25: {bm25:.4f}

        RERANK: {rerank:.4f}

        PREVIEW:
        {chunk.get("preview", chunk.get("text", ""))[:300]}

        ----------------------------
        """
            )

        print(
            "\n(Experimental CLI path — not used by production HTTP /chat.)"
        )

        print("\n====================\n")


if __name__ == "__main__":
    main()
