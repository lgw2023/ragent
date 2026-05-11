# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:46:09`
- Ended at: `2026-04-12T21:46:17`
- Metadata:
  - `query`: `如果我想按减重又兼顾高血压控制来安排饮食，在这些西南地区的示例里，哪一种一日食谱的总能量最低，而且它一天的油和盐用量分别是多少？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4513 | 169 | 4682 | 0 |
| embedding | 12 | 104 | 0 | 104 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 15 | 4617 | 169 | 4786 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4513 | 169 | 4682 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 12 | 104 | 0 | 104 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:46:09` `embedding` / `text-embedding-v3` input=46 output=0 total=46 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:46:11` `chat` / `qwen3-32b` input=911 output=50 total=961 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:46:11` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:46:11` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:46:11` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:46:11` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:46:11` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:46:11` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:46:11` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:46:12` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:46:12` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:46:12` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:46:12` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:46:12` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
15. `2026-04-12T21:46:17` `chat` / `qwen3-32b` input=3602 output=119 total=3721 source=`ragent.llm.openai.openai_complete_if_cache`
