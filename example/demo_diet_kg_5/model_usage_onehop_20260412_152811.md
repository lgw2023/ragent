# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T15:27:57`
- Ended at: `2026-04-12T15:28:11`
- Metadata:
  - `query`: `如果想控制体重，晚餐只吃水果和蔬菜，或者干脆不吃晚饭，这样做有没有助于减肥？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4837 | 437 | 5274 | 0 |
| embedding | 11 | 71 | 0 | 71 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 14 | 4908 | 437 | 5345 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4837 | 437 | 5274 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 71 | 0 | 71 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T15:27:57` `embedding` / `text-embedding-v3` input=25 output=0 total=25 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T15:27:59` `chat` / `qwen3-32b` input=893 output=43 total=936 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T15:27:59` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T15:27:59` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T15:27:59` `embedding` / `text-embedding-v3` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T15:27:59` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T15:27:59` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T15:28:00` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T15:28:00` `embedding` / `text-embedding-v3` input=16 output=0 total=16 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T15:28:00` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T15:28:00` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T15:28:00` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T15:28:00` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
14. `2026-04-12T15:28:11` `chat` / `qwen3-32b` input=3944 output=394 total=4338 source=`ragent.llm.openai.openai_complete_if_cache`
