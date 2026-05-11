# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T03:39:03`
- Ended at: `2026-04-07T03:39:16`
- Metadata:
  - `query`: `下午多吃了 150 千卡点心，先快走 30 分钟，再爬楼多久能补回来？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 3 | 6087 | 1043 | 7130 | 0 |
| embedding | 4 | 80 | 0 | 80 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 8 | 6167 | 1043 | 7210 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3.5-flash | 3 | 6087 | 1043 | 7130 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 80 | 0 | 80 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T03:39:03` `embedding` / `text-embedding-v3` input=25 output=0 total=25 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T03:39:04` `chat` / `qwen3.5-flash` input=487 output=54 total=541 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-07T03:39:04` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T03:39:05` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T03:39:05` `embedding` / `text-embedding-v3` input=25 output=0 total=25 source=`ragent.llm.openai.openai_embed`
6. `2026-04-07T03:39:06` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
7. `2026-04-07T03:39:11` `chat` / `qwen3.5-flash` input=4603 output=551 total=5154 source=`ragent.llm.openai.openai_complete_if_cache`
8. `2026-04-07T03:39:15` `chat` / `qwen3.5-flash` input=997 output=438 total=1435 source=`ragent.llm.openai.openai_complete_if_cache`
