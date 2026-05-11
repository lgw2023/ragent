# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T15:29:24`
- Ended at: `2026-04-12T15:29:36`
- Metadata:
  - `query`: `家里平时做饭，怎样安排分量才更容易吃得刚好、又尽量不浪费？如果是三口之家，一顿饭大概做几道菜比较合适，单盘菜的分量大致多少？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3382 | 381 | 3763 | 0 |
| embedding | 11 | 104 | 0 | 104 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 14 | 3486 | 381 | 3867 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3382 | 381 | 3763 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 104 | 0 | 104 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T15:29:24` `embedding` / `text-embedding-v3` input=46 output=0 total=46 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T15:29:26` `chat` / `qwen3-32b` input=914 output=54 total=968 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T15:29:27` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T15:29:27` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T15:29:27` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T15:29:27` `embedding` / `text-embedding-v3` input=18 output=0 total=18 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T15:29:27` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T15:29:27` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T15:29:27` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T15:29:27` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T15:29:27` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T15:29:27` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T15:29:28` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
14. `2026-04-12T15:29:36` `chat` / `qwen3-32b` input=2468 output=327 total=2795 source=`ragent.llm.openai.openai_complete_if_cache`
