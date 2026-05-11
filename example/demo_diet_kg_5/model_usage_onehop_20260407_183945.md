# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-07T18:39:17`
- Ended at: `2026-04-07T18:39:45`
- Metadata:
  - `query`: `我已经是个成年男人了，但是下午多喝了一听含糖饮料(330ml)，我先快步走30 分钟，再爬楼多久能补回来？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4887 | 473 | 5360 | 0 |
| embedding | 8 | 56 | 0 | 56 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 11 | 4943 | 473 | 5416 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4887 | 473 | 5360 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 8 | 56 | 0 | 56 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-07T18:39:19` `embedding` / `text-embedding-v3` input=37 output=0 total=37 source=`ragent.llm.openai.openai_embed`
2. `2026-04-07T18:39:22` `chat` / `qwen3-32b` input=912 output=46 total=958 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-07T18:39:24` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T18:39:24` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T18:39:25` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-07T18:39:26` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-07T18:39:28` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-07T18:39:28` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
9. `2026-04-07T18:39:29` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-07T18:39:31` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
11. `2026-04-07T18:39:44` `chat` / `qwen3-32b` input=3975 output=427 total=4402 source=`ragent.llm.openai.openai_complete_if_cache`
