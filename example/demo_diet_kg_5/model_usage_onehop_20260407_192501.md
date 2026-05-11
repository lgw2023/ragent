# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T19:24:17`
- Ended at: `2026-04-07T19:25:01`
- Metadata:
  - `query`: `我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先 中速步行30 分钟，再爬楼多久能补回来？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 1 | 3770 | 264 | 4034 | 0 |
| embedding | 11 | 92 | 0 | 92 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 13 | 3862 | 264 | 4126 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 1 | 3770 | 264 | 4034 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 92 | 0 | 92 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T19:24:22` `embedding` / `text-embedding-v3` input=38 output=0 total=38 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T19:24:23` `embedding` / `text-embedding-v3` input=21 output=0 total=21 source=`ragent.llm.openai.openai_embed`
3. `2026-04-07T19:24:24` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T19:24:25` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T19:24:25` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-07T19:24:26` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-07T19:24:26` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-07T19:24:29` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-07T19:24:29` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-07T19:24:30` `embedding` / `text-embedding-v3` input=12 output=0 total=12 source=`ragent.llm.openai.openai_embed`
11. `2026-04-07T19:24:46` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-07T19:24:51` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
13. `2026-04-07T19:25:01` `chat` / `qwen3-32b` input=3770 output=264 total=4034 source=`ragent.llm.openai.openai_complete_if_cache`
