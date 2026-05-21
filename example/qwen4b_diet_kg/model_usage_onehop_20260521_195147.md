# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-05-21T19:50:36`
- Ended at: `2026-05-21T19:51:47`
- Metadata:
  - `query`: `我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`
  - `enable_rerank`: `None`
  - `response_type`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 3 | 4682 | 1998 | 6680 | 0 |
| embedding | 13 | 126 | 0 | 126 | 0 |
| rerank | 2 | 0 | 0 | 0 | 2 |
| image | 1 | 0 | 0 | 0 | 1 |
| total | 19 | 4808 | 1998 | 6806 | 3 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| deepseek-v4-flash | 3 | 4682 | 1998 | 6680 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen/Qwen3-Embedding-4B | 13 | 126 | 0 | 126 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 2 | 0 | 0 | 0 | 2 |

### image

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-vl-flash | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-05-21T19:50:38` `chat` / `deepseek-v4-flash` input=25 output=41 total=66 source=`ragent.llm.openai.openai_complete_if_cache`
2. `2026-05-21T19:50:43` `embedding` / `Qwen/Qwen3-Embedding-4B` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
3. `2026-05-21T19:50:43` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
4. `2026-05-21T19:50:44` `image` / `qwen3-vl-flash` input=0 output=0 total=0 source=`ragent.inference_runtime._image_text_ping_sync`
5. `2026-05-21T19:51:04` `embedding` / `Qwen/Qwen3-Embedding-4B` input=41 output=0 total=41 source=`ragent.llm.openai.openai_embed`
6. `2026-05-21T19:51:09` `chat` / `deepseek-v4-flash` input=913 output=300 total=1213 source=`ragent.llm.openai.openai_complete_if_cache`
7. `2026-05-21T19:51:14` `embedding` / `Qwen/Qwen3-Embedding-4B` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-05-21T19:51:15` `embedding` / `Qwen/Qwen3-Embedding-4B` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-05-21T19:51:15` `embedding` / `Qwen/Qwen3-Embedding-4B` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-05-21T19:51:15` `embedding` / `Qwen/Qwen3-Embedding-4B` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-05-21T19:51:15` `embedding` / `Qwen/Qwen3-Embedding-4B` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
12. `2026-05-21T19:51:17` `embedding` / `Qwen/Qwen3-Embedding-4B` input=22 output=0 total=22 source=`ragent.llm.openai.openai_embed`
13. `2026-05-21T19:51:19` `embedding` / `Qwen/Qwen3-Embedding-4B` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-05-21T19:51:20` `embedding` / `Qwen/Qwen3-Embedding-4B` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
15. `2026-05-21T19:51:20` `embedding` / `Qwen/Qwen3-Embedding-4B` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
16. `2026-05-21T19:51:20` `embedding` / `Qwen/Qwen3-Embedding-4B` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
17. `2026-05-21T19:51:20` `embedding` / `Qwen/Qwen3-Embedding-4B` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
18. `2026-05-21T19:51:25` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
19. `2026-05-21T19:51:44` `chat` / `deepseek-v4-flash` input=3744 output=1657 total=5401 source=`ragent.llm.openai.openai_complete_if_cache`
