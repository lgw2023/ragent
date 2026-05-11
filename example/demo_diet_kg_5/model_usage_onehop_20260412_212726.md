# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:27:10`
- Ended at: `2026-04-12T21:27:26`
- Metadata:
  - `query`: `相比单纯增加食量，先做到哪一种更能帮助成年人维持健康体重：每天坚持身体活动，还是把饮食吃得更多样、更丰富？请列出理由。`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4023 | 520 | 4543 | 0 |
| embedding | 10 | 83 | 0 | 83 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 13 | 4106 | 520 | 4626 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4023 | 520 | 4543 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 10 | 83 | 0 | 83 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:27:10` `embedding` / `text-embedding-v3` input=37 output=0 total=37 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:27:12` `chat` / `qwen3-32b` input=908 output=49 total=957 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:27:12` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:27:12` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:27:12` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:27:12` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:27:12` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:27:12` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:27:12` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:27:12` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:27:12` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:27:13` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
13. `2026-04-12T21:27:26` `chat` / `qwen3-32b` input=3115 output=471 total=3586 source=`ragent.llm.openai.openai_complete_if_cache`
