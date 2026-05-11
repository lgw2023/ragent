# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:52:13`
- Ended at: `2026-04-12T21:52:28`
- Metadata:
  - `query`: `如果我想按高血压和减重都更合适的方式来吃，成人肥胖食养里华北地区那个总能量约1400千卡的春季食谱，三餐加起来全天植物油和盐分别是多少？另外，高血压的生活要点里，除了少盐，最核心的其他四个方向是什么？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 5255 | 319 | 5574 | 0 |
| embedding | 16 | 164 | 0 | 164 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 19 | 5419 | 319 | 5738 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 5255 | 319 | 5574 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 16 | 164 | 0 | 164 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:52:13` `embedding` / `text-embedding-v3` input=71 output=0 total=71 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:52:18` `chat` / `qwen3-32b` input=936 output=78 total=1014 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:52:19` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:52:19` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:52:19` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:52:19` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:52:19` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:52:19` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:52:19` `embedding` / `text-embedding-v3` input=31 output=0 total=31 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:52:19` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:52:19` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:52:19` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:52:19` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:52:19` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T21:52:19` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T21:52:19` `embedding` / `text-embedding-v3` input=29 output=0 total=29 source=`ragent.llm.openai.openai_embed`
17. `2026-04-12T21:52:19` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
18. `2026-04-12T21:52:20` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
19. `2026-04-12T21:52:28` `chat` / `qwen3-32b` input=4319 output=241 total=4560 source=`ragent.llm.openai.openai_complete_if_cache`
