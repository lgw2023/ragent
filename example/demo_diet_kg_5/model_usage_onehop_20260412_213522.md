# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:35:12`
- Ended at: `2026-04-12T21:35:22`
- Metadata:
  - `query`: `我每天吃的肉类不算多，但最近想调整饮食，让身体更好一些。按每100克食物里蛋白质含量来看，下面这些常见食物里，哪一种蛋白质含量最高：猪肉（代表值）、鸡（代表值）、鲤鱼、牛肉（代表值）、鸭（代表值）、青鱼？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4128 | 269 | 4397 | 0 |
| embedding | 13 | 133 | 0 | 133 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 16 | 4261 | 269 | 4530 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4128 | 269 | 4397 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 13 | 133 | 0 | 133 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:35:12` `embedding` / `text-embedding-v3` input=73 output=0 total=73 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:35:14` `chat` / `qwen3-32b` input=939 output=51 total=990 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:35:14` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:35:15` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:35:15` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:35:15` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:35:15` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:35:15` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:35:15` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:35:15` `embedding` / `text-embedding-v3` input=26 output=0 total=26 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:35:15` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:35:15` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:35:15` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:35:15` `embedding` / `text-embedding-v3` input=12 output=0 total=12 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T21:35:16` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
16. `2026-04-12T21:35:21` `chat` / `qwen3-32b` input=3189 output=218 total=3407 source=`ragent.llm.openai.openai_complete_if_cache`
