# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-09T12:41:51`
- Ended at: `2026-04-09T12:42:08`
- Metadata:
  - `query`: `如果你想用这组资料来判断一顿饭是否既符合《中国居民膳食指南（2022）》强调的均衡搭配、又能从包装标准角度进一步核实其成分安全性与效果确认，这个 bundle 里哪一份资料能直接帮助你看食物类别与搭配比例，哪一份资料不能直接提供具体成分或检验结果、因此不足以单独完成安全性确认？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3458 | 449 | 3907 | 0 |
| embedding | 14 | 153 | 0 | 153 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 17 | 3611 | 449 | 4060 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3458 | 449 | 3907 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 14 | 153 | 0 | 153 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-09T12:41:52` `embedding` / `text-embedding-v3` input=81 output=0 total=81 source=`ragent.llm.openai.openai_embed`
2. `2026-04-09T12:41:54` `chat` / `qwen3-32b` input=950 output=65 total=1015 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-09T12:41:55` `embedding` / `text-embedding-v3` input=6 output=0 total=6 source=`ragent.llm.openai.openai_embed`
4. `2026-04-09T12:41:55` `embedding` / `text-embedding-v3` input=27 output=0 total=27 source=`ragent.llm.openai.openai_embed`
5. `2026-04-09T12:41:55` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-09T12:41:55` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-09T12:41:55` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-09T12:41:55` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
9. `2026-04-09T12:41:55` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
10. `2026-04-09T12:41:55` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-09T12:41:55` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-09T12:41:55` `embedding` / `text-embedding-v3` input=18 output=0 total=18 source=`ragent.llm.openai.openai_embed`
13. `2026-04-09T12:41:55` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
14. `2026-04-09T12:41:56` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
15. `2026-04-09T12:41:56` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
16. `2026-04-09T12:41:56` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
17. `2026-04-09T12:42:08` `chat` / `qwen3-32b` input=2508 output=384 total=2892 source=`ragent.llm.openai.openai_complete_if_cache`
