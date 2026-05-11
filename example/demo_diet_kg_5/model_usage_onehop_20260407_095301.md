# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T09:52:38`
- Ended at: `2026-04-07T09:53:01`
- Metadata:
  - `query`: `下午多吃了 150 千卡点心，先快走 30 分钟，再爬楼多久能补回来？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 5475 | 578 | 6053 | 0 |
| embedding | 4 | 80 | 0 | 80 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 7 | 5555 | 578 | 6133 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 5475 | 578 | 6053 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 80 | 0 | 80 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T09:52:38` `embedding` / `text-embedding-v3` input=25 output=0 total=25 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T09:52:39` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
3. `2026-04-07T09:52:39` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T09:52:39` `embedding` / `text-embedding-v3` input=25 output=0 total=25 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T09:52:40` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
6. `2026-04-07T09:52:51` `chat` / `qwen3-32b` input=4728 output=313 total=5041 source=`ragent.llm.openai.openai_complete_if_cache`
7. `2026-04-07T09:53:01` `chat` / `qwen3-32b` input=747 output=265 total=1012 source=`ragent.llm.openai.openai_complete_if_cache`
