# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T13:40:38`
- Ended at: `2026-04-11T13:41:02`
- Metadata:
  - `query`: `如果我需要控制血压、想把每天的食盐量压到3g左右，并希望饮食总能量大约在1600～2000kcal之间，那么下面哪份冬季食谱最符合这两个要求：冬季食谱1、冬季食谱2还是冬季食谱3？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 5071 | 558 | 5629 | 0 |
| embedding | 12 | 130 | 0 | 130 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 5201 | 558 | 5759 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 5071 | 558 | 5629 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 130 | 0 | 130 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T13:40:38` `embedding` / `text-embedding-v3` input=60 output=0 total=60 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T13:40:40` `chat` / `qwen3-32b` input=935 output=57 total=992 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T13:40:40` `embedding` / `text-embedding-v3` input=25 output=0 total=25 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T13:40:40` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T13:40:40` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T13:40:40` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T13:40:40` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T13:40:40` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T13:40:41` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T13:40:41` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T13:40:41` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
12. `2026-04-11T13:40:41` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-11T13:40:41` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
14. `2026-04-11T13:40:41` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-11T13:41:01` `chat` / `qwen3-32b` input=4136 output=501 total=4637 source=`ragent.llm.openai.openai_complete_if_cache`
