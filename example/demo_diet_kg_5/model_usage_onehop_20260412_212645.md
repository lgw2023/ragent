# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:26:32`
- Ended at: `2026-04-12T21:26:45`
- Metadata:
  - `query`: `我想安排一顿更清淡、蔬菜多一些的晚餐，最好能同时有蛋白质和水果。能不能给我一个由3道菜组成的晚餐搭配，并明确每道菜分别是什么？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4978 | 430 | 5408 | 0 |
| embedding | 13 | 101 | 0 | 101 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 16 | 5079 | 430 | 5509 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4978 | 430 | 5408 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 13 | 101 | 0 | 101 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:26:32` `embedding` / `text-embedding-v3` input=43 output=0 total=43 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:26:33` `chat` / `qwen3-32b` input=910 output=51 total=961 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:26:34` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:26:34` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:26:34` `embedding` / `text-embedding-v3` input=15 output=0 total=15 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:26:34` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:26:34` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:26:34` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:26:34` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:26:34` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:26:35` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:26:35` `embedding` / `text-embedding-v3` input=22 output=0 total=22 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:26:35` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:26:35` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T21:26:36` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
16. `2026-04-12T21:26:45` `chat` / `qwen3-32b` input=4068 output=379 total=4447 source=`ragent.llm.openai.openai_complete_if_cache`
