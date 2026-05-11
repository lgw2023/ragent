# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T21:30:56`
- Ended at: `2026-04-12T21:31:21`
- Metadata:
  - `query`: `我今年38岁，男，身高170厘米、体重71公斤，平时也比较久坐。现在如果我想靠运动来减肥并改善健康，应该怎么安排更合适：像每周保持150到300分钟中等强度有氧运动、每周2到3天做抗阻训练、尽量每周通过运动多消耗一些能量，同时把日常饮食尽量做得更均衡，多吃些谷类和杂豆，这样对减重和身体状态分别会有什么帮助？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4799 | 797 | 5596 | 0 |
| embedding | 16 | 186 | 0 | 186 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 19 | 4985 | 797 | 5782 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4799 | 797 | 5596 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 16 | 186 | 0 | 186 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T21:30:57` `embedding` / `text-embedding-v3` input=100 output=0 total=100 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T21:31:00` `chat` / `qwen3-32b` input=977 output=76 total=1053 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T21:31:00` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T21:31:00` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T21:31:00` `embedding` / `text-embedding-v3` input=24 output=0 total=24 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T21:31:00` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T21:31:00` `embedding` / `text-embedding-v3` input=6 output=0 total=6 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T21:31:00` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T21:31:00` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T21:31:00` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T21:31:00` `embedding` / `text-embedding-v3` input=30 output=0 total=30 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T21:31:00` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T21:31:00` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T21:31:00` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T21:31:00` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T21:31:00` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
17. `2026-04-12T21:31:00` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
18. `2026-04-12T21:31:01` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
19. `2026-04-12T21:31:20` `chat` / `qwen3-32b` input=3822 output=721 total=4543 source=`ragent.llm.openai.openai_complete_if_cache`
