# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-11T13:40:14`
- Ended at: `2026-04-11T13:40:27`
- Metadata:
  - `query`: `这张图显示的是“孕前肥胖（BMI≥28.0）妇女孕期增重适宜值范围”。如果一位孕前 BMI≥28.0 的女性在孕 14 周时累计增重约 1–2 kg，而在孕晚期（约孕 38–42 周）时累计增重约 8–9 kg，那么这张图所表达的孕期增重趋势是怎样的？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4697 | 314 | 5011 | 0 |
| embedding | 13 | 172 | 0 | 172 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 16 | 4869 | 314 | 5183 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4697 | 314 | 5011 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 13 | 172 | 0 | 172 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-11T13:40:14` `embedding` / `text-embedding-v3` input=92 output=0 total=92 source=`ragent.llm.openai.openai_embed`
2. `2026-04-11T13:40:17` `chat` / `qwen3-32b` input=968 output=70 total=1038 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-11T13:40:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-11T13:40:17` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
5. `2026-04-11T13:40:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
6. `2026-04-11T13:40:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-11T13:40:17` `embedding` / `text-embedding-v3` input=8 output=0 total=8 source=`ragent.llm.openai.openai_embed`
8. `2026-04-11T13:40:17` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
9. `2026-04-11T13:40:17` `embedding` / `text-embedding-v3` input=29 output=0 total=29 source=`ragent.llm.openai.openai_embed`
10. `2026-04-11T13:40:17` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
11. `2026-04-11T13:40:17` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
12. `2026-04-11T13:40:17` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
13. `2026-04-11T13:40:17` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-11T13:40:17` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
15. `2026-04-11T13:40:18` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
16. `2026-04-11T13:40:27` `chat` / `qwen3-32b` input=3729 output=244 total=3973 source=`ragent.llm.openai.openai_complete_if_cache`
