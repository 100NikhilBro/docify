from typing import Optional, List
import time

from app.retrieval.retrieve import retrieve_per_file_async

from app.memory.memory import (
    add_message_async
)

from app.qa.query_rewriter import (
    rewrite_query_async
)

from app.llm.gemini import (
    stream_answer_async
)

from app.qa.ask import build_context

from app.agent.router import classify_query
from app.agent.handlers import (
    handle_document_summary,
    handle_aggregation,
    handle_comparison,
)
from app.logging_utils import get_logger, log_exception

logger = get_logger("docify.chat")


async def stream_question(
    question: str,
    user_id: str = "default_tenant",
    session_id: Optional[str] = None,
    selected_files: Optional[List[str]] = None
):
    final_answer = ""
    t0 = time.perf_counter()
    logger.info(
        "chat.start user=%s session=%s files=%s q_len=%s",
        user_id,
        session_id,
        selected_files,
        len(question or ""),
    )

    try:
        t = time.perf_counter()
        rewritten_question = await rewrite_query_async(
            question,
            user_id=user_id,
            session_id=session_id
        )
        logger.info(
            "chat.rewrite done in %.2fs changed=%s",
            time.perf_counter() - t,
            rewritten_question != question,
        )

        t = time.perf_counter()
        intent = await classify_query(rewritten_question, selected_files or [])
        logger.info(
            "chat.classify intent=%s files=%s in %.2fs",
            intent,
            selected_files,
            time.perf_counter() - t,
        )

        if intent == "document_summary":
            async for token in handle_document_summary(
                rewritten_question, selected_files or [], user_id
            ):
                final_answer += token
                yield token

        elif intent == "aggregation":
            async for token in handle_aggregation(
                rewritten_question, selected_files or [], user_id
            ):
                final_answer += token
                yield token

        elif intent == "comparison":
            async for token in handle_comparison(
                rewritten_question, selected_files or [], user_id,
                selected_files or []
            ):
                final_answer += token
                yield token

        else:
            t = time.perf_counter()
            chunks = await retrieve_per_file_async(
                rewritten_question,
                user_id=user_id,
                selected_files=selected_files
            )
            logger.info(
                "chat.retrieve chunks=%s in %.2fs",
                len(chunks),
                time.perf_counter() - t,
            )

            context = build_context(chunks)

            image_paths = []
            page_renders = []

            for chunk in chunks:
                images = chunk.get("images", [])
                image_paths.extend(images)
                page_render = chunk.get("page_render")
                if page_render:
                    page_renders.append(page_render)

            image_paths = list(set(image_paths))
            page_renders = list(set(page_renders))

            prompt = f"""
You are a helpful AI assistant answering questions from documents.

Answer in clean markdown format. Use:
- **bold** for key terms
- bullet points for lists
- code blocks for any code/technical content

Only answer from the provided context. If uncertain, say so. 
Exception: If the user asks to solve, answer, or complete questions/tasks/assignments that are listed or found within the document (e.g., a test paper or problem set) and the document itself does not contain the answers/solutions, you should use your own knowledge to solve and answer them, while clearly noting that you are solving/answering the questions from the document using external knowledge.

QUESTION:
{question}

REWRITTEN QUESTION:
{rewritten_question}

CONTEXT:
{context}

Provide a well-formatted answer in markdown. List sources at the end as:
**Sources:** [file.pdf, page X], [file2.pdf, page Y]

If you quote or reference a YouTube video, include the exact timestamp in the format [MM:SS] as a citation, like:
**Sources:** [YouTube - Title (ID).txt, 12:34]
"""

            t = time.perf_counter()
            token_count = 0
            async for token in stream_answer_async(
                prompt,
                image_paths=image_paths + page_renders
            ):
                token_count += 1
                final_answer += token
                yield token
            logger.info(
                "chat.gemini_stream tokens=%s chars=%s in %.2fs",
                token_count,
                len(final_answer),
                time.perf_counter() - t,
            )

        logger.info(
            "chat.ok total=%.2fs answer_chars=%s",
            time.perf_counter() - t0,
            len(final_answer),
        )

    except Exception as e:
        log_exception(logger, "chat.pipeline", e)
        error_msg = (
            "Sorry — I hit an error while retrieving or generating an answer. "
            "Please try again in a moment."
        )
        final_answer = error_msg
        yield error_msg

    try:
        await add_message_async(
            "user",
            question,
            user_id=user_id,
            session_id=session_id
        )
        await add_message_async(
            "assistant",
            final_answer,
            user_id=user_id,
            session_id=session_id
        )
    except Exception as e:
        log_exception(logger, "chat.persist", e)
