# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T22:52:05`
- Ended at: `2026-04-11T22:52:29`
- Metadata:
  - `query`: `我今年17岁，身高170cm，体重160斤，平时几乎每天要打排球2到3小时，而且每周还会安排几次力量训练。想把体重降到130斤的话，日常饮食更适合怎么安排？如果想选豆浆，应该选哪种外观和质地的？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3833 | 642 | 4475 | 0 |
| embedding | 12 | 114 | 0 | 114 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 3947 | 642 | 4589 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3833 | 642 | 4475 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 114 | 0 | 114 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T22:52:05` `embedding` / `text-embedding-v3` input=64 output=0 total=64 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T22:52:07` `chat` / `qwen3-32b` input=938 output=49 total=987 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T22:52:07` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T22:52:07` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T22:52:07` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T22:52:07` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T22:52:07` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T22:52:07` `embedding` / `text-embedding-v3` input=16 output=0 total=16 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T22:52:08` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T22:52:08` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T22:52:08` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-11T22:52:08` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-11T22:52:08` `embedding` / `text-embedding-v3` input=16 output=0 total=16 source=`ragent.llm.openai.openai_embed`
14. `2026-04-11T22:52:08` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-11T22:52:28` `chat` / `qwen3-32b` input=2895 output=593 total=3488 source=`ragent.llm.openai.openai_complete_if_cache`
