# Model Usage Report: onehop

- Task label: `onehop_trace`
- Started at: `2026-04-12T18:58:48`
- Ended at: `2026-04-12T18:59:09`
- Metadata:
  - `query`: `如果我想把早餐吃得更均衡一点，一碗杂粮粥再配一份豆浆和少量鸡蛋，这样的搭配和“谷薯类、蔬菜水果类、动物性食物、大豆和坚果、烹调油和盐”这些类别相比，哪一类最容易吃得过量，哪一类通常又最容易吃得不够？另外，日常饮水量大致应该控制在什么范围？`
  - `mode`: `hybrid`
  - `trace`: `True`
  - `history_messages`: `0`
  - `history_turns`: `None`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 2 | 4743 | 547 | 5290 | 0 |
| embedding | 16 | 200 | 0 | 200 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 0 | 0 | 0 | 0 | 0 |
| total | 19 | 4943 | 547 | 5490 | 1 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-32b | 2 | 4743 | 547 | 5290 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 16 | 200 | 0 | 200 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-04-12T18:58:48` `embedding` / `text-embedding-v3` input=91 output=0 total=91 source=`ragent.llm.openai.openai_embed`
2. `2026-04-12T18:58:52` `chat` / `qwen3-32b` input=948 output=84 total=1032 source=`ragent.llm.openai.openai_complete_if_cache`
3. `2026-04-12T18:58:53` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
4. `2026-04-12T18:58:53` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
5. `2026-04-12T18:58:53` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
6. `2026-04-12T18:58:53` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
7. `2026-04-12T18:58:53` `embedding` / `text-embedding-v3` input=4 output=0 total=4 source=`ragent.llm.openai.openai_embed`
8. `2026-04-12T18:58:53` `embedding` / `text-embedding-v3` input=1 output=0 total=1 source=`ragent.llm.openai.openai_embed`
9. `2026-04-12T18:58:53` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
10. `2026-04-12T18:58:53` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
11. `2026-04-12T18:58:53` `embedding` / `text-embedding-v3` input=28 output=0 total=28 source=`ragent.llm.openai.openai_embed`
12. `2026-04-12T18:58:53` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
13. `2026-04-12T18:58:53` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
14. `2026-04-12T18:58:53` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
15. `2026-04-12T18:58:53` `embedding` / `text-embedding-v3` input=3 output=0 total=3 source=`ragent.llm.openai.openai_embed`
16. `2026-04-12T18:58:53` `embedding` / `text-embedding-v3` input=5 output=0 total=5 source=`ragent.llm.openai.openai_embed`
17. `2026-04-12T18:58:53` `embedding` / `text-embedding-v3` input=2 output=0 total=2 source=`ragent.llm.openai.openai_embed`
18. `2026-04-12T18:58:54` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
19. `2026-04-12T18:59:09` `chat` / `qwen3-32b` input=3795 output=463 total=4258 source=`ragent.llm.openai.openai_complete_if_cache`
