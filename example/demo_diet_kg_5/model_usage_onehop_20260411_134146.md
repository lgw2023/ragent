# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T13:41:13`
- Ended at: `2026-04-11T13:41:46`
- Metadata:
  - `query`: `我是一名成年男性，身高1.75米，体重88公斤，想通过控制饮食减重。按权威膳食指南，这种体重属于什么范围？如果想减到“健康体重”上限，大约需要减到多少公斤；同时，减重时每天把总能量摄入降低多少，比较符合指南建议且一般还能兼顾健康？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4118 | 599 | 4717 | 0 |
| embedding | 13 | 145 | 0 | 145 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 16 | 4263 | 599 | 4862 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4118 | 599 | 4717 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 13 | 145 | 0 | 145 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T13:41:14` `embedding` / `text-embedding-v3` input=75 output=0 total=75 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T13:41:16` `chat` / `qwen3-32b` input=947 output=58 total=1005 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T13:41:17` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T13:41:17` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T13:41:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T13:41:17` `embedding` / `text-embedding-v3` input=20 output=0 total=20 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T13:41:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T13:41:17` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T13:41:17` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T13:41:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T13:41:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-11T13:41:17` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-11T13:41:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-11T13:41:17` `embedding` / `text-embedding-v3` input=23 output=0 total=23 source=`ragent.llm.openai.openai_embed`
15. `2026-04-11T13:41:18` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
16. `2026-04-11T13:41:45` `chat` / `qwen3-32b` input=3171 output=541 total=3712 source=`ragent.llm.openai.openai_complete_if_cache`
