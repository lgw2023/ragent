# Model Usage Report: raw_export

- Task label: `export_md_to_raw_merge_units`
- Started at: `2026-05-20T22:00:01`
- Ended at: `2026-05-20T22:35:37`
- Metadata:
  - `pdf_file_path`: `/Volumes/SSD1/ragent/example/GBT22106-2008dz.pdf`
  - `md_path`: `/Volumes/SSD1/ragent/example/GBT22106-2008dz_md/txt/GBT22106-2008dz.md`
  - `output`: `/Volumes/SSD1/ragent/example/qwen4b_diet_kg_raw_units/GBT22106-2008dz.raw-units.jsonl`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 67 | 167690 | 158399 | 326089 | 0 |
| embedding | 67 | 7003 | 0 | 7003 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 1 | 0 | 0 | 0 | 1 |
| total | 136 | 174693 | 158399 | 333092 | 2 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| deepseek-v4-flash | 67 | 167690 | 158399 | 326089 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen/Qwen3-Embedding-4B | 67 | 7003 | 0 | 7003 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

### image

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-vl-flash | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-05-20T22:00:03` `chat` / `deepseek-v4-flash` input=25 output=40 total=65 source=`ragent.llm.openai.openai_complete_if_cache`
2. `2026-05-20T22:00:07` `embedding` / `Qwen/Qwen3-Embedding-4B` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
3. `2026-05-20T22:00:08` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
4. `2026-05-20T22:00:08` `image` / `qwen3-vl-flash` input=0 output=0 total=0 source=`ragent.inference_runtime._image_text_ping_sync`
5. `2026-05-20T22:00:13` `embedding` / `Qwen/Qwen3-Embedding-4B` input=34 output=0 total=34 source=`ragent.llm.openai.openai_embed`
6. `2026-05-20T22:00:28` `chat` / `deepseek-v4-flash` input=2467 output=1261 total=3728 source=`ragent.llm.openai.openai_complete_if_cache`
7. `2026-05-20T22:00:34` `embedding` / `Qwen/Qwen3-Embedding-4B` input=53 output=0 total=53 source=`ragent.llm.openai.openai_embed`
8. `2026-05-20T22:01:14` `chat` / `deepseek-v4-flash` input=2482 output=3284 total=5766 source=`ragent.llm.openai.openai_complete_if_cache`
9. `2026-05-20T22:01:20` `embedding` / `Qwen/Qwen3-Embedding-4B` input=237 output=0 total=237 source=`ragent.llm.openai.openai_embed`
10. `2026-05-20T22:03:56` `chat` / `deepseek-v4-flash` input=2666 output=14629 total=17295 source=`ragent.llm.openai.openai_complete_if_cache`
11. `2026-05-20T22:03:59` `embedding` / `Qwen/Qwen3-Embedding-4B` input=98 output=0 total=98 source=`ragent.llm.openai.openai_embed`
12. `2026-05-20T22:04:19` `chat` / `deepseek-v4-flash` input=2529 output=1778 total=4307 source=`ragent.llm.openai.openai_complete_if_cache`
13. `2026-05-20T22:04:20` `embedding` / `Qwen/Qwen3-Embedding-4B` input=303 output=0 total=303 source=`ragent.llm.openai.openai_embed`
14. `2026-05-20T22:05:31` `chat` / `deepseek-v4-flash` input=2697 output=5685 total=8382 source=`ragent.llm.openai.openai_complete_if_cache`
15. `2026-05-20T22:05:34` `embedding` / `Qwen/Qwen3-Embedding-4B` input=83 output=0 total=83 source=`ragent.llm.openai.openai_embed`
16. `2026-05-20T22:06:00` `chat` / `deepseek-v4-flash` input=2513 output=2217 total=4730 source=`ragent.llm.openai.openai_complete_if_cache`
17. `2026-05-20T22:06:59` `embedding` / `Qwen/Qwen3-Embedding-4B` input=63 output=0 total=63 source=`ragent.llm.openai.openai_embed`
18. `2026-05-20T22:07:15` `chat` / `deepseek-v4-flash` input=2498 output=1400 total=3898 source=`ragent.llm.openai.openai_complete_if_cache`
19. `2026-05-20T22:07:25` `embedding` / `Qwen/Qwen3-Embedding-4B` input=46 output=0 total=46 source=`ragent.llm.openai.openai_embed`
20. `2026-05-20T22:07:38` `chat` / `deepseek-v4-flash` input=2481 output=1042 total=3523 source=`ragent.llm.openai.openai_complete_if_cache`
21. `2026-05-20T22:07:44` `embedding` / `Qwen/Qwen3-Embedding-4B` input=53 output=0 total=53 source=`ragent.llm.openai.openai_embed`
22. `2026-05-20T22:07:57` `chat` / `deepseek-v4-flash` input=2488 output=1084 total=3572 source=`ragent.llm.openai.openai_complete_if_cache`
23. `2026-05-20T22:08:03` `embedding` / `Qwen/Qwen3-Embedding-4B` input=52 output=0 total=52 source=`ragent.llm.openai.openai_embed`
24. `2026-05-20T22:08:13` `chat` / `deepseek-v4-flash` input=2487 output=865 total=3352 source=`ragent.llm.openai.openai_complete_if_cache`
25. `2026-05-20T22:08:22` `embedding` / `Qwen/Qwen3-Embedding-4B` input=48 output=0 total=48 source=`ragent.llm.openai.openai_embed`
26. `2026-05-20T22:08:46` `chat` / `deepseek-v4-flash` input=2484 output=1746 total=4230 source=`ragent.llm.openai.openai_complete_if_cache`
27. `2026-05-20T22:08:47` `embedding` / `Qwen/Qwen3-Embedding-4B` input=47 output=0 total=47 source=`ragent.llm.openai.openai_embed`
28. `2026-05-20T22:08:55` `chat` / `deepseek-v4-flash` input=2483 output=698 total=3181 source=`ragent.llm.openai.openai_complete_if_cache`
29. `2026-05-20T22:09:02` `embedding` / `Qwen/Qwen3-Embedding-4B` input=66 output=0 total=66 source=`ragent.llm.openai.openai_embed`
30. `2026-05-20T22:09:31` `chat` / `deepseek-v4-flash` input=2504 output=2656 total=5160 source=`ragent.llm.openai.openai_complete_if_cache`
31. `2026-05-20T22:09:32` `embedding` / `Qwen/Qwen3-Embedding-4B` input=47 output=0 total=47 source=`ragent.llm.openai.openai_embed`
32. `2026-05-20T22:09:56` `chat` / `deepseek-v4-flash` input=2485 output=2024 total=4509 source=`ragent.llm.openai.openai_complete_if_cache`
33. `2026-05-20T22:10:02` `embedding` / `Qwen/Qwen3-Embedding-4B` input=54 output=0 total=54 source=`ragent.llm.openai.openai_embed`
34. `2026-05-20T22:10:36` `chat` / `deepseek-v4-flash` input=2489 output=3106 total=5595 source=`ragent.llm.openai.openai_complete_if_cache`
35. `2026-05-20T22:10:38` `embedding` / `Qwen/Qwen3-Embedding-4B` input=54 output=0 total=54 source=`ragent.llm.openai.openai_embed`
36. `2026-05-20T22:10:49` `chat` / `deepseek-v4-flash` input=2489 output=1165 total=3654 source=`ragent.llm.openai.openai_complete_if_cache`
37. `2026-05-20T22:10:51` `embedding` / `Qwen/Qwen3-Embedding-4B` input=55 output=0 total=55 source=`ragent.llm.openai.openai_embed`
38. `2026-05-20T22:11:12` `chat` / `deepseek-v4-flash` input=2492 output=2106 total=4598 source=`ragent.llm.openai.openai_complete_if_cache`
39. `2026-05-20T22:11:15` `embedding` / `Qwen/Qwen3-Embedding-4B` input=50 output=0 total=50 source=`ragent.llm.openai.openai_embed`
40. `2026-05-20T22:11:39` `chat` / `deepseek-v4-flash` input=2487 output=2214 total=4701 source=`ragent.llm.openai.openai_complete_if_cache`
41. `2026-05-20T22:11:41` `embedding` / `Qwen/Qwen3-Embedding-4B` input=67 output=0 total=67 source=`ragent.llm.openai.openai_embed`
42. `2026-05-20T22:12:04` `chat` / `deepseek-v4-flash` input=2505 output=1944 total=4449 source=`ragent.llm.openai.openai_complete_if_cache`
43. `2026-05-20T22:12:05` `embedding` / `Qwen/Qwen3-Embedding-4B` input=57 output=0 total=57 source=`ragent.llm.openai.openai_embed`
44. `2026-05-20T22:12:33` `chat` / `deepseek-v4-flash` input=2492 output=2570 total=5062 source=`ragent.llm.openai.openai_complete_if_cache`
45. `2026-05-20T22:12:34` `embedding` / `Qwen/Qwen3-Embedding-4B` input=52 output=0 total=52 source=`ragent.llm.openai.openai_embed`
46. `2026-05-20T22:12:53` `chat` / `deepseek-v4-flash` input=2487 output=1694 total=4181 source=`ragent.llm.openai.openai_complete_if_cache`
47. `2026-05-20T22:12:56` `embedding` / `Qwen/Qwen3-Embedding-4B` input=62 output=0 total=62 source=`ragent.llm.openai.openai_embed`
48. `2026-05-20T22:13:09` `chat` / `deepseek-v4-flash` input=2496 output=1373 total=3869 source=`ragent.llm.openai.openai_complete_if_cache`
49. `2026-05-20T22:13:13` `embedding` / `Qwen/Qwen3-Embedding-4B` input=226 output=0 total=226 source=`ragent.llm.openai.openai_embed`
50. `2026-05-20T22:13:45` `chat` / `deepseek-v4-flash` input=2640 output=3384 total=6024 source=`ragent.llm.openai.openai_complete_if_cache`
51. `2026-05-20T22:14:05` `embedding` / `Qwen/Qwen3-Embedding-4B` input=63 output=0 total=63 source=`ragent.llm.openai.openai_embed`
52. `2026-05-20T22:14:40` `chat` / `deepseek-v4-flash` input=2495 output=3240 total=5735 source=`ragent.llm.openai.openai_complete_if_cache`
53. `2026-05-20T22:14:43` `embedding` / `Qwen/Qwen3-Embedding-4B` input=79 output=0 total=79 source=`ragent.llm.openai.openai_embed`
54. `2026-05-20T22:15:31` `chat` / `deepseek-v4-flash` input=2508 output=4443 total=6951 source=`ragent.llm.openai.openai_complete_if_cache`
55. `2026-05-20T22:15:32` `embedding` / `Qwen/Qwen3-Embedding-4B` input=63 output=0 total=63 source=`ragent.llm.openai.openai_embed`
56. `2026-05-20T22:15:55` `chat` / `deepseek-v4-flash` input=2496 output=2387 total=4883 source=`ragent.llm.openai.openai_complete_if_cache`
57. `2026-05-20T22:15:57` `embedding` / `Qwen/Qwen3-Embedding-4B` input=37 output=0 total=37 source=`ragent.llm.openai.openai_embed`
58. `2026-05-20T22:16:07` `chat` / `deepseek-v4-flash` input=2476 output=793 total=3269 source=`ragent.llm.openai.openai_complete_if_cache`
59. `2026-05-20T22:16:08` `embedding` / `Qwen/Qwen3-Embedding-4B` input=54 output=0 total=54 source=`ragent.llm.openai.openai_embed`
60. `2026-05-20T22:16:15` `chat` / `deepseek-v4-flash` input=2492 output=644 total=3136 source=`ragent.llm.openai.openai_complete_if_cache`
61. `2026-05-20T22:16:17` `embedding` / `Qwen/Qwen3-Embedding-4B` input=189 output=0 total=189 source=`ragent.llm.openai.openai_embed`
62. `2026-05-20T22:16:28` `chat` / `deepseek-v4-flash` input=2634 output=877 total=3511 source=`ragent.llm.openai.openai_complete_if_cache`
63. `2026-05-20T22:16:30` `embedding` / `Qwen/Qwen3-Embedding-4B` input=41 output=0 total=41 source=`ragent.llm.openai.openai_embed`
64. `2026-05-20T22:16:42` `chat` / `deepseek-v4-flash` input=2477 output=993 total=3470 source=`ragent.llm.openai.openai_complete_if_cache`
65. `2026-05-20T22:16:43` `embedding` / `Qwen/Qwen3-Embedding-4B` input=326 output=0 total=326 source=`ragent.llm.openai.openai_embed`
66. `2026-05-20T22:17:00` `chat` / `deepseek-v4-flash` input=2740 output=1491 total=4231 source=`ragent.llm.openai.openai_complete_if_cache`
67. `2026-05-20T22:17:01` `embedding` / `Qwen/Qwen3-Embedding-4B` input=241 output=0 total=241 source=`ragent.llm.openai.openai_embed`
68. `2026-05-20T22:17:22` `chat` / `deepseek-v4-flash` input=2678 output=1754 total=4432 source=`ragent.llm.openai.openai_complete_if_cache`
69. `2026-05-20T22:17:23` `embedding` / `Qwen/Qwen3-Embedding-4B` input=74 output=0 total=74 source=`ragent.llm.openai.openai_embed`
70. `2026-05-20T22:17:44` `chat` / `deepseek-v4-flash` input=2508 output=1741 total=4249 source=`ragent.llm.openai.openai_complete_if_cache`
71. `2026-05-20T22:17:46` `embedding` / `Qwen/Qwen3-Embedding-4B` input=60 output=0 total=60 source=`ragent.llm.openai.openai_embed`
72. `2026-05-20T22:17:58` `chat` / `deepseek-v4-flash` input=2498 output=1091 total=3589 source=`ragent.llm.openai.openai_complete_if_cache`
73. `2026-05-20T22:17:59` `embedding` / `Qwen/Qwen3-Embedding-4B` input=476 output=0 total=476 source=`ragent.llm.openai.openai_embed`
74. `2026-05-20T22:18:59` `chat` / `deepseek-v4-flash` input=2930 output=5562 total=8492 source=`ragent.llm.openai.openai_complete_if_cache`
75. `2026-05-20T22:19:01` `embedding` / `Qwen/Qwen3-Embedding-4B` input=41 output=0 total=41 source=`ragent.llm.openai.openai_embed`
76. `2026-05-20T22:19:09` `chat` / `deepseek-v4-flash` input=2477 output=819 total=3296 source=`ragent.llm.openai.openai_complete_if_cache`
77. `2026-05-20T22:19:13` `embedding` / `Qwen/Qwen3-Embedding-4B` input=472 output=0 total=472 source=`ragent.llm.openai.openai_embed`
78. `2026-05-20T22:19:40` `chat` / `deepseek-v4-flash` input=2917 output=2459 total=5376 source=`ragent.llm.openai.openai_complete_if_cache`
79. `2026-05-20T22:19:55` `embedding` / `Qwen/Qwen3-Embedding-4B` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
80. `2026-05-20T22:20:07` `chat` / `deepseek-v4-flash` input=2479 output=1067 total=3546 source=`ragent.llm.openai.openai_complete_if_cache`
81. `2026-05-20T22:20:11` `embedding` / `Qwen/Qwen3-Embedding-4B` input=60 output=0 total=60 source=`ragent.llm.openai.openai_embed`
82. `2026-05-20T22:20:32` `chat` / `deepseek-v4-flash` input=2498 output=1594 total=4092 source=`ragent.llm.openai.openai_complete_if_cache`
83. `2026-05-20T22:20:34` `embedding` / `Qwen/Qwen3-Embedding-4B` input=382 output=0 total=382 source=`ragent.llm.openai.openai_embed`
84. `2026-05-20T22:20:59` `chat` / `deepseek-v4-flash` input=2833 output=2205 total=5038 source=`ragent.llm.openai.openai_complete_if_cache`
85. `2026-05-20T22:21:00` `embedding` / `Qwen/Qwen3-Embedding-4B` input=41 output=0 total=41 source=`ragent.llm.openai.openai_embed`
86. `2026-05-20T22:21:15` `chat` / `deepseek-v4-flash` input=2477 output=1355 total=3832 source=`ragent.llm.openai.openai_complete_if_cache`
87. `2026-05-20T22:21:16` `embedding` / `Qwen/Qwen3-Embedding-4B` input=392 output=0 total=392 source=`ragent.llm.openai.openai_embed`
88. `2026-05-20T22:21:39` `chat` / `deepseek-v4-flash` input=2829 output=2116 total=4945 source=`ragent.llm.openai.openai_complete_if_cache`
89. `2026-05-20T22:21:40` `embedding` / `Qwen/Qwen3-Embedding-4B` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
90. `2026-05-20T22:22:27` `chat` / `deepseek-v4-flash` input=2479 output=4264 total=6743 source=`ragent.llm.openai.openai_complete_if_cache`
91. `2026-05-20T22:22:29` `embedding` / `Qwen/Qwen3-Embedding-4B` input=60 output=0 total=60 source=`ragent.llm.openai.openai_embed`
92. `2026-05-20T22:22:43` `chat` / `deepseek-v4-flash` input=2498 output=1208 total=3706 source=`ragent.llm.openai.openai_complete_if_cache`
93. `2026-05-20T22:22:46` `embedding` / `Qwen/Qwen3-Embedding-4B` input=259 output=0 total=259 source=`ragent.llm.openai.openai_embed`
94. `2026-05-20T22:23:12` `chat` / `deepseek-v4-flash` input=2706 output=2445 total=5151 source=`ragent.llm.openai.openai_complete_if_cache`
95. `2026-05-20T22:23:14` `embedding` / `Qwen/Qwen3-Embedding-4B` input=41 output=0 total=41 source=`ragent.llm.openai.openai_embed`
96. `2026-05-20T22:23:28` `chat` / `deepseek-v4-flash` input=2477 output=1381 total=3858 source=`ragent.llm.openai.openai_complete_if_cache`
97. `2026-05-20T22:23:30` `embedding` / `Qwen/Qwen3-Embedding-4B` input=253 output=0 total=253 source=`ragent.llm.openai.openai_embed`
98. `2026-05-20T22:24:00` `chat` / `deepseek-v4-flash` input=2680 output=2725 total=5405 source=`ragent.llm.openai.openai_complete_if_cache`
99. `2026-05-20T22:24:04` `embedding` / `Qwen/Qwen3-Embedding-4B` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
100. `2026-05-20T22:24:38` `chat` / `deepseek-v4-flash` input=2479 output=3165 total=5644 source=`ragent.llm.openai.openai_complete_if_cache`
101. `2026-05-20T22:24:39` `embedding` / `Qwen/Qwen3-Embedding-4B` input=42 output=0 total=42 source=`ragent.llm.openai.openai_embed`
102. `2026-05-20T22:25:24` `chat` / `deepseek-v4-flash` input=2479 output=3729 total=6208 source=`ragent.llm.openai.openai_complete_if_cache`
103. `2026-05-20T22:25:27` `embedding` / `Qwen/Qwen3-Embedding-4B` input=105 output=0 total=105 source=`ragent.llm.openai.openai_embed`
104. `2026-05-20T22:25:50` `chat` / `deepseek-v4-flash` input=2541 output=1553 total=4094 source=`ragent.llm.openai.openai_complete_if_cache`
105. `2026-05-20T22:25:52` `embedding` / `Qwen/Qwen3-Embedding-4B` input=62 output=0 total=62 source=`ragent.llm.openai.openai_embed`
106. `2026-05-20T22:26:33` `chat` / `deepseek-v4-flash` input=2495 output=3747 total=6242 source=`ragent.llm.openai.openai_complete_if_cache`
107. `2026-05-20T22:26:35` `embedding` / `Qwen/Qwen3-Embedding-4B` input=52 output=0 total=52 source=`ragent.llm.openai.openai_embed`
108. `2026-05-20T22:26:48` `chat` / `deepseek-v4-flash` input=2486 output=1305 total=3791 source=`ragent.llm.openai.openai_complete_if_cache`
109. `2026-05-20T22:26:50` `embedding` / `Qwen/Qwen3-Embedding-4B` input=53 output=0 total=53 source=`ragent.llm.openai.openai_embed`
110. `2026-05-20T22:27:10` `chat` / `deepseek-v4-flash` input=2485 output=1887 total=4372 source=`ragent.llm.openai.openai_complete_if_cache`
111. `2026-05-20T22:27:12` `embedding` / `Qwen/Qwen3-Embedding-4B` input=48 output=0 total=48 source=`ragent.llm.openai.openai_embed`
112. `2026-05-20T22:28:08` `chat` / `deepseek-v4-flash` input=2482 output=5208 total=7690 source=`ragent.llm.openai.openai_complete_if_cache`
113. `2026-05-20T22:28:11` `embedding` / `Qwen/Qwen3-Embedding-4B` input=39 output=0 total=39 source=`ragent.llm.openai.openai_embed`
114. `2026-05-20T22:28:41` `chat` / `deepseek-v4-flash` input=2477 output=1913 total=4390 source=`ragent.llm.openai.openai_complete_if_cache`
115. `2026-05-20T22:28:50` `embedding` / `Qwen/Qwen3-Embedding-4B` input=57 output=0 total=57 source=`ragent.llm.openai.openai_embed`
116. `2026-05-20T22:29:20` `chat` / `deepseek-v4-flash` input=2492 output=1984 total=4476 source=`ragent.llm.openai.openai_complete_if_cache`
117. `2026-05-20T22:29:36` `embedding` / `Qwen/Qwen3-Embedding-4B` input=78 output=0 total=78 source=`ragent.llm.openai.openai_embed`
118. `2026-05-20T22:30:01` `chat` / `deepseek-v4-flash` input=2510 output=1522 total=4032 source=`ragent.llm.openai.openai_complete_if_cache`
119. `2026-05-20T22:30:14` `embedding` / `Qwen/Qwen3-Embedding-4B` input=85 output=0 total=85 source=`ragent.llm.openai.openai_embed`
120. `2026-05-20T22:30:55` `chat` / `deepseek-v4-flash` input=2521 output=2912 total=5433 source=`ragent.llm.openai.openai_complete_if_cache`
121. `2026-05-20T22:30:58` `embedding` / `Qwen/Qwen3-Embedding-4B` input=109 output=0 total=109 source=`ragent.llm.openai.openai_embed`
122. `2026-05-20T22:31:19` `chat` / `deepseek-v4-flash` input=2537 output=1946 total=4483 source=`ragent.llm.openai.openai_complete_if_cache`
123. `2026-05-20T22:31:21` `embedding` / `Qwen/Qwen3-Embedding-4B` input=54 output=0 total=54 source=`ragent.llm.openai.openai_embed`
124. `2026-05-20T22:31:44` `chat` / `deepseek-v4-flash` input=2489 output=2397 total=4886 source=`ragent.llm.openai.openai_complete_if_cache`
125. `2026-05-20T22:31:48` `embedding` / `Qwen/Qwen3-Embedding-4B` input=84 output=0 total=84 source=`ragent.llm.openai.openai_embed`
126. `2026-05-20T22:32:29` `chat` / `deepseek-v4-flash` input=2514 output=3662 total=6176 source=`ragent.llm.openai.openai_complete_if_cache`
127. `2026-05-20T22:32:31` `embedding` / `Qwen/Qwen3-Embedding-4B` input=85 output=0 total=85 source=`ragent.llm.openai.openai_embed`
128. `2026-05-20T22:33:24` `chat` / `deepseek-v4-flash` input=2521 output=1174 total=3695 source=`ragent.llm.openai.openai_complete_if_cache`
129. `2026-05-20T22:33:25` `embedding` / `Qwen/Qwen3-Embedding-4B` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
130. `2026-05-20T22:34:13` `chat` / `deepseek-v4-flash` input=2479 output=4350 total=6829 source=`ragent.llm.openai.openai_complete_if_cache`
131. `2026-05-20T22:34:14` `embedding` / `Qwen/Qwen3-Embedding-4B` input=68 output=0 total=68 source=`ragent.llm.openai.openai_embed`
132. `2026-05-20T22:34:49` `chat` / `deepseek-v4-flash` input=2503 output=3016 total=5519 source=`ragent.llm.openai.openai_complete_if_cache`
133. `2026-05-20T22:34:51` `embedding` / `Qwen/Qwen3-Embedding-4B` input=86 output=0 total=86 source=`ragent.llm.openai.openai_embed`
134. `2026-05-20T22:35:17` `chat` / `deepseek-v4-flash` input=2523 output=2630 total=5153 source=`ragent.llm.openai.openai_complete_if_cache`
135. `2026-05-20T22:35:18` `embedding` / `Qwen/Qwen3-Embedding-4B` input=96 output=0 total=96 source=`ragent.llm.openai.openai_embed`
136. `2026-05-20T22:35:37` `chat` / `deepseek-v4-flash` input=2529 output=1680 total=4209 source=`ragent.llm.openai.openai_complete_if_cache`
