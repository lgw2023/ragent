# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-09T12:40:09`
- Ended at: `2026-04-09T12:40:15`
- Metadata:
  - `query`: `根据本轮资料中可直接辨识到的英文大写字母，两个图片里一共出现了多少个字母字符？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4029 | 110 | 4139 | 0 |
| embedding | 9 | 67 | 0 | 67 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 4096 | 110 | 4206 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4029 | 110 | 4139 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 67 | 0 | 67 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-09T12:40:09` `embedding` / `text-embedding-v3` input=25 output=0 total=25 source=`ragent.llm.openai.openai_embed`
2. `2026-04-09T12:40:11` `chat` / `qwen3-32b` input=897 output=41 total=938 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-09T12:40:11` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
4. `2026-04-09T12:40:11` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
5. `2026-04-09T12:40:11` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-09T12:40:11` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-09T12:40:11` `embedding` / `text-embedding-v3` input=12 output=0 total=12 source=`ragent.llm.openai.openai_embed`
8. `2026-04-09T12:40:11` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-09T12:40:11` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-09T12:40:11` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-09T12:40:12` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-09T12:40:15` `chat` / `qwen3-32b` input=3132 output=69 total=3201 source=`ragent.llm.openai.openai_complete_if_cache`
