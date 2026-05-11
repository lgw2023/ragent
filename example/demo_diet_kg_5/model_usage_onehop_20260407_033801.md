# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T03:37:46`
- Ended at: `2026-04-07T03:38:01`
- Metadata:
  - `query`: `我有点胖，现在90kg， 想 6 个月减到 75kg，会不会太猛？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 3 | 7296 | 1426 | 8722 | 0 |
| embedding | 4 | 68 | 0 | 68 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 8 | 7364 | 1426 | 8790 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3.5-flash | 3 | 7296 | 1426 | 8722 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 4 | 68 | 0 | 68 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T03:37:47` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T03:37:47` `chat` / `qwen3.5-flash` input=485 output=53 total=538 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-07T03:37:48` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T03:37:48` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T03:37:48` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
6. `2026-04-07T03:37:49` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
7. `2026-04-07T03:37:56` `chat` / `qwen3.5-flash` input=5648 output=717 total=6365 source=`ragent.llm.openai.openai_complete_if_cache`
8. `2026-04-07T03:38:01` `chat` / `qwen3.5-flash` input=1163 output=656 total=1819 source=`ragent.llm.openai.openai_complete_if_cache`
