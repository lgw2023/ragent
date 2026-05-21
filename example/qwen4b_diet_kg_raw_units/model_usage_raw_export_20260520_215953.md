# Model Usage Report: raw_export

- Task label: `export_md_to_raw_merge_units`
- Started at: `2026-05-20T21:13:54`
- Ended at: `2026-05-20T21:59:53`
- Metadata:
  - `pdf_file_path`: `/Volumes/SSD1/ragent/example/GBT1354-2018bz.pdf`
  - `md_path`: `/Volumes/SSD1/ragent/example/GBT1354-2018bz_md/txt/GBT1354-2018bz.md`
  - `output`: `/Volumes/SSD1/ragent/example/qwen4b_diet_kg_raw_units/GBT1354-2018bz.raw-units.jsonl`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 66 | 166215 | 209809 | 376024 | 0 |
| embedding | 66 | 7982 | 0 | 7982 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 1 | 0 | 0 | 0 | 1 |
| total | 134 | 174197 | 209809 | 384006 | 2 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| deepseek-v4-flash | 66 | 166215 | 209809 | 376024 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen/Qwen3-Embedding-4B | 66 | 7982 | 0 | 7982 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

### image

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-vl-flash | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-05-20T21:13:57` `chat` / `deepseek-v4-flash` input=25 output=51 total=76 source=`ragent.llm.openai.openai_complete_if_cache`
2. `2026-05-20T21:14:00` `embedding` / `Qwen/Qwen3-Embedding-4B` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
3. `2026-05-20T21:14:02` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
4. `2026-05-20T21:14:04` `image` / `qwen3-vl-flash` input=0 output=0 total=0 source=`ragent.inference_runtime._image_text_ping_sync`
5. `2026-05-20T21:14:23` `embedding` / `Qwen/Qwen3-Embedding-4B` input=77 output=0 total=77 source=`ragent.llm.openai.openai_embed`
6. `2026-05-20T21:14:54` `chat` / `deepseek-v4-flash` input=2500 output=2303 total=4803 source=`ragent.llm.openai.openai_complete_if_cache`
7. `2026-05-20T21:14:56` `embedding` / `Qwen/Qwen3-Embedding-4B` input=331 output=0 total=331 source=`ragent.llm.openai.openai_embed`
8. `2026-05-20T21:16:53` `chat` / `deepseek-v4-flash` input=2722 output=10936 total=13658 source=`ragent.llm.openai.openai_complete_if_cache`
9. `2026-05-20T21:16:56` `embedding` / `Qwen/Qwen3-Embedding-4B` input=80 output=0 total=80 source=`ragent.llm.openai.openai_embed`
10. `2026-05-20T21:17:42` `chat` / `deepseek-v4-flash` input=2514 output=3651 total=6165 source=`ragent.llm.openai.openai_complete_if_cache`
11. `2026-05-20T21:17:50` `embedding` / `Qwen/Qwen3-Embedding-4B` input=495 output=0 total=495 source=`ragent.llm.openai.openai_embed`
12. `2026-05-20T21:19:10` `chat` / `deepseek-v4-flash` input=2861 output=7680 total=10541 source=`ragent.llm.openai.openai_complete_if_cache`
13. `2026-05-20T21:19:12` `embedding` / `Qwen/Qwen3-Embedding-4B` input=46 output=0 total=46 source=`ragent.llm.openai.openai_embed`
14. `2026-05-20T21:19:31` `chat` / `deepseek-v4-flash` input=2481 output=1796 total=4277 source=`ragent.llm.openai.openai_complete_if_cache`
15. `2026-05-20T21:19:33` `embedding` / `Qwen/Qwen3-Embedding-4B` input=54 output=0 total=54 source=`ragent.llm.openai.openai_embed`
16. `2026-05-20T21:20:23` `chat` / `deepseek-v4-flash` input=2490 output=4806 total=7296 source=`ragent.llm.openai.openai_complete_if_cache`
17. `2026-05-20T21:20:25` `embedding` / `Qwen/Qwen3-Embedding-4B` input=71 output=0 total=71 source=`ragent.llm.openai.openai_embed`
18. `2026-05-20T21:20:44` `chat` / `deepseek-v4-flash` input=2506 output=1575 total=4081 source=`ragent.llm.openai.openai_complete_if_cache`
19. `2026-05-20T21:20:46` `embedding` / `Qwen/Qwen3-Embedding-4B` input=72 output=0 total=72 source=`ragent.llm.openai.openai_embed`
20. `2026-05-20T21:21:00` `chat` / `deepseek-v4-flash` input=2508 output=1179 total=3687 source=`ragent.llm.openai.openai_complete_if_cache`
21. `2026-05-20T21:21:02` `embedding` / `Qwen/Qwen3-Embedding-4B` input=55 output=0 total=55 source=`ragent.llm.openai.openai_embed`
22. `2026-05-20T21:21:22` `chat` / `deepseek-v4-flash` input=2493 output=1634 total=4127 source=`ragent.llm.openai.openai_complete_if_cache`
23. `2026-05-20T21:21:24` `embedding` / `Qwen/Qwen3-Embedding-4B` input=46 output=0 total=46 source=`ragent.llm.openai.openai_embed`
24. `2026-05-20T21:21:46` `chat` / `deepseek-v4-flash` input=2479 output=1837 total=4316 source=`ragent.llm.openai.openai_complete_if_cache`
25. `2026-05-20T21:21:48` `embedding` / `Qwen/Qwen3-Embedding-4B` input=41 output=0 total=41 source=`ragent.llm.openai.openai_embed`
26. `2026-05-20T21:22:09` `chat` / `deepseek-v4-flash` input=2478 output=1670 total=4148 source=`ragent.llm.openai.openai_complete_if_cache`
27. `2026-05-20T21:22:12` `embedding` / `Qwen/Qwen3-Embedding-4B` input=65 output=0 total=65 source=`ragent.llm.openai.openai_embed`
28. `2026-05-20T21:22:33` `chat` / `deepseek-v4-flash` input=2502 output=1953 total=4455 source=`ragent.llm.openai.openai_complete_if_cache`
29. `2026-05-20T21:22:35` `embedding` / `Qwen/Qwen3-Embedding-4B` input=76 output=0 total=76 source=`ragent.llm.openai.openai_embed`
30. `2026-05-20T21:23:00` `chat` / `deepseek-v4-flash` input=2508 output=2160 total=4668 source=`ragent.llm.openai.openai_complete_if_cache`
31. `2026-05-20T21:23:02` `embedding` / `Qwen/Qwen3-Embedding-4B` input=94 output=0 total=94 source=`ragent.llm.openai.openai_embed`
32. `2026-05-20T21:23:23` `chat` / `deepseek-v4-flash` input=2527 output=1952 total=4479 source=`ragent.llm.openai.openai_complete_if_cache`
33. `2026-05-20T21:23:53` `embedding` / `Qwen/Qwen3-Embedding-4B` input=54 output=0 total=54 source=`ragent.llm.openai.openai_embed`
34. `2026-05-20T21:24:13` `chat` / `deepseek-v4-flash` input=2485 output=1725 total=4210 source=`ragent.llm.openai.openai_complete_if_cache`
35. `2026-05-20T21:24:21` `embedding` / `Qwen/Qwen3-Embedding-4B` input=89 output=0 total=89 source=`ragent.llm.openai.openai_embed`
36. `2026-05-20T21:24:40` `chat` / `deepseek-v4-flash` input=2525 output=1525 total=4050 source=`ragent.llm.openai.openai_complete_if_cache`
37. `2026-05-20T21:24:43` `embedding` / `Qwen/Qwen3-Embedding-4B` input=43 output=0 total=43 source=`ragent.llm.openai.openai_embed`
38. `2026-05-20T21:25:31` `chat` / `deepseek-v4-flash` input=2480 output=3965 total=6445 source=`ragent.llm.openai.openai_complete_if_cache`
39. `2026-05-20T21:25:33` `embedding` / `Qwen/Qwen3-Embedding-4B` input=43 output=0 total=43 source=`ragent.llm.openai.openai_embed`
40. `2026-05-20T21:26:01` `chat` / `deepseek-v4-flash` input=2481 output=1946 total=4427 source=`ragent.llm.openai.openai_complete_if_cache`
41. `2026-05-20T21:26:03` `embedding` / `Qwen/Qwen3-Embedding-4B` input=39 output=0 total=39 source=`ragent.llm.openai.openai_embed`
42. `2026-05-20T21:26:20` `chat` / `deepseek-v4-flash` input=2475 output=1392 total=3867 source=`ragent.llm.openai.openai_complete_if_cache`
43. `2026-05-20T21:26:23` `embedding` / `Qwen/Qwen3-Embedding-4B` input=43 output=0 total=43 source=`ragent.llm.openai.openai_embed`
44. `2026-05-20T21:26:41` `chat` / `deepseek-v4-flash` input=2482 output=1514 total=3996 source=`ragent.llm.openai.openai_complete_if_cache`
45. `2026-05-20T21:26:43` `embedding` / `Qwen/Qwen3-Embedding-4B` input=45 output=0 total=45 source=`ragent.llm.openai.openai_embed`
46. `2026-05-20T21:27:06` `chat` / `deepseek-v4-flash` input=2481 output=1846 total=4327 source=`ragent.llm.openai.openai_complete_if_cache`
47. `2026-05-20T21:27:11` `embedding` / `Qwen/Qwen3-Embedding-4B` input=59 output=0 total=59 source=`ragent.llm.openai.openai_embed`
48. `2026-05-20T21:27:39` `chat` / `deepseek-v4-flash` input=2495 output=2167 total=4662 source=`ragent.llm.openai.openai_complete_if_cache`
49. `2026-05-20T21:27:41` `embedding` / `Qwen/Qwen3-Embedding-4B` input=60 output=0 total=60 source=`ragent.llm.openai.openai_embed`
50. `2026-05-20T21:28:24` `chat` / `deepseek-v4-flash` input=2499 output=3661 total=6160 source=`ragent.llm.openai.openai_complete_if_cache`
51. `2026-05-20T21:28:26` `embedding` / `Qwen/Qwen3-Embedding-4B` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
52. `2026-05-20T21:28:49` `chat` / `deepseek-v4-flash` input=2481 output=2058 total=4539 source=`ragent.llm.openai.openai_complete_if_cache`
53. `2026-05-20T21:28:52` `embedding` / `Qwen/Qwen3-Embedding-4B` input=54 output=0 total=54 source=`ragent.llm.openai.openai_embed`
54. `2026-05-20T21:29:05` `chat` / `deepseek-v4-flash` input=2491 output=1189 total=3680 source=`ragent.llm.openai.openai_complete_if_cache`
55. `2026-05-20T21:29:07` `embedding` / `Qwen/Qwen3-Embedding-4B` input=66 output=0 total=66 source=`ragent.llm.openai.openai_embed`
56. `2026-05-20T21:30:05` `chat` / `deepseek-v4-flash` input=2502 output=4424 total=6926 source=`ragent.llm.openai.openai_complete_if_cache`
57. `2026-05-20T21:30:09` `embedding` / `Qwen/Qwen3-Embedding-4B` input=55 output=0 total=55 source=`ragent.llm.openai.openai_embed`
58. `2026-05-20T21:30:30` `chat` / `deepseek-v4-flash` input=2491 output=1666 total=4157 source=`ragent.llm.openai.openai_complete_if_cache`
59. `2026-05-20T21:30:49` `embedding` / `Qwen/Qwen3-Embedding-4B` input=79 output=0 total=79 source=`ragent.llm.openai.openai_embed`
60. `2026-05-20T21:31:20` `chat` / `deepseek-v4-flash` input=2516 output=2352 total=4868 source=`ragent.llm.openai.openai_complete_if_cache`
61. `2026-05-20T21:31:24` `embedding` / `Qwen/Qwen3-Embedding-4B` input=59 output=0 total=59 source=`ragent.llm.openai.openai_embed`
62. `2026-05-20T21:31:54` `chat` / `deepseek-v4-flash` input=2490 output=2469 total=4959 source=`ragent.llm.openai.openai_complete_if_cache`
63. `2026-05-20T21:31:56` `embedding` / `Qwen/Qwen3-Embedding-4B` input=47 output=0 total=47 source=`ragent.llm.openai.openai_embed`
64. `2026-05-20T21:32:23` `chat` / `deepseek-v4-flash` input=2482 output=2409 total=4891 source=`ragent.llm.openai.openai_complete_if_cache`
65. `2026-05-20T21:32:25` `embedding` / `Qwen/Qwen3-Embedding-4B` input=52 output=0 total=52 source=`ragent.llm.openai.openai_embed`
66. `2026-05-20T21:33:12` `chat` / `deepseek-v4-flash` input=2488 output=4713 total=7201 source=`ragent.llm.openai.openai_complete_if_cache`
67. `2026-05-20T21:33:15` `embedding` / `Qwen/Qwen3-Embedding-4B` input=54 output=0 total=54 source=`ragent.llm.openai.openai_embed`
68. `2026-05-20T21:33:33` `chat` / `deepseek-v4-flash` input=2491 output=1388 total=3879 source=`ragent.llm.openai.openai_complete_if_cache`
69. `2026-05-20T21:33:36` `embedding` / `Qwen/Qwen3-Embedding-4B` input=69 output=0 total=69 source=`ragent.llm.openai.openai_embed`
70. `2026-05-20T21:34:13` `chat` / `deepseek-v4-flash` input=2502 output=3128 total=5630 source=`ragent.llm.openai.openai_complete_if_cache`
71. `2026-05-20T21:34:22` `embedding` / `Qwen/Qwen3-Embedding-4B` input=85 output=0 total=85 source=`ragent.llm.openai.openai_embed`
72. `2026-05-20T21:34:43` `chat` / `deepseek-v4-flash` input=2521 output=1754 total=4275 source=`ragent.llm.openai.openai_complete_if_cache`
73. `2026-05-20T21:34:46` `embedding` / `Qwen/Qwen3-Embedding-4B` input=81 output=0 total=81 source=`ragent.llm.openai.openai_embed`
74. `2026-05-20T21:35:21` `chat` / `deepseek-v4-flash` input=2518 output=2868 total=5386 source=`ragent.llm.openai.openai_complete_if_cache`
75. `2026-05-20T21:35:24` `embedding` / `Qwen/Qwen3-Embedding-4B` input=68 output=0 total=68 source=`ragent.llm.openai.openai_embed`
76. `2026-05-20T21:36:08` `chat` / `deepseek-v4-flash` input=2506 output=4188 total=6694 source=`ragent.llm.openai.openai_complete_if_cache`
77. `2026-05-20T21:36:11` `embedding` / `Qwen/Qwen3-Embedding-4B` input=65 output=0 total=65 source=`ragent.llm.openai.openai_embed`
78. `2026-05-20T21:37:10` `chat` / `deepseek-v4-flash` input=2500 output=5181 total=7681 source=`ragent.llm.openai.openai_complete_if_cache`
79. `2026-05-20T21:37:13` `embedding` / `Qwen/Qwen3-Embedding-4B` input=741 output=0 total=741 source=`ragent.llm.openai.openai_embed`
80. `2026-05-20T21:38:03` `chat` / `deepseek-v4-flash` input=3218 output=4724 total=7942 source=`ragent.llm.openai.openai_complete_if_cache`
81. `2026-05-20T21:38:06` `embedding` / `Qwen/Qwen3-Embedding-4B` input=542 output=0 total=542 source=`ragent.llm.openai.openai_embed`
82. `2026-05-20T21:38:40` `chat` / `deepseek-v4-flash` input=2998 output=2959 total=5957 source=`ragent.llm.openai.openai_complete_if_cache`
83. `2026-05-20T21:38:43` `embedding` / `Qwen/Qwen3-Embedding-4B` input=69 output=0 total=69 source=`ragent.llm.openai.openai_embed`
84. `2026-05-20T21:39:04` `chat` / `deepseek-v4-flash` input=2504 output=1664 total=4168 source=`ragent.llm.openai.openai_complete_if_cache`
85. `2026-05-20T21:39:13` `embedding` / `Qwen/Qwen3-Embedding-4B` input=761 output=0 total=761 source=`ragent.llm.openai.openai_embed`
86. `2026-05-20T21:39:51` `chat` / `deepseek-v4-flash` input=3234 output=3040 total=6274 source=`ragent.llm.openai.openai_complete_if_cache`
87. `2026-05-20T21:39:54` `embedding` / `Qwen/Qwen3-Embedding-4B` input=370 output=0 total=370 source=`ragent.llm.openai.openai_embed`
88. `2026-05-20T21:40:25` `chat` / `deepseek-v4-flash` input=2823 output=2325 total=5148 source=`ragent.llm.openai.openai_complete_if_cache`
89. `2026-05-20T21:40:27` `embedding` / `Qwen/Qwen3-Embedding-4B` input=57 output=0 total=57 source=`ragent.llm.openai.openai_embed`
90. `2026-05-20T21:41:12` `chat` / `deepseek-v4-flash` input=2493 output=3937 total=6430 source=`ragent.llm.openai.openai_complete_if_cache`
91. `2026-05-20T21:41:16` `embedding` / `Qwen/Qwen3-Embedding-4B` input=49 output=0 total=49 source=`ragent.llm.openai.openai_embed`
92. `2026-05-20T21:41:57` `chat` / `deepseek-v4-flash` input=2486 output=3569 total=6055 source=`ragent.llm.openai.openai_complete_if_cache`
93. `2026-05-20T21:42:00` `embedding` / `Qwen/Qwen3-Embedding-4B` input=436 output=0 total=436 source=`ragent.llm.openai.openai_embed`
94. `2026-05-20T21:45:21` `chat` / `deepseek-v4-flash` input=2818 output=19665 total=22483 source=`ragent.llm.openai.openai_complete_if_cache`
95. `2026-05-20T21:45:33` `embedding` / `Qwen/Qwen3-Embedding-4B` input=41 output=0 total=41 source=`ragent.llm.openai.openai_embed`
96. `2026-05-20T21:46:16` `chat` / `deepseek-v4-flash` input=2478 output=3649 total=6127 source=`ragent.llm.openai.openai_complete_if_cache`
97. `2026-05-20T21:46:23` `embedding` / `Qwen/Qwen3-Embedding-4B` input=41 output=0 total=41 source=`ragent.llm.openai.openai_embed`
98. `2026-05-20T21:47:03` `chat` / `deepseek-v4-flash` input=2476 output=3474 total=5950 source=`ragent.llm.openai.openai_complete_if_cache`
99. `2026-05-20T21:47:09` `embedding` / `Qwen/Qwen3-Embedding-4B` input=46 output=0 total=46 source=`ragent.llm.openai.openai_embed`
100. `2026-05-20T21:47:35` `chat` / `deepseek-v4-flash` input=2484 output=2332 total=4816 source=`ragent.llm.openai.openai_complete_if_cache`
101. `2026-05-20T21:47:37` `embedding` / `Qwen/Qwen3-Embedding-4B` input=38 output=0 total=38 source=`ragent.llm.openai.openai_embed`
102. `2026-05-20T21:48:08` `chat` / `deepseek-v4-flash` input=2476 output=2445 total=4921 source=`ragent.llm.openai.openai_complete_if_cache`
103. `2026-05-20T21:48:13` `embedding` / `Qwen/Qwen3-Embedding-4B` input=227 output=0 total=227 source=`ragent.llm.openai.openai_embed`
104. `2026-05-20T21:48:42` `chat` / `deepseek-v4-flash` input=2652 output=2688 total=5340 source=`ragent.llm.openai.openai_complete_if_cache`
105. `2026-05-20T21:48:44` `embedding` / `Qwen/Qwen3-Embedding-4B` input=118 output=0 total=118 source=`ragent.llm.openai.openai_embed`
106. `2026-05-20T21:49:25` `chat` / `deepseek-v4-flash` input=2546 output=3930 total=6476 source=`ragent.llm.openai.openai_complete_if_cache`
107. `2026-05-20T21:49:27` `embedding` / `Qwen/Qwen3-Embedding-4B` input=182 output=0 total=182 source=`ragent.llm.openai.openai_embed`
108. `2026-05-20T21:50:09` `chat` / `deepseek-v4-flash` input=2610 output=4320 total=6930 source=`ragent.llm.openai.openai_complete_if_cache`
109. `2026-05-20T21:50:12` `embedding` / `Qwen/Qwen3-Embedding-4B` input=72 output=0 total=72 source=`ragent.llm.openai.openai_embed`
110. `2026-05-20T21:50:55` `chat` / `deepseek-v4-flash` input=2507 output=3333 total=5840 source=`ragent.llm.openai.openai_complete_if_cache`
111. `2026-05-20T21:51:00` `embedding` / `Qwen/Qwen3-Embedding-4B` input=130 output=0 total=130 source=`ragent.llm.openai.openai_embed`
112. `2026-05-20T21:52:03` `chat` / `deepseek-v4-flash` input=2555 output=4461 total=7016 source=`ragent.llm.openai.openai_complete_if_cache`
113. `2026-05-20T21:52:38` `embedding` / `Qwen/Qwen3-Embedding-4B` input=118 output=0 total=118 source=`ragent.llm.openai.openai_embed`
114. `2026-05-20T21:53:45` `chat` / `deepseek-v4-flash` input=2552 output=5334 total=7886 source=`ragent.llm.openai.openai_complete_if_cache`
115. `2026-05-20T21:53:47` `embedding` / `Qwen/Qwen3-Embedding-4B` input=52 output=0 total=52 source=`ragent.llm.openai.openai_embed`
116. `2026-05-20T21:54:10` `chat` / `deepseek-v4-flash` input=2492 output=1821 total=4313 source=`ragent.llm.openai.openai_complete_if_cache`
117. `2026-05-20T21:54:12` `embedding` / `Qwen/Qwen3-Embedding-4B` input=191 output=0 total=191 source=`ragent.llm.openai.openai_embed`
118. `2026-05-20T21:54:42` `chat` / `deepseek-v4-flash` input=2624 output=2398 total=5022 source=`ragent.llm.openai.openai_complete_if_cache`
119. `2026-05-20T21:54:44` `embedding` / `Qwen/Qwen3-Embedding-4B` input=166 output=0 total=166 source=`ragent.llm.openai.openai_embed`
120. `2026-05-20T21:55:25` `chat` / `deepseek-v4-flash` input=2599 output=3787 total=6386 source=`ragent.llm.openai.openai_complete_if_cache`
121. `2026-05-20T21:55:27` `embedding` / `Qwen/Qwen3-Embedding-4B` input=69 output=0 total=69 source=`ragent.llm.openai.openai_embed`
122. `2026-05-20T21:55:53` `chat` / `deepseek-v4-flash` input=2502 output=1885 total=4387 source=`ragent.llm.openai.openai_complete_if_cache`
123. `2026-05-20T21:55:55` `embedding` / `Qwen/Qwen3-Embedding-4B` input=84 output=0 total=84 source=`ragent.llm.openai.openai_embed`
124. `2026-05-20T21:56:46` `chat` / `deepseek-v4-flash` input=2523 output=4227 total=6750 source=`ragent.llm.openai.openai_complete_if_cache`
125. `2026-05-20T21:56:47` `embedding` / `Qwen/Qwen3-Embedding-4B` input=75 output=0 total=75 source=`ragent.llm.openai.openai_embed`
126. `2026-05-20T21:57:14` `chat` / `deepseek-v4-flash` input=2513 output=2496 total=5009 source=`ragent.llm.openai.openai_complete_if_cache`
127. `2026-05-20T21:57:17` `embedding` / `Qwen/Qwen3-Embedding-4B` input=114 output=0 total=114 source=`ragent.llm.openai.openai_embed`
128. `2026-05-20T21:58:01` `chat` / `deepseek-v4-flash` input=2549 output=3516 total=6065 source=`ragent.llm.openai.openai_complete_if_cache`
129. `2026-05-20T21:58:04` `embedding` / `Qwen/Qwen3-Embedding-4B` input=49 output=0 total=49 source=`ragent.llm.openai.openai_embed`
130. `2026-05-20T21:58:26` `chat` / `deepseek-v4-flash` input=2486 output=1640 total=4126 source=`ragent.llm.openai.openai_complete_if_cache`
131. `2026-05-20T21:58:42` `embedding` / `Qwen/Qwen3-Embedding-4B` input=125 output=0 total=125 source=`ragent.llm.openai.openai_embed`
132. `2026-05-20T21:59:06` `chat` / `deepseek-v4-flash` input=2557 output=1959 total=4516 source=`ragent.llm.openai.openai_complete_if_cache`
133. `2026-05-20T21:59:13` `embedding` / `Qwen/Qwen3-Embedding-4B` input=50 output=0 total=50 source=`ragent.llm.openai.openai_embed`
134. `2026-05-20T21:59:53` `chat` / `deepseek-v4-flash` input=2484 output=3520 total=6004 source=`ragent.llm.openai.openai_complete_if_cache`
