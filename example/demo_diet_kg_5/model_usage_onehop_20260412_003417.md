# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T00:34:09`
- Ended at: `2026-04-12T00:34:17`
- Metadata:
  - `query`: `我在做大米垩白度的重复测定时，想确认结果是否算合格：如果同一样品两次独立测试的平均垩白度是 4.8%，这两次结果之间允许的最大绝对差是多少？如果平均垩白度是 5.2%，允许的最大绝对差又是多少？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3690 | 253 | 3943 | 0 |
| embedding | 11 | 121 | 0 | 121 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 14 | 3811 | 253 | 4064 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3690 | 253 | 3943 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 121 | 0 | 121 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T00:34:09` `embedding` / `text-embedding-v3` input=63 output=0 total=63 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T00:34:11` `chat` / `qwen3-32b` input=936 output=52 total=988 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T00:34:11` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T00:34:11` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T00:34:11` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T00:34:11` `embedding` / `text-embedding-v3` input=16 output=0 total=16 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T00:34:11` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T00:34:12` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T00:34:12` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T00:34:12` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T00:34:12` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T00:34:12` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T00:34:12` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
14. `2026-04-12T00:34:17` `chat` / `qwen3-32b` input=2754 output=201 total=2955 source=`ragent.llm.openai.openai_complete_if_cache`
