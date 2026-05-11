# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-20T17:16:31`
- Ended at: `2026-04-20T17:16:57`
- Metadata:
  - `query`: `我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3932 | 450 | 4382 | 0 |
| embedding | 12 | 106 | 0 | 106 | 0 |
| rerank | 2 | 0 | 0 | 0 | 2 |
| image | 1 | 0 | 0 | 0 | 1 |
| total | 17 | 4038 | 450 | 4488 | 3 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3932 | 450 | 4382 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 106 | 0 | 106 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 2 | 0 | 0 | 0 | 2 |

### image

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-vl-flash | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-20T17:16:31` `chat` / `qwen3-32b` input=40 output=3 total=43 source=`ragent.llm.openai.openai_complete_if_cache`
2. `2026-04-20T17:16:32` `embedding` / `text-embedding-v3` input=14 output=0 total=14 source=`ragent.llm.openai.openai_embed`
3. `2026-04-20T17:16:32` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
4. `2026-04-20T17:16:33` `image` / `qwen3-vl-flash` input=0 output=0 total=0 source=`integrations._image_text_ping_sync`
5. `2026-04-20T17:16:37` `embedding` / `text-embedding-v3` input=38 output=0 total=38 source=`ragent.llm.openai.openai_embed`
6. `2026-04-20T17:16:37` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-20T17:16:38` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-20T17:16:38` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-20T17:16:38` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
10. `2026-04-20T17:16:38` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-20T17:16:38` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-20T17:16:39` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
13. `2026-04-20T17:16:39` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
14. `2026-04-20T17:16:39` `embedding` / `text-embedding-v3` input=12 output=0 total=12 source=`ragent.llm.openai.openai_embed`
15. `2026-04-20T17:16:39` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
16. `2026-04-20T17:16:40` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
17. `2026-04-20T17:16:56` `chat` / `qwen3-32b` input=3892 output=447 total=4339 source=`ragent.llm.openai.openai_complete_if_cache`
