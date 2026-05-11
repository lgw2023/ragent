# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T13:38:18`
- Ended at: `2026-04-11T13:38:25`
- Metadata:
  - `query`: `按图中“小份量，量化有数”的标准，鸡翅每个可食重50克。那如果我只吃2个鸡翅，一共是多少克可食重？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3747 | 129 | 3876 | 0 |
| embedding | 9 | 83 | 0 | 83 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 12 | 3830 | 129 | 3959 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3747 | 129 | 3876 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 9 | 83 | 0 | 83 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T13:38:19` `embedding` / `text-embedding-v3` input=43 output=0 total=43 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T13:38:20` `chat` / `qwen3-32b` input=913 output=41 total=954 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T13:38:20` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T13:38:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T13:38:21` `embedding` / `text-embedding-v3` input=11 output=0 total=11 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T13:38:21` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T13:38:21` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T13:38:21` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T13:38:21` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T13:38:21` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T13:38:21` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
12. `2026-04-11T13:38:25` `chat` / `qwen3-32b` input=2834 output=88 total=2922 source=`ragent.llm.openai.openai_complete_if_cache`
