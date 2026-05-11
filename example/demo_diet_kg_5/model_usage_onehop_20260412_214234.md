# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:42:15`
- Ended at: `2026-04-12T21:42:34`
- Metadata:
  - `query`: `如果一个人空腹血糖测到102 mg/dL，想通过更合理的饮食来预防慢性病，应该更接近哪种膳食方式：高纤维、低饱和脂肪的搭配，还是长期高脂高糖的吃法？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3949 | 666 | 4615 | 0 |
| embedding | 11 | 111 | 0 | 111 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 14 | 4060 | 666 | 4726 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3949 | 666 | 4615 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 11 | 111 | 0 | 111 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:42:15` `embedding` / `text-embedding-v3` input=51 output=0 total=51 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:42:17` `chat` / `qwen3-32b` input=920 output=51 total=971 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:42:17` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:42:17` `embedding` / `text-embedding-v3` input=18 output=0 total=18 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:42:17` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:42:17` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:42:17` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:42:17` `embedding` / `text-embedding-v3` input=18 output=0 total=18 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:42:18` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:42:18` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:42:18` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:42:18` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:42:18` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
14. `2026-04-12T21:42:34` `chat` / `qwen3-32b` input=3029 output=615 total=3644 source=`ragent.llm.openai.openai_complete_if_cache`
