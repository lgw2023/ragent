# Model Usage Report: raw_export

- Task label: `export_md_to_raw_merge_units`
- Started at: `2026-05-20T23:47:13`
- Ended at: `2026-05-21T00:54:51`
- Metadata:
  - `pdf_file_path`: `/Volumes/SSD1/ragent/example/成人高血压食养指南_2022.pdf`
  - `md_path`: `/Volumes/SSD1/ragent/example/成人高血压食养指南_2022_md/txt/成人高血压食养指南_2022.md`
  - `output`: `/Volumes/SSD1/ragent/example/qwen4b_diet_kg_raw_units/成人高血压食养指南_2022.raw-units.jsonl`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 110 | 322487 | 370060 | 692547 | 0 |
| embedding | 108 | 59740 | 0 | 59740 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 1 | 0 | 0 | 0 | 1 |
| total | 220 | 382227 | 370060 | 752287 | 2 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| deepseek-v4-flash | 110 | 322487 | 370060 | 692547 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen/Qwen3-Embedding-4B | 108 | 59740 | 0 | 59740 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

### image

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-vl-flash | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-05-20T23:47:15` `chat` / `deepseek-v4-flash` input=25 output=40 total=65 source=`ragent.llm.openai.openai_complete_if_cache`
2. `2026-05-20T23:47:16` `embedding` / `Qwen/Qwen3-Embedding-4B` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
3. `2026-05-20T23:47:16` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
4. `2026-05-20T23:47:17` `image` / `qwen3-vl-flash` input=0 output=0 total=0 source=`ragent.inference_runtime._image_text_ping_sync`
5. `2026-05-20T23:47:24` `embedding` / `Qwen/Qwen3-Embedding-4B` input=22 output=0 total=22 source=`ragent.llm.openai.openai_embed`
6. `2026-05-20T23:47:40` `chat` / `deepseek-v4-flash` input=2466 output=1317 total=3783 source=`ragent.llm.openai.openai_complete_if_cache`
7. `2026-05-20T23:47:57` `embedding` / `Qwen/Qwen3-Embedding-4B` input=46 output=0 total=46 source=`ragent.llm.openai.openai_embed`
8. `2026-05-20T23:48:19` `chat` / `deepseek-v4-flash` input=2486 output=1398 total=3884 source=`ragent.llm.openai.openai_complete_if_cache`
9. `2026-05-20T23:48:21` `embedding` / `Qwen/Qwen3-Embedding-4B` input=287 output=0 total=287 source=`ragent.llm.openai.openai_embed`
10. `2026-05-20T23:49:24` `chat` / `deepseek-v4-flash` input=2699 output=5466 total=8165 source=`ragent.llm.openai.openai_complete_if_cache`
11. `2026-05-20T23:49:28` `embedding` / `Qwen/Qwen3-Embedding-4B` input=24 output=0 total=24 source=`ragent.llm.openai.openai_embed`
12. `2026-05-20T23:49:45` `chat` / `deepseek-v4-flash` input=2466 output=1436 total=3902 source=`ragent.llm.openai.openai_complete_if_cache`
13. `2026-05-20T23:49:46` `embedding` / `Qwen/Qwen3-Embedding-4B` input=530 output=0 total=530 source=`ragent.llm.openai.openai_embed`
14. `2026-05-20T23:50:40` `chat` / `deepseek-v4-flash` input=2917 output=5631 total=8548 source=`ragent.llm.openai.openai_complete_if_cache`
15. `2026-05-20T23:50:41` `embedding` / `Qwen/Qwen3-Embedding-4B` input=682 output=0 total=682 source=`ragent.llm.openai.openai_embed`
16. `2026-05-20T23:51:31` `chat` / `deepseek-v4-flash` input=3060 output=4006 total=7066 source=`ragent.llm.openai.openai_complete_if_cache`
17. `2026-05-20T23:51:36` `embedding` / `Qwen/Qwen3-Embedding-4B` input=201 output=0 total=201 source=`ragent.llm.openai.openai_embed`
18. `2026-05-20T23:52:29` `chat` / `deepseek-v4-flash` input=2629 output=4611 total=7240 source=`ragent.llm.openai.openai_complete_if_cache`
19. `2026-05-20T23:52:31` `embedding` / `Qwen/Qwen3-Embedding-4B` input=976 output=0 total=976 source=`ragent.llm.openai.openai_embed`
20. `2026-05-20T23:53:20` `chat` / `deepseek-v4-flash` input=3091 output=4975 total=8066 source=`ragent.llm.openai.openai_complete_if_cache`
21. `2026-05-20T23:53:40` `chat` / `deepseek-v4-flash` input=2684 output=5035 total=7719 source=`ragent.llm.openai.openai_complete_if_cache`
22. `2026-05-20T23:53:42` `embedding` / `Qwen/Qwen3-Embedding-4B` input=592 output=0 total=592 source=`ragent.llm.openai.openai_embed`
23. `2026-05-20T23:54:38` `chat` / `deepseek-v4-flash` input=2996 output=5022 total=8018 source=`ragent.llm.openai.openai_complete_if_cache`
24. `2026-05-20T23:54:39` `embedding` / `Qwen/Qwen3-Embedding-4B` input=645 output=0 total=645 source=`ragent.llm.openai.openai_embed`
25. `2026-05-20T23:55:16` `chat` / `deepseek-v4-flash` input=3032 output=3954 total=6986 source=`ragent.llm.openai.openai_complete_if_cache`
26. `2026-05-20T23:55:18` `embedding` / `Qwen/Qwen3-Embedding-4B` input=400 output=0 total=400 source=`ragent.llm.openai.openai_embed`
27. `2026-05-20T23:55:58` `chat` / `deepseek-v4-flash` input=2824 output=3806 total=6630 source=`ragent.llm.openai.openai_complete_if_cache`
28. `2026-05-20T23:56:00` `embedding` / `Qwen/Qwen3-Embedding-4B` input=700 output=0 total=700 source=`ragent.llm.openai.openai_embed`
29. `2026-05-20T23:56:59` `chat` / `deepseek-v4-flash` input=3056 output=5948 total=9004 source=`ragent.llm.openai.openai_complete_if_cache`
30. `2026-05-20T23:57:01` `embedding` / `Qwen/Qwen3-Embedding-4B` input=539 output=0 total=539 source=`ragent.llm.openai.openai_embed`
31. `2026-05-20T23:57:47` `chat` / `deepseek-v4-flash` input=2988 output=3260 total=6248 source=`ragent.llm.openai.openai_complete_if_cache`
32. `2026-05-20T23:57:49` `embedding` / `Qwen/Qwen3-Embedding-4B` input=76 output=0 total=76 source=`ragent.llm.openai.openai_embed`
33. `2026-05-20T23:58:18` `chat` / `deepseek-v4-flash` input=2505 output=2667 total=5172 source=`ragent.llm.openai.openai_complete_if_cache`
34. `2026-05-20T23:58:21` `embedding` / `Qwen/Qwen3-Embedding-4B` input=709 output=0 total=709 source=`ragent.llm.openai.openai_embed`
35. `2026-05-20T23:58:49` `chat` / `deepseek-v4-flash` input=3151 output=2496 total=5647 source=`ragent.llm.openai.openai_complete_if_cache`
36. `2026-05-20T23:58:51` `embedding` / `Qwen/Qwen3-Embedding-4B` input=812 output=0 total=812 source=`ragent.llm.openai.openai_embed`
37. `2026-05-20T23:59:33` `chat` / `deepseek-v4-flash` input=3240 output=3518 total=6758 source=`ragent.llm.openai.openai_complete_if_cache`
38. `2026-05-20T23:59:34` `embedding` / `Qwen/Qwen3-Embedding-4B` input=599 output=0 total=599 source=`ragent.llm.openai.openai_embed`
39. `2026-05-21T00:00:31` `chat` / `deepseek-v4-flash` input=3028 output=5055 total=8083 source=`ragent.llm.openai.openai_complete_if_cache`
40. `2026-05-21T00:00:35` `embedding` / `Qwen/Qwen3-Embedding-4B` input=879 output=0 total=879 source=`ragent.llm.openai.openai_embed`
41. `2026-05-21T00:01:17` `chat` / `deepseek-v4-flash` input=3325 output=4626 total=7951 source=`ragent.llm.openai.openai_complete_if_cache`
42. `2026-05-21T00:01:20` `embedding` / `Qwen/Qwen3-Embedding-4B` input=169 output=0 total=169 source=`ragent.llm.openai.openai_embed`
43. `2026-05-21T00:01:41` `chat` / `deepseek-v4-flash` input=2601 output=1975 total=4576 source=`ragent.llm.openai.openai_complete_if_cache`
44. `2026-05-21T00:01:44` `embedding` / `Qwen/Qwen3-Embedding-4B` input=417 output=0 total=417 source=`ragent.llm.openai.openai_embed`
45. `2026-05-21T00:02:21` `chat` / `deepseek-v4-flash` input=2865 output=3137 total=6002 source=`ragent.llm.openai.openai_complete_if_cache`
46. `2026-05-21T00:02:23` `embedding` / `Qwen/Qwen3-Embedding-4B` input=402 output=0 total=402 source=`ragent.llm.openai.openai_embed`
47. `2026-05-21T00:02:53` `chat` / `deepseek-v4-flash` input=2845 output=2425 total=5270 source=`ragent.llm.openai.openai_complete_if_cache`
48. `2026-05-21T00:02:54` `embedding` / `Qwen/Qwen3-Embedding-4B` input=305 output=0 total=305 source=`ragent.llm.openai.openai_embed`
49. `2026-05-21T00:03:16` `chat` / `deepseek-v4-flash` input=2750 output=2037 total=4787 source=`ragent.llm.openai.openai_complete_if_cache`
50. `2026-05-21T00:03:18` `embedding` / `Qwen/Qwen3-Embedding-4B` input=385 output=0 total=385 source=`ragent.llm.openai.openai_embed`
51. `2026-05-21T00:03:44` `chat` / `deepseek-v4-flash` input=2836 output=2585 total=5421 source=`ragent.llm.openai.openai_complete_if_cache`
52. `2026-05-21T00:03:45` `embedding` / `Qwen/Qwen3-Embedding-4B` input=93 output=0 total=93 source=`ragent.llm.openai.openai_embed`
53. `2026-05-21T00:04:23` `chat` / `deepseek-v4-flash` input=2527 output=3276 total=5803 source=`ragent.llm.openai.openai_complete_if_cache`
54. `2026-05-21T00:04:24` `embedding` / `Qwen/Qwen3-Embedding-4B` input=159 output=0 total=159 source=`ragent.llm.openai.openai_embed`
55. `2026-05-21T00:04:47` `chat` / `deepseek-v4-flash` input=2592 output=2018 total=4610 source=`ragent.llm.openai.openai_complete_if_cache`
56. `2026-05-21T00:04:48` `embedding` / `Qwen/Qwen3-Embedding-4B` input=972 output=0 total=972 source=`ragent.llm.openai.openai_embed`
57. `2026-05-21T00:05:05` `chat` / `deepseek-v4-flash` input=3352 output=1588 total=4940 source=`ragent.llm.openai.openai_complete_if_cache`
58. `2026-05-21T00:05:07` `embedding` / `Qwen/Qwen3-Embedding-4B` input=957 output=0 total=957 source=`ragent.llm.openai.openai_embed`
59. `2026-05-21T00:05:17` `chat` / `deepseek-v4-flash` input=3332 output=868 total=4200 source=`ragent.llm.openai.openai_complete_if_cache`
60. `2026-05-21T00:05:18` `embedding` / `Qwen/Qwen3-Embedding-4B` input=951 output=0 total=951 source=`ragent.llm.openai.openai_embed`
61. `2026-05-21T00:05:58` `chat` / `deepseek-v4-flash` input=3326 output=3061 total=6387 source=`ragent.llm.openai.openai_complete_if_cache`
62. `2026-05-21T00:06:03` `embedding` / `Qwen/Qwen3-Embedding-4B` input=950 output=0 total=950 source=`ragent.llm.openai.openai_embed`
63. `2026-05-21T00:06:40` `chat` / `deepseek-v4-flash` input=3329 output=3448 total=6777 source=`ragent.llm.openai.openai_complete_if_cache`
64. `2026-05-21T00:06:46` `embedding` / `Qwen/Qwen3-Embedding-4B` input=901 output=0 total=901 source=`ragent.llm.openai.openai_embed`
65. `2026-05-21T00:07:11` `chat` / `deepseek-v4-flash` input=3266 output=2199 total=5465 source=`ragent.llm.openai.openai_complete_if_cache`
66. `2026-05-21T00:07:14` `embedding` / `Qwen/Qwen3-Embedding-4B` input=149 output=0 total=149 source=`ragent.llm.openai.openai_embed`
67. `2026-05-21T00:07:34` `chat` / `deepseek-v4-flash` input=2585 output=2005 total=4590 source=`ragent.llm.openai.openai_complete_if_cache`
68. `2026-05-21T00:07:40` `embedding` / `Qwen/Qwen3-Embedding-4B` input=974 output=0 total=974 source=`ragent.llm.openai.openai_embed`
69. `2026-05-21T00:07:57` `chat` / `deepseek-v4-flash` input=3354 output=1677 total=5031 source=`ragent.llm.openai.openai_complete_if_cache`
70. `2026-05-21T00:08:01` `embedding` / `Qwen/Qwen3-Embedding-4B` input=897 output=0 total=897 source=`ragent.llm.openai.openai_embed`
71. `2026-05-21T00:09:02` `chat` / `deepseek-v4-flash` input=3300 output=5887 total=9187 source=`ragent.llm.openai.openai_complete_if_cache`
72. `2026-05-21T00:09:08` `embedding` / `Qwen/Qwen3-Embedding-4B` input=913 output=0 total=913 source=`ragent.llm.openai.openai_embed`
73. `2026-05-21T00:09:43` `chat` / `deepseek-v4-flash` input=3308 output=3590 total=6898 source=`ragent.llm.openai.openai_complete_if_cache`
74. `2026-05-21T00:09:47` `embedding` / `Qwen/Qwen3-Embedding-4B` input=898 output=0 total=898 source=`ragent.llm.openai.openai_embed`
75. `2026-05-21T00:09:59` `chat` / `deepseek-v4-flash` input=3301 output=1083 total=4384 source=`ragent.llm.openai.openai_complete_if_cache`
76. `2026-05-21T00:10:04` `embedding` / `Qwen/Qwen3-Embedding-4B` input=865 output=0 total=865 source=`ragent.llm.openai.openai_embed`
77. `2026-05-21T00:10:44` `chat` / `deepseek-v4-flash` input=3266 output=3448 total=6714 source=`ragent.llm.openai.openai_complete_if_cache`
78. `2026-05-21T00:10:48` `embedding` / `Qwen/Qwen3-Embedding-4B` input=600 output=0 total=600 source=`ragent.llm.openai.openai_embed`
79. `2026-05-21T00:11:35` `chat` / `deepseek-v4-flash` input=3002 output=4721 total=7723 source=`ragent.llm.openai.openai_complete_if_cache`
80. `2026-05-21T00:11:41` `embedding` / `Qwen/Qwen3-Embedding-4B` input=150 output=0 total=150 source=`ragent.llm.openai.openai_embed`
81. `2026-05-21T00:12:03` `chat` / `deepseek-v4-flash` input=2587 output=2087 total=4674 source=`ragent.llm.openai.openai_complete_if_cache`
82. `2026-05-21T00:12:19` `embedding` / `Qwen/Qwen3-Embedding-4B` input=953 output=0 total=953 source=`ragent.llm.openai.openai_embed`
83. `2026-05-21T00:12:33` `chat` / `deepseek-v4-flash` input=3322 output=1116 total=4438 source=`ragent.llm.openai.openai_complete_if_cache`
84. `2026-05-21T00:12:37` `embedding` / `Qwen/Qwen3-Embedding-4B` input=941 output=0 total=941 source=`ragent.llm.openai.openai_embed`
85. `2026-05-21T00:13:04` `chat` / `deepseek-v4-flash` input=3336 output=2581 total=5917 source=`ragent.llm.openai.openai_complete_if_cache`
86. `2026-05-21T00:13:07` `embedding` / `Qwen/Qwen3-Embedding-4B` input=920 output=0 total=920 source=`ragent.llm.openai.openai_embed`
87. `2026-05-21T00:13:38` `chat` / `deepseek-v4-flash` input=3307 output=3220 total=6527 source=`ragent.llm.openai.openai_complete_if_cache`
88. `2026-05-21T00:13:43` `embedding` / `Qwen/Qwen3-Embedding-4B` input=896 output=0 total=896 source=`ragent.llm.openai.openai_embed`
89. `2026-05-21T00:13:56` `chat` / `deepseek-v4-flash` input=3283 output=1288 total=4571 source=`ragent.llm.openai.openai_complete_if_cache`
90. `2026-05-21T00:13:58` `embedding` / `Qwen/Qwen3-Embedding-4B` input=904 output=0 total=904 source=`ragent.llm.openai.openai_embed`
91. `2026-05-21T00:14:29` `chat` / `deepseek-v4-flash` input=3290 output=3115 total=6405 source=`ragent.llm.openai.openai_complete_if_cache`
92. `2026-05-21T00:14:30` `embedding` / `Qwen/Qwen3-Embedding-4B` input=727 output=0 total=727 source=`ragent.llm.openai.openai_embed`
93. `2026-05-21T00:15:31` `chat` / `deepseek-v4-flash` input=3132 output=5866 total=8998 source=`ragent.llm.openai.openai_complete_if_cache`
94. `2026-05-21T00:15:34` `embedding` / `Qwen/Qwen3-Embedding-4B` input=173 output=0 total=173 source=`ragent.llm.openai.openai_embed`
95. `2026-05-21T00:16:23` `chat` / `deepseek-v4-flash` input=2611 output=4094 total=6705 source=`ragent.llm.openai.openai_complete_if_cache`
96. `2026-05-21T00:16:25` `embedding` / `Qwen/Qwen3-Embedding-4B` input=983 output=0 total=983 source=`ragent.llm.openai.openai_embed`
97. `2026-05-21T00:17:03` `chat` / `deepseek-v4-flash` input=3355 output=3372 total=6727 source=`ragent.llm.openai.openai_complete_if_cache`
98. `2026-05-21T00:17:07` `embedding` / `Qwen/Qwen3-Embedding-4B` input=728 output=0 total=728 source=`ragent.llm.openai.openai_embed`
99. `2026-05-21T00:17:35` `chat` / `deepseek-v4-flash` input=3082 output=2516 total=5598 source=`ragent.llm.openai.openai_complete_if_cache`
100. `2026-05-21T00:17:45` `embedding` / `Qwen/Qwen3-Embedding-4B` input=955 output=0 total=955 source=`ragent.llm.openai.openai_embed`
101. `2026-05-21T00:17:56` `chat` / `deepseek-v4-flash` input=3345 output=1086 total=4431 source=`ragent.llm.openai.openai_complete_if_cache`
102. `2026-05-21T00:18:02` `embedding` / `Qwen/Qwen3-Embedding-4B` input=939 output=0 total=939 source=`ragent.llm.openai.openai_embed`
103. `2026-05-21T00:18:34` `chat` / `deepseek-v4-flash` input=3330 output=2657 total=5987 source=`ragent.llm.openai.openai_complete_if_cache`
104. `2026-05-21T00:18:43` `embedding` / `Qwen/Qwen3-Embedding-4B` input=916 output=0 total=916 source=`ragent.llm.openai.openai_embed`
105. `2026-05-21T00:18:59` `chat` / `deepseek-v4-flash` input=3321 output=1446 total=4767 source=`ragent.llm.openai.openai_complete_if_cache`
106. `2026-05-21T00:19:02` `embedding` / `Qwen/Qwen3-Embedding-4B` input=938 output=0 total=938 source=`ragent.llm.openai.openai_embed`
107. `2026-05-21T00:19:46` `chat` / `deepseek-v4-flash` input=3338 output=3829 total=7167 source=`ragent.llm.openai.openai_complete_if_cache`
108. `2026-05-21T00:19:50` `embedding` / `Qwen/Qwen3-Embedding-4B` input=186 output=0 total=186 source=`ragent.llm.openai.openai_embed`
109. `2026-05-21T00:20:07` `chat` / `deepseek-v4-flash` input=2617 output=1713 total=4330 source=`ragent.llm.openai.openai_complete_if_cache`
110. `2026-05-21T00:20:12` `embedding` / `Qwen/Qwen3-Embedding-4B` input=89 output=0 total=89 source=`ragent.llm.openai.openai_embed`
111. `2026-05-21T00:20:51` `chat` / `deepseek-v4-flash` input=2522 output=3612 total=6134 source=`ragent.llm.openai.openai_complete_if_cache`
112. `2026-05-21T00:21:06` `embedding` / `Qwen/Qwen3-Embedding-4B` input=187 output=0 total=187 source=`ragent.llm.openai.openai_embed`
113. `2026-05-21T00:21:29` `chat` / `deepseek-v4-flash` input=2619 output=1915 total=4534 source=`ragent.llm.openai.openai_complete_if_cache`
114. `2026-05-21T00:21:34` `embedding` / `Qwen/Qwen3-Embedding-4B` input=884 output=0 total=884 source=`ragent.llm.openai.openai_embed`
115. `2026-05-21T00:21:49` `chat` / `deepseek-v4-flash` input=3282 output=1272 total=4554 source=`ragent.llm.openai.openai_complete_if_cache`
116. `2026-05-21T00:21:50` `embedding` / `Qwen/Qwen3-Embedding-4B` input=828 output=0 total=828 source=`ragent.llm.openai.openai_embed`
117. `2026-05-21T00:22:10` `chat` / `deepseek-v4-flash` input=3220 output=1393 total=4613 source=`ragent.llm.openai.openai_complete_if_cache`
118. `2026-05-21T00:22:11` `embedding` / `Qwen/Qwen3-Embedding-4B` input=896 output=0 total=896 source=`ragent.llm.openai.openai_embed`
119. `2026-05-21T00:22:45` `chat` / `deepseek-v4-flash` input=3291 output=3046 total=6337 source=`ragent.llm.openai.openai_complete_if_cache`
120. `2026-05-21T00:22:46` `embedding` / `Qwen/Qwen3-Embedding-4B` input=943 output=0 total=943 source=`ragent.llm.openai.openai_embed`
121. `2026-05-21T00:23:24` `chat` / `deepseek-v4-flash` input=3335 output=3510 total=6845 source=`ragent.llm.openai.openai_complete_if_cache`
122. `2026-05-21T00:23:25` `embedding` / `Qwen/Qwen3-Embedding-4B` input=807 output=0 total=807 source=`ragent.llm.openai.openai_embed`
123. `2026-05-21T00:23:59` `chat` / `deepseek-v4-flash` input=3194 output=2826 total=6020 source=`ragent.llm.openai.openai_complete_if_cache`
124. `2026-05-21T00:24:00` `embedding` / `Qwen/Qwen3-Embedding-4B` input=182 output=0 total=182 source=`ragent.llm.openai.openai_embed`
125. `2026-05-21T00:24:29` `chat` / `deepseek-v4-flash` input=2620 output=2274 total=4894 source=`ragent.llm.openai.openai_complete_if_cache`
126. `2026-05-21T00:24:32` `embedding` / `Qwen/Qwen3-Embedding-4B` input=911 output=0 total=911 source=`ragent.llm.openai.openai_embed`
127. `2026-05-21T00:25:00` `chat` / `deepseek-v4-flash` input=3304 output=2648 total=5952 source=`ragent.llm.openai.openai_complete_if_cache`
128. `2026-05-21T00:25:02` `embedding` / `Qwen/Qwen3-Embedding-4B` input=866 output=0 total=866 source=`ragent.llm.openai.openai_embed`
129. `2026-05-21T00:25:56` `chat` / `deepseek-v4-flash` input=3259 output=5048 total=8307 source=`ragent.llm.openai.openai_complete_if_cache`
130. `2026-05-21T00:26:00` `embedding` / `Qwen/Qwen3-Embedding-4B` input=979 output=0 total=979 source=`ragent.llm.openai.openai_embed`
131. `2026-05-21T00:26:54` `chat` / `deepseek-v4-flash` input=3350 output=4975 total=8325 source=`ragent.llm.openai.openai_complete_if_cache`
132. `2026-05-21T00:26:58` `embedding` / `Qwen/Qwen3-Embedding-4B` input=874 output=0 total=874 source=`ragent.llm.openai.openai_embed`
133. `2026-05-21T00:27:32` `chat` / `deepseek-v4-flash` input=3277 output=3251 total=6528 source=`ragent.llm.openai.openai_complete_if_cache`
134. `2026-05-21T00:27:35` `embedding` / `Qwen/Qwen3-Embedding-4B` input=938 output=0 total=938 source=`ragent.llm.openai.openai_embed`
135. `2026-05-21T00:28:01` `chat` / `deepseek-v4-flash` input=3316 output=2155 total=5471 source=`ragent.llm.openai.openai_complete_if_cache`
136. `2026-05-21T00:28:06` `embedding` / `Qwen/Qwen3-Embedding-4B` input=944 output=0 total=944 source=`ragent.llm.openai.openai_embed`
137. `2026-05-21T00:29:11` `chat` / `deepseek-v4-flash` input=3315 output=6320 total=9635 source=`ragent.llm.openai.openai_complete_if_cache`
138. `2026-05-21T00:29:15` `embedding` / `Qwen/Qwen3-Embedding-4B` input=869 output=0 total=869 source=`ragent.llm.openai.openai_embed`
139. `2026-05-21T00:29:39` `chat` / `deepseek-v4-flash` input=3272 output=2293 total=5565 source=`ragent.llm.openai.openai_complete_if_cache`
140. `2026-05-21T00:29:45` `embedding` / `Qwen/Qwen3-Embedding-4B` input=703 output=0 total=703 source=`ragent.llm.openai.openai_embed`
141. `2026-05-21T00:30:03` `chat` / `deepseek-v4-flash` input=3100 output=1805 total=4905 source=`ragent.llm.openai.openai_complete_if_cache`
142. `2026-05-21T00:30:09` `embedding` / `Qwen/Qwen3-Embedding-4B` input=158 output=0 total=158 source=`ragent.llm.openai.openai_embed`
143. `2026-05-21T00:30:45` `chat` / `deepseek-v4-flash` input=2594 output=3621 total=6215 source=`ragent.llm.openai.openai_complete_if_cache`
144. `2026-05-21T00:30:53` `embedding` / `Qwen/Qwen3-Embedding-4B` input=1004 output=0 total=1004 source=`ragent.llm.openai.openai_embed`
145. `2026-05-21T00:31:16` `chat` / `deepseek-v4-flash` input=3371 output=2069 total=5440 source=`ragent.llm.openai.openai_complete_if_cache`
146. `2026-05-21T00:31:22` `embedding` / `Qwen/Qwen3-Embedding-4B` input=1006 output=0 total=1006 source=`ragent.llm.openai.openai_embed`
147. `2026-05-21T00:31:51` `chat` / `deepseek-v4-flash` input=3366 output=2539 total=5905 source=`ragent.llm.openai.openai_complete_if_cache`
148. `2026-05-21T00:31:55` `embedding` / `Qwen/Qwen3-Embedding-4B` input=874 output=0 total=874 source=`ragent.llm.openai.openai_embed`
149. `2026-05-21T00:32:12` `chat` / `deepseek-v4-flash` input=3277 output=1653 total=4930 source=`ragent.llm.openai.openai_complete_if_cache`
150. `2026-05-21T00:32:23` `embedding` / `Qwen/Qwen3-Embedding-4B` input=981 output=0 total=981 source=`ragent.llm.openai.openai_embed`
151. `2026-05-21T00:32:41` `chat` / `deepseek-v4-flash` input=3377 output=1895 total=5272 source=`ragent.llm.openai.openai_complete_if_cache`
152. `2026-05-21T00:32:56` `embedding` / `Qwen/Qwen3-Embedding-4B` input=952 output=0 total=952 source=`ragent.llm.openai.openai_embed`
153. `2026-05-21T00:33:29` `chat` / `deepseek-v4-flash` input=3329 output=3084 total=6413 source=`ragent.llm.openai.openai_complete_if_cache`
154. `2026-05-21T00:33:35` `embedding` / `Qwen/Qwen3-Embedding-4B` input=845 output=0 total=845 source=`ragent.llm.openai.openai_embed`
155. `2026-05-21T00:33:55` `chat` / `deepseek-v4-flash` input=3231 output=1867 total=5098 source=`ragent.llm.openai.openai_complete_if_cache`
156. `2026-05-21T00:33:57` `embedding` / `Qwen/Qwen3-Embedding-4B` input=36 output=0 total=36 source=`ragent.llm.openai.openai_embed`
157. `2026-05-21T00:34:17` `chat` / `deepseek-v4-flash` input=2477 output=1710 total=4187 source=`ragent.llm.openai.openai_complete_if_cache`
158. `2026-05-21T00:34:19` `embedding` / `Qwen/Qwen3-Embedding-4B` input=136 output=0 total=136 source=`ragent.llm.openai.openai_embed`
159. `2026-05-21T00:34:33` `chat` / `deepseek-v4-flash` input=2560 output=1402 total=3962 source=`ragent.llm.openai.openai_complete_if_cache`
160. `2026-05-21T00:34:34` `embedding` / `Qwen/Qwen3-Embedding-4B` input=109 output=0 total=109 source=`ragent.llm.openai.openai_embed`
161. `2026-05-21T00:34:59` `chat` / `deepseek-v4-flash` input=2544 output=2310 total=4854 source=`ragent.llm.openai.openai_complete_if_cache`
162. `2026-05-21T00:35:00` `embedding` / `Qwen/Qwen3-Embedding-4B` input=176 output=0 total=176 source=`ragent.llm.openai.openai_embed`
163. `2026-05-21T00:35:28` `chat` / `deepseek-v4-flash` input=2600 output=2422 total=5022 source=`ragent.llm.openai.openai_complete_if_cache`
164. `2026-05-21T00:35:31` `embedding` / `Qwen/Qwen3-Embedding-4B` input=130 output=0 total=130 source=`ragent.llm.openai.openai_embed`
165. `2026-05-21T00:35:47` `chat` / `deepseek-v4-flash` input=2557 output=1220 total=3777 source=`ragent.llm.openai.openai_complete_if_cache`
166. `2026-05-21T00:35:50` `embedding` / `Qwen/Qwen3-Embedding-4B` input=119 output=0 total=119 source=`ragent.llm.openai.openai_embed`
167. `2026-05-21T00:36:03` `chat` / `deepseek-v4-flash` input=2556 output=1317 total=3873 source=`ragent.llm.openai.openai_complete_if_cache`
168. `2026-05-21T00:36:05` `embedding` / `Qwen/Qwen3-Embedding-4B` input=178 output=0 total=178 source=`ragent.llm.openai.openai_embed`
169. `2026-05-21T00:36:27` `chat` / `deepseek-v4-flash` input=2591 output=2374 total=4965 source=`ragent.llm.openai.openai_complete_if_cache`
170. `2026-05-21T00:36:28` `embedding` / `Qwen/Qwen3-Embedding-4B` input=155 output=0 total=155 source=`ragent.llm.openai.openai_embed`
171. `2026-05-21T00:37:06` `chat` / `deepseek-v4-flash` input=2579 output=3916 total=6495 source=`ragent.llm.openai.openai_complete_if_cache`
172. `2026-05-21T00:37:07` `embedding` / `Qwen/Qwen3-Embedding-4B` input=467 output=0 total=467 source=`ragent.llm.openai.openai_embed`
173. `2026-05-21T00:37:34` `chat` / `deepseek-v4-flash` input=2895 output=2524 total=5419 source=`ragent.llm.openai.openai_complete_if_cache`
174. `2026-05-21T00:37:35` `embedding` / `Qwen/Qwen3-Embedding-4B` input=48 output=0 total=48 source=`ragent.llm.openai.openai_embed`
175. `2026-05-21T00:37:56` `chat` / `deepseek-v4-flash` input=2491 output=2013 total=4504 source=`ragent.llm.openai.openai_complete_if_cache`
176. `2026-05-21T00:37:58` `embedding` / `Qwen/Qwen3-Embedding-4B` input=510 output=0 total=510 source=`ragent.llm.openai.openai_embed`
177. `2026-05-21T00:38:36` `chat` / `deepseek-v4-flash` input=2952 output=3795 total=6747 source=`ragent.llm.openai.openai_complete_if_cache`
178. `2026-05-21T00:38:38` `embedding` / `Qwen/Qwen3-Embedding-4B` input=37 output=0 total=37 source=`ragent.llm.openai.openai_embed`
179. `2026-05-21T00:39:02` `chat` / `deepseek-v4-flash` input=2479 output=1835 total=4314 source=`ragent.llm.openai.openai_complete_if_cache`
180. `2026-05-21T00:39:03` `embedding` / `Qwen/Qwen3-Embedding-4B` input=272 output=0 total=272 source=`ragent.llm.openai.openai_embed`
181. `2026-05-21T00:39:47` `chat` / `deepseek-v4-flash` input=2693 output=4339 total=7032 source=`ragent.llm.openai.openai_complete_if_cache`
182. `2026-05-21T00:39:48` `embedding` / `Qwen/Qwen3-Embedding-4B` input=571 output=0 total=571 source=`ragent.llm.openai.openai_embed`
183. `2026-05-21T00:41:25` `chat` / `deepseek-v4-flash` input=2976 output=10568 total=13544 source=`ragent.llm.openai.openai_complete_if_cache`
184. `2026-05-21T00:41:27` `embedding` / `Qwen/Qwen3-Embedding-4B` input=544 output=0 total=544 source=`ragent.llm.openai.openai_embed`
185. `2026-05-21T00:42:26` `chat` / `deepseek-v4-flash` input=2914 output=6408 total=9322 source=`ragent.llm.openai.openai_complete_if_cache`
186. `2026-05-21T00:42:27` `embedding` / `Qwen/Qwen3-Embedding-4B` input=491 output=0 total=491 source=`ragent.llm.openai.openai_embed`
187. `2026-05-21T00:43:39` `chat` / `deepseek-v4-flash` input=2894 output=7948 total=10842 source=`ragent.llm.openai.openai_complete_if_cache`
188. `2026-05-21T00:43:41` `embedding` / `Qwen/Qwen3-Embedding-4B` input=563 output=0 total=563 source=`ragent.llm.openai.openai_embed`
189. `2026-05-21T00:44:22` `chat` / `deepseek-v4-flash` input=2955 output=4050 total=7005 source=`ragent.llm.openai.openai_complete_if_cache`
190. `2026-05-21T00:44:23` `embedding` / `Qwen/Qwen3-Embedding-4B` input=305 output=0 total=305 source=`ragent.llm.openai.openai_embed`
191. `2026-05-21T00:45:30` `chat` / `deepseek-v4-flash` input=2709 output=7159 total=9868 source=`ragent.llm.openai.openai_complete_if_cache`
192. `2026-05-21T00:45:32` `embedding` / `Qwen/Qwen3-Embedding-4B` input=59 output=0 total=59 source=`ragent.llm.openai.openai_embed`
193. `2026-05-21T00:45:53` `chat` / `deepseek-v4-flash` input=2501 output=2208 total=4709 source=`ragent.llm.openai.openai_complete_if_cache`
194. `2026-05-21T00:45:54` `embedding` / `Qwen/Qwen3-Embedding-4B` input=65 output=0 total=65 source=`ragent.llm.openai.openai_embed`
195. `2026-05-21T00:46:11` `chat` / `deepseek-v4-flash` input=2505 output=2142 total=4647 source=`ragent.llm.openai.openai_complete_if_cache`
196. `2026-05-21T00:46:13` `embedding` / `Qwen/Qwen3-Embedding-4B` input=254 output=0 total=254 source=`ragent.llm.openai.openai_embed`
197. `2026-05-21T00:46:45` `chat` / `deepseek-v4-flash` input=2681 output=3789 total=6470 source=`ragent.llm.openai.openai_complete_if_cache`
198. `2026-05-21T00:46:46` `embedding` / `Qwen/Qwen3-Embedding-4B` input=112 output=0 total=112 source=`ragent.llm.openai.openai_embed`
199. `2026-05-21T00:47:07` `chat` / `deepseek-v4-flash` input=2545 output=2519 total=5064 source=`ragent.llm.openai.openai_complete_if_cache`
200. `2026-05-21T00:47:09` `embedding` / `Qwen/Qwen3-Embedding-4B` input=70 output=0 total=70 source=`ragent.llm.openai.openai_embed`
201. `2026-05-21T00:47:25` `chat` / `deepseek-v4-flash` input=2510 output=1853 total=4363 source=`ragent.llm.openai.openai_complete_if_cache`
202. `2026-05-21T00:47:27` `embedding` / `Qwen/Qwen3-Embedding-4B` input=688 output=0 total=688 source=`ragent.llm.openai.openai_embed`
203. `2026-05-21T00:48:06` `chat` / `deepseek-v4-flash` input=3095 output=4937 total=8032 source=`ragent.llm.openai.openai_complete_if_cache`
204. `2026-05-21T00:48:08` `embedding` / `Qwen/Qwen3-Embedding-4B` input=414 output=0 total=414 source=`ragent.llm.openai.openai_embed`
205. `2026-05-21T00:48:47` `chat` / `deepseek-v4-flash` input=2828 output=4907 total=7735 source=`ragent.llm.openai.openai_complete_if_cache`
206. `2026-05-21T00:48:49` `embedding` / `Qwen/Qwen3-Embedding-4B` input=961 output=0 total=961 source=`ragent.llm.openai.openai_embed`
207. `2026-05-21T00:49:34` `chat` / `deepseek-v4-flash` input=2557 output=5378 total=7935 source=`ragent.llm.openai.openai_complete_if_cache`
208. `2026-05-21T00:50:24` `chat` / `deepseek-v4-flash` input=3136 output=11884 total=15020 source=`ragent.llm.openai.openai_complete_if_cache`
209. `2026-05-21T00:50:25` `embedding` / `Qwen/Qwen3-Embedding-4B` input=153 output=0 total=153 source=`ragent.llm.openai.openai_embed`
210. `2026-05-21T00:51:04` `chat` / `deepseek-v4-flash` input=2570 output=4905 total=7475 source=`ragent.llm.openai.openai_complete_if_cache`
211. `2026-05-21T00:51:06` `embedding` / `Qwen/Qwen3-Embedding-4B` input=347 output=0 total=347 source=`ragent.llm.openai.openai_embed`
212. `2026-05-21T00:52:12` `chat` / `deepseek-v4-flash` input=2739 output=7853 total=10592 source=`ragent.llm.openai.openai_complete_if_cache`
213. `2026-05-21T00:52:14` `embedding` / `Qwen/Qwen3-Embedding-4B` input=37 output=0 total=37 source=`ragent.llm.openai.openai_embed`
214. `2026-05-21T00:52:31` `chat` / `deepseek-v4-flash` input=2479 output=2040 total=4519 source=`ragent.llm.openai.openai_complete_if_cache`
215. `2026-05-21T00:52:32` `embedding` / `Qwen/Qwen3-Embedding-4B` input=699 output=0 total=699 source=`ragent.llm.openai.openai_embed`
216. `2026-05-21T00:53:21` `chat` / `deepseek-v4-flash` input=3172 output=6828 total=10000 source=`ragent.llm.openai.openai_complete_if_cache`
217. `2026-05-21T00:53:22` `embedding` / `Qwen/Qwen3-Embedding-4B` input=731 output=0 total=731 source=`ragent.llm.openai.openai_embed`
218. `2026-05-21T00:54:10` `chat` / `deepseek-v4-flash` input=3207 output=6158 total=9365 source=`ragent.llm.openai.openai_complete_if_cache`
219. `2026-05-21T00:54:11` `embedding` / `Qwen/Qwen3-Embedding-4B` input=585 output=0 total=585 source=`ragent.llm.openai.openai_embed`
220. `2026-05-21T00:54:51` `chat` / `deepseek-v4-flash` input=3058 output=4997 total=8055 source=`ragent.llm.openai.openai_complete_if_cache`
