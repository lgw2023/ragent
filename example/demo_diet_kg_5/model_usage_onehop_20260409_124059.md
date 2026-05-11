# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-09T12:40:48`
- Ended at: `2026-04-09T12:40:59`
- Metadata:
  - `query`: `如果你现在要立刻准备一顿更贴近这张指南配图所倡导的家庭健康饮食，以下哪种做法最符合图中直接传达的原则：A. 一个人点外卖炸鸡配含糖饮料，家人各吃各的；B. 全家一起用台面上的新鲜蔬菜和鸡蛋现做一餐；C. 只给孩子吃鸡蛋，大人不吃蔬菜；D. 用现成零食代替做饭以节省时间`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 3713 | 289 | 4002 | 0 |
| embedding | 13 | 167 | 0 | 167 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 16 | 3880 | 289 | 4169 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 3713 | 289 | 4002 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 13 | 167 | 0 | 167 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-09T12:40:48` `embedding` / `text-embedding-v3` input=97 output=0 total=97 source=`ragent.llm.openai.openai_embed`
2. `2026-04-09T12:40:50` `chat` / `qwen3-32b` input=962 output=59 total=1021 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-09T12:40:50` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
4. `2026-04-09T12:40:50` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
5. `2026-04-09T12:40:50` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
6. `2026-04-09T12:40:50` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
7. `2026-04-09T12:40:51` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
8. `2026-04-09T12:40:51` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
9. `2026-04-09T12:40:51` `embedding` / `text-embedding-v3` input=26 output=0 total=26 source=`ragent.llm.openai.openai_embed`
10. `2026-04-09T12:40:51` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
11. `2026-04-09T12:40:51` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
12. `2026-04-09T12:40:51` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-09T12:40:51` `embedding` / `text-embedding-v3` input=17 output=0 total=17 source=`ragent.llm.openai.openai_embed`
14. `2026-04-09T12:40:51` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
15. `2026-04-09T12:40:52` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
16. `2026-04-09T12:40:59` `chat` / `qwen3-32b` input=2751 output=230 total=2981 source=`ragent.llm.openai.openai_complete_if_cache`
