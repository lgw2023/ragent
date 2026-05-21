# Model Usage Report: raw_export

- Task label: `export_md_to_raw_merge_units`
- Started at: `2026-05-20T22:35:41`
- Ended at: `2026-05-20T23:47:06`
- Metadata:
  - `pdf_file_path`: `/Volumes/SSD1/ragent/example/成人肥胖食养指南_2024.pdf`
  - `md_path`: `/Volumes/SSD1/ragent/example/成人肥胖食养指南_2024_md/txt/成人肥胖食养指南_2024.md`
  - `output`: `/Volumes/SSD1/ragent/example/qwen4b_diet_kg_raw_units/成人肥胖食养指南_2024.raw-units.jsonl`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 108 | 324259 | 350374 | 674633 | 0 |
| embedding | 108 | 67736 | 0 | 67736 | 0 |
| rerank | 1 | 0 | 0 | 0 | 1 |
| image | 1 | 0 | 0 | 0 | 1 |
| total | 218 | 391995 | 350374 | 742369 | 2 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| deepseek-v4-flash | 108 | 324259 | 350374 | 674633 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen/Qwen3-Embedding-4B | 108 | 67736 | 0 | 67736 | 0 |

### rerank

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-rerank | 1 | 0 | 0 | 0 | 1 |

### image

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-vl-flash | 1 | 0 | 0 | 0 | 1 |

## Call Events

1. `2026-05-20T22:35:42` `chat` / `deepseek-v4-flash` input=25 output=40 total=65 source=`ragent.llm.openai.openai_complete_if_cache`
2. `2026-05-20T22:35:43` `embedding` / `Qwen/Qwen3-Embedding-4B` input=13 output=0 total=13 source=`ragent.llm.openai.openai_embed`
3. `2026-05-20T22:35:44` `rerank` / `qwen3-rerank` input=0 output=0 total=0 source=`ragent.rerank.rerank_api`
4. `2026-05-20T22:35:44` `image` / `qwen3-vl-flash` input=0 output=0 total=0 source=`ragent.inference_runtime._image_text_ping_sync`
5. `2026-05-20T22:35:46` `embedding` / `Qwen/Qwen3-Embedding-4B` input=32 output=0 total=32 source=`ragent.llm.openai.openai_embed`
6. `2026-05-20T22:36:00` `chat` / `deepseek-v4-flash` input=2472 output=1141 total=3613 source=`ragent.llm.openai.openai_complete_if_cache`
7. `2026-05-20T22:36:02` `embedding` / `Qwen/Qwen3-Embedding-4B` input=338 output=0 total=338 source=`ragent.llm.openai.openai_embed`
8. `2026-05-20T22:36:24` `chat` / `deepseek-v4-flash` input=2750 output=2285 total=5035 source=`ragent.llm.openai.openai_complete_if_cache`
9. `2026-05-20T22:36:25` `embedding` / `Qwen/Qwen3-Embedding-4B` input=502 output=0 total=502 source=`ragent.llm.openai.openai_embed`
10. `2026-05-20T22:37:18` `chat` / `deepseek-v4-flash` input=2892 output=4954 total=7846 source=`ragent.llm.openai.openai_complete_if_cache`
11. `2026-05-20T22:37:20` `embedding` / `Qwen/Qwen3-Embedding-4B` input=229 output=0 total=229 source=`ragent.llm.openai.openai_embed`
12. `2026-05-20T22:37:48` `chat` / `deepseek-v4-flash` input=2649 output=2537 total=5186 source=`ragent.llm.openai.openai_complete_if_cache`
13. `2026-05-20T22:37:50` `embedding` / `Qwen/Qwen3-Embedding-4B` input=758 output=0 total=758 source=`ragent.llm.openai.openai_embed`
14. `2026-05-20T22:38:38` `chat` / `deepseek-v4-flash` input=3136 output=4412 total=7548 source=`ragent.llm.openai.openai_complete_if_cache`
15. `2026-05-20T22:38:42` `embedding` / `Qwen/Qwen3-Embedding-4B` input=263 output=0 total=263 source=`ragent.llm.openai.openai_embed`
16. `2026-05-20T22:38:55` `chat` / `deepseek-v4-flash` input=2691 output=1183 total=3874 source=`ragent.llm.openai.openai_complete_if_cache`
17. `2026-05-20T22:38:57` `embedding` / `Qwen/Qwen3-Embedding-4B` input=153 output=0 total=153 source=`ragent.llm.openai.openai_embed`
18. `2026-05-20T22:39:32` `chat` / `deepseek-v4-flash` input=2589 output=3086 total=5675 source=`ragent.llm.openai.openai_complete_if_cache`
19. `2026-05-20T22:39:33` `embedding` / `Qwen/Qwen3-Embedding-4B` input=637 output=0 total=637 source=`ragent.llm.openai.openai_embed`
20. `2026-05-20T22:40:28` `chat` / `deepseek-v4-flash` input=3005 output=4703 total=7708 source=`ragent.llm.openai.openai_complete_if_cache`
21. `2026-05-20T22:40:30` `embedding` / `Qwen/Qwen3-Embedding-4B` input=565 output=0 total=565 source=`ragent.llm.openai.openai_embed`
22. `2026-05-20T22:41:02` `chat` / `deepseek-v4-flash` input=2932 output=2969 total=5901 source=`ragent.llm.openai.openai_complete_if_cache`
23. `2026-05-20T22:41:03` `embedding` / `Qwen/Qwen3-Embedding-4B` input=190 output=0 total=190 source=`ragent.llm.openai.openai_embed`
24. `2026-05-20T22:41:46` `chat` / `deepseek-v4-flash` input=2602 output=4036 total=6638 source=`ragent.llm.openai.openai_complete_if_cache`
25. `2026-05-20T22:41:48` `embedding` / `Qwen/Qwen3-Embedding-4B` input=508 output=0 total=508 source=`ragent.llm.openai.openai_embed`
26. `2026-05-20T22:43:28` `chat` / `deepseek-v4-flash` input=2908 output=9351 total=12259 source=`ragent.llm.openai.openai_complete_if_cache`
27. `2026-05-20T22:43:35` `embedding` / `Qwen/Qwen3-Embedding-4B` input=542 output=0 total=542 source=`ragent.llm.openai.openai_embed`
28. `2026-05-20T22:44:19` `chat` / `deepseek-v4-flash` input=2935 output=4095 total=7030 source=`ragent.llm.openai.openai_complete_if_cache`
29. `2026-05-20T22:44:20` `embedding` / `Qwen/Qwen3-Embedding-4B` input=535 output=0 total=535 source=`ragent.llm.openai.openai_embed`
30. `2026-05-20T22:45:32` `chat` / `deepseek-v4-flash` input=2934 output=6563 total=9497 source=`ragent.llm.openai.openai_complete_if_cache`
31. `2026-05-20T22:45:34` `embedding` / `Qwen/Qwen3-Embedding-4B` input=140 output=0 total=140 source=`ragent.llm.openai.openai_embed`
32. `2026-05-20T22:46:17` `chat` / `deepseek-v4-flash` input=2568 output=3774 total=6342 source=`ragent.llm.openai.openai_complete_if_cache`
33. `2026-05-20T22:46:19` `embedding` / `Qwen/Qwen3-Embedding-4B` input=636 output=0 total=636 source=`ragent.llm.openai.openai_embed`
34. `2026-05-20T22:47:19` `chat` / `deepseek-v4-flash` input=3017 output=5046 total=8063 source=`ragent.llm.openai.openai_complete_if_cache`
35. `2026-05-20T22:47:21` `embedding` / `Qwen/Qwen3-Embedding-4B` input=337 output=0 total=337 source=`ragent.llm.openai.openai_embed`
36. `2026-05-20T22:48:20` `chat` / `deepseek-v4-flash` input=2750 output=3831 total=6581 source=`ragent.llm.openai.openai_complete_if_cache`
37. `2026-05-20T22:48:23` `embedding` / `Qwen/Qwen3-Embedding-4B` input=756 output=0 total=756 source=`ragent.llm.openai.openai_embed`
38. `2026-05-20T22:49:11` `chat` / `deepseek-v4-flash` input=3198 output=3304 total=6502 source=`ragent.llm.openai.openai_complete_if_cache`
39. `2026-05-20T22:49:13` `embedding` / `Qwen/Qwen3-Embedding-4B` input=476 output=0 total=476 source=`ragent.llm.openai.openai_embed`
40. `2026-05-20T22:49:53` `chat` / `deepseek-v4-flash` input=2931 output=3353 total=6284 source=`ragent.llm.openai.openai_complete_if_cache`
41. `2026-05-20T22:49:55` `embedding` / `Qwen/Qwen3-Embedding-4B` input=396 output=0 total=396 source=`ragent.llm.openai.openai_embed`
42. `2026-05-20T22:50:24` `chat` / `deepseek-v4-flash` input=2835 output=2959 total=5794 source=`ragent.llm.openai.openai_complete_if_cache`
43. `2026-05-20T22:50:26` `embedding` / `Qwen/Qwen3-Embedding-4B` input=95 output=0 total=95 source=`ragent.llm.openai.openai_embed`
44. `2026-05-20T22:50:46` `chat` / `deepseek-v4-flash` input=2525 output=1764 total=4289 source=`ragent.llm.openai.openai_complete_if_cache`
45. `2026-05-20T22:50:48` `embedding` / `Qwen/Qwen3-Embedding-4B` input=774 output=0 total=774 source=`ragent.llm.openai.openai_embed`
46. `2026-05-20T22:51:42` `chat` / `deepseek-v4-flash` input=3234 output=4699 total=7933 source=`ragent.llm.openai.openai_complete_if_cache`
47. `2026-05-20T22:51:45` `embedding` / `Qwen/Qwen3-Embedding-4B` input=489 output=0 total=489 source=`ragent.llm.openai.openai_embed`
48. `2026-05-20T22:52:27` `chat` / `deepseek-v4-flash` input=2937 output=3643 total=6580 source=`ragent.llm.openai.openai_complete_if_cache`
49. `2026-05-20T22:52:28` `embedding` / `Qwen/Qwen3-Embedding-4B` input=799 output=0 total=799 source=`ragent.llm.openai.openai_embed`
50. `2026-05-20T22:53:08` `chat` / `deepseek-v4-flash` input=3249 output=3128 total=6377 source=`ragent.llm.openai.openai_complete_if_cache`
51. `2026-05-20T22:53:09` `embedding` / `Qwen/Qwen3-Embedding-4B` input=541 output=0 total=541 source=`ragent.llm.openai.openai_embed`
52. `2026-05-20T22:53:35` `chat` / `deepseek-v4-flash` input=2988 output=2282 total=5270 source=`ragent.llm.openai.openai_complete_if_cache`
53. `2026-05-20T22:53:37` `embedding` / `Qwen/Qwen3-Embedding-4B` input=781 output=0 total=781 source=`ragent.llm.openai.openai_embed`
54. `2026-05-20T22:54:34` `chat` / `deepseek-v4-flash` input=3228 output=5207 total=8435 source=`ragent.llm.openai.openai_complete_if_cache`
55. `2026-05-20T22:54:36` `embedding` / `Qwen/Qwen3-Embedding-4B` input=270 output=0 total=270 source=`ragent.llm.openai.openai_embed`
56. `2026-05-20T22:55:05` `chat` / `deepseek-v4-flash` input=2714 output=2623 total=5337 source=`ragent.llm.openai.openai_complete_if_cache`
57. `2026-05-20T22:55:07` `embedding` / `Qwen/Qwen3-Embedding-4B` input=856 output=0 total=856 source=`ragent.llm.openai.openai_embed`
58. `2026-05-20T22:56:02` `chat` / `deepseek-v4-flash` input=3317 output=5211 total=8528 source=`ragent.llm.openai.openai_complete_if_cache`
59. `2026-05-20T22:56:04` `embedding` / `Qwen/Qwen3-Embedding-4B` input=691 output=0 total=691 source=`ragent.llm.openai.openai_embed`
60. `2026-05-20T22:57:44` `chat` / `deepseek-v4-flash` input=3144 output=7242 total=10386 source=`ragent.llm.openai.openai_complete_if_cache`
61. `2026-05-20T22:57:46` `embedding` / `Qwen/Qwen3-Embedding-4B` input=688 output=0 total=688 source=`ragent.llm.openai.openai_embed`
62. `2026-05-20T22:58:18` `chat` / `deepseek-v4-flash` input=3139 output=2917 total=6056 source=`ragent.llm.openai.openai_complete_if_cache`
63. `2026-05-20T22:58:19` `embedding` / `Qwen/Qwen3-Embedding-4B` input=801 output=0 total=801 source=`ragent.llm.openai.openai_embed`
64. `2026-05-20T22:59:16` `chat` / `deepseek-v4-flash` input=3270 output=4566 total=7836 source=`ragent.llm.openai.openai_complete_if_cache`
65. `2026-05-20T22:59:19` `embedding` / `Qwen/Qwen3-Embedding-4B` input=635 output=0 total=635 source=`ragent.llm.openai.openai_embed`
66. `2026-05-20T23:00:13` `chat` / `deepseek-v4-flash` input=3094 output=4547 total=7641 source=`ragent.llm.openai.openai_complete_if_cache`
67. `2026-05-20T23:00:14` `embedding` / `Qwen/Qwen3-Embedding-4B` input=176 output=0 total=176 source=`ragent.llm.openai.openai_embed`
68. `2026-05-20T23:00:59` `chat` / `deepseek-v4-flash` input=2595 output=4094 total=6689 source=`ragent.llm.openai.openai_complete_if_cache`
69. `2026-05-20T23:01:00` `embedding` / `Qwen/Qwen3-Embedding-4B` input=116 output=0 total=116 source=`ragent.llm.openai.openai_embed`
70. `2026-05-20T23:01:20` `chat` / `deepseek-v4-flash` input=2554 output=1725 total=4279 source=`ragent.llm.openai.openai_complete_if_cache`
71. `2026-05-20T23:01:22` `embedding` / `Qwen/Qwen3-Embedding-4B` input=933 output=0 total=933 source=`ragent.llm.openai.openai_embed`
72. `2026-05-20T23:01:36` `chat` / `deepseek-v4-flash` input=3309 output=1369 total=4678 source=`ragent.llm.openai.openai_complete_if_cache`
73. `2026-05-20T23:01:38` `embedding` / `Qwen/Qwen3-Embedding-4B` input=928 output=0 total=928 source=`ragent.llm.openai.openai_embed`
74. `2026-05-20T23:02:32` `chat` / `deepseek-v4-flash` input=3284 output=4912 total=8196 source=`ragent.llm.openai.openai_complete_if_cache`
75. `2026-05-20T23:02:34` `embedding` / `Qwen/Qwen3-Embedding-4B` input=868 output=0 total=868 source=`ragent.llm.openai.openai_embed`
76. `2026-05-20T23:03:19` `chat` / `deepseek-v4-flash` input=3241 output=3999 total=7240 source=`ragent.llm.openai.openai_complete_if_cache`
77. `2026-05-20T23:03:21` `embedding` / `Qwen/Qwen3-Embedding-4B` input=953 output=0 total=953 source=`ragent.llm.openai.openai_embed`
78. `2026-05-20T23:03:52` `chat` / `deepseek-v4-flash` input=3315 output=2518 total=5833 source=`ragent.llm.openai.openai_complete_if_cache`
79. `2026-05-20T23:04:01` `embedding` / `Qwen/Qwen3-Embedding-4B` input=934 output=0 total=934 source=`ragent.llm.openai.openai_embed`
80. `2026-05-20T23:04:36` `chat` / `deepseek-v4-flash` input=3307 output=3123 total=6430 source=`ragent.llm.openai.openai_complete_if_cache`
81. `2026-05-20T23:04:39` `embedding` / `Qwen/Qwen3-Embedding-4B` input=921 output=0 total=921 source=`ragent.llm.openai.openai_embed`
82. `2026-05-20T23:05:30` `chat` / `deepseek-v4-flash` input=3289 output=4384 total=7673 source=`ragent.llm.openai.openai_complete_if_cache`
83. `2026-05-20T23:05:32` `embedding` / `Qwen/Qwen3-Embedding-4B` input=945 output=0 total=945 source=`ragent.llm.openai.openai_embed`
84. `2026-05-20T23:05:57` `chat` / `deepseek-v4-flash` input=3323 output=2117 total=5440 source=`ragent.llm.openai.openai_complete_if_cache`
85. `2026-05-20T23:05:58` `embedding` / `Qwen/Qwen3-Embedding-4B` input=173 output=0 total=173 source=`ragent.llm.openai.openai_embed`
86. `2026-05-20T23:06:30` `chat` / `deepseek-v4-flash` input=2590 output=2151 total=4741 source=`ragent.llm.openai.openai_complete_if_cache`
87. `2026-05-20T23:06:33` `embedding` / `Qwen/Qwen3-Embedding-4B` input=142 output=0 total=142 source=`ragent.llm.openai.openai_embed`
88. `2026-05-20T23:07:18` `chat` / `deepseek-v4-flash` input=2576 output=4233 total=6809 source=`ragent.llm.openai.openai_complete_if_cache`
89. `2026-05-20T23:07:21` `embedding` / `Qwen/Qwen3-Embedding-4B` input=909 output=0 total=909 source=`ragent.llm.openai.openai_embed`
90. `2026-05-20T23:08:06` `chat` / `deepseek-v4-flash` input=3286 output=3699 total=6985 source=`ragent.llm.openai.openai_complete_if_cache`
91. `2026-05-20T23:08:08` `embedding` / `Qwen/Qwen3-Embedding-4B` input=921 output=0 total=921 source=`ragent.llm.openai.openai_embed`
92. `2026-05-20T23:08:59` `chat` / `deepseek-v4-flash` input=3277 output=4305 total=7582 source=`ragent.llm.openai.openai_complete_if_cache`
93. `2026-05-20T23:09:03` `embedding` / `Qwen/Qwen3-Embedding-4B` input=931 output=0 total=931 source=`ragent.llm.openai.openai_embed`
94. `2026-05-20T23:09:25` `chat` / `deepseek-v4-flash` input=3303 output=2120 total=5423 source=`ragent.llm.openai.openai_complete_if_cache`
95. `2026-05-20T23:09:27` `embedding` / `Qwen/Qwen3-Embedding-4B` input=951 output=0 total=951 source=`ragent.llm.openai.openai_embed`
96. `2026-05-20T23:09:59` `chat` / `deepseek-v4-flash` input=3314 output=3339 total=6653 source=`ragent.llm.openai.openai_complete_if_cache`
97. `2026-05-20T23:10:00` `embedding` / `Qwen/Qwen3-Embedding-4B` input=916 output=0 total=916 source=`ragent.llm.openai.openai_embed`
98. `2026-05-20T23:10:20` `chat` / `deepseek-v4-flash` input=3278 output=1982 total=5260 source=`ragent.llm.openai.openai_complete_if_cache`
99. `2026-05-20T23:10:21` `embedding` / `Qwen/Qwen3-Embedding-4B` input=911 output=0 total=911 source=`ragent.llm.openai.openai_embed`
100. `2026-05-20T23:10:50` `chat` / `deepseek-v4-flash` input=3283 output=2589 total=5872 source=`ragent.llm.openai.openai_complete_if_cache`
101. `2026-05-20T23:10:53` `embedding` / `Qwen/Qwen3-Embedding-4B` input=870 output=0 total=870 source=`ragent.llm.openai.openai_embed`
102. `2026-05-20T23:11:34` `chat` / `deepseek-v4-flash` input=3230 output=3891 total=7121 source=`ragent.llm.openai.openai_complete_if_cache`
103. `2026-05-20T23:11:36` `embedding` / `Qwen/Qwen3-Embedding-4B` input=618 output=0 total=618 source=`ragent.llm.openai.openai_embed`
104. `2026-05-20T23:11:58` `chat` / `deepseek-v4-flash` input=3016 output=2201 total=5217 source=`ragent.llm.openai.openai_complete_if_cache`
105. `2026-05-20T23:11:59` `embedding` / `Qwen/Qwen3-Embedding-4B` input=126 output=0 total=126 source=`ragent.llm.openai.openai_embed`
106. `2026-05-20T23:12:43` `chat` / `deepseek-v4-flash` input=2563 output=3413 total=5976 source=`ragent.llm.openai.openai_complete_if_cache`
107. `2026-05-20T23:12:44` `embedding` / `Qwen/Qwen3-Embedding-4B` input=964 output=0 total=964 source=`ragent.llm.openai.openai_embed`
108. `2026-05-20T23:13:03` `chat` / `deepseek-v4-flash` input=3318 output=1634 total=4952 source=`ragent.llm.openai.openai_complete_if_cache`
109. `2026-05-20T23:13:04` `embedding` / `Qwen/Qwen3-Embedding-4B` input=966 output=0 total=966 source=`ragent.llm.openai.openai_embed`
110. `2026-05-20T23:13:54` `chat` / `deepseek-v4-flash` input=3308 output=5142 total=8450 source=`ragent.llm.openai.openai_complete_if_cache`
111. `2026-05-20T23:13:56` `embedding` / `Qwen/Qwen3-Embedding-4B` input=919 output=0 total=919 source=`ragent.llm.openai.openai_embed`
112. `2026-05-20T23:14:43` `chat` / `deepseek-v4-flash` input=3286 output=3955 total=7241 source=`ragent.llm.openai.openai_complete_if_cache`
113. `2026-05-20T23:14:45` `embedding` / `Qwen/Qwen3-Embedding-4B` input=952 output=0 total=952 source=`ragent.llm.openai.openai_embed`
114. `2026-05-20T23:15:12` `chat` / `deepseek-v4-flash` input=3315 output=2799 total=6114 source=`ragent.llm.openai.openai_complete_if_cache`
115. `2026-05-20T23:15:15` `embedding` / `Qwen/Qwen3-Embedding-4B` input=984 output=0 total=984 source=`ragent.llm.openai.openai_embed`
116. `2026-05-20T23:15:46` `chat` / `deepseek-v4-flash` input=3336 output=3019 total=6355 source=`ragent.llm.openai.openai_complete_if_cache`
117. `2026-05-20T23:15:49` `embedding` / `Qwen/Qwen3-Embedding-4B` input=910 output=0 total=910 source=`ragent.llm.openai.openai_embed`
118. `2026-05-20T23:16:22` `chat` / `deepseek-v4-flash` input=3264 output=3563 total=6827 source=`ragent.llm.openai.openai_complete_if_cache`
119. `2026-05-20T23:16:25` `embedding` / `Qwen/Qwen3-Embedding-4B` input=948 output=0 total=948 source=`ragent.llm.openai.openai_embed`
120. `2026-05-20T23:16:46` `chat` / `deepseek-v4-flash` input=3294 output=1952 total=5246 source=`ragent.llm.openai.openai_complete_if_cache`
121. `2026-05-20T23:16:48` `embedding` / `Qwen/Qwen3-Embedding-4B` input=180 output=0 total=180 source=`ragent.llm.openai.openai_embed`
122. `2026-05-20T23:17:09` `chat` / `deepseek-v4-flash` input=2596 output=2184 total=4780 source=`ragent.llm.openai.openai_complete_if_cache`
123. `2026-05-20T23:17:12` `embedding` / `Qwen/Qwen3-Embedding-4B` input=114 output=0 total=114 source=`ragent.llm.openai.openai_embed`
124. `2026-05-20T23:17:37` `chat` / `deepseek-v4-flash` input=2551 output=2069 total=4620 source=`ragent.llm.openai.openai_complete_if_cache`
125. `2026-05-20T23:17:38` `embedding` / `Qwen/Qwen3-Embedding-4B` input=940 output=0 total=940 source=`ragent.llm.openai.openai_embed`
126. `2026-05-20T23:18:24` `chat` / `deepseek-v4-flash` input=3320 output=2011 total=5331 source=`ragent.llm.openai.openai_complete_if_cache`
127. `2026-05-20T23:18:25` `embedding` / `Qwen/Qwen3-Embedding-4B` input=974 output=0 total=974 source=`ragent.llm.openai.openai_embed`
128. `2026-05-20T23:18:52` `chat` / `deepseek-v4-flash` input=3340 output=2342 total=5682 source=`ragent.llm.openai.openai_complete_if_cache`
129. `2026-05-20T23:18:54` `embedding` / `Qwen/Qwen3-Embedding-4B` input=1019 output=0 total=1019 source=`ragent.llm.openai.openai_embed`
130. `2026-05-20T23:19:54` `chat` / `deepseek-v4-flash` input=3350 output=5573 total=8923 source=`ragent.llm.openai.openai_complete_if_cache`
131. `2026-05-20T23:20:01` `embedding` / `Qwen/Qwen3-Embedding-4B` input=1019 output=0 total=1019 source=`ragent.llm.openai.openai_embed`
132. `2026-05-20T23:20:47` `chat` / `deepseek-v4-flash` input=3347 output=4425 total=7772 source=`ragent.llm.openai.openai_complete_if_cache`
133. `2026-05-20T23:20:48` `embedding` / `Qwen/Qwen3-Embedding-4B` input=920 output=0 total=920 source=`ragent.llm.openai.openai_embed`
134. `2026-05-20T23:21:39` `chat` / `deepseek-v4-flash` input=3299 output=5105 total=8404 source=`ragent.llm.openai.openai_complete_if_cache`
135. `2026-05-20T23:21:41` `embedding` / `Qwen/Qwen3-Embedding-4B` input=896 output=0 total=896 source=`ragent.llm.openai.openai_embed`
136. `2026-05-20T23:22:15` `chat` / `deepseek-v4-flash` input=3265 output=3105 total=6370 source=`ragent.llm.openai.openai_complete_if_cache`
137. `2026-05-20T23:22:17` `embedding` / `Qwen/Qwen3-Embedding-4B` input=997 output=0 total=997 source=`ragent.llm.openai.openai_embed`
138. `2026-05-20T23:22:38` `chat` / `deepseek-v4-flash` input=3374 output=2219 total=5593 source=`ragent.llm.openai.openai_complete_if_cache`
139. `2026-05-20T23:22:39` `embedding` / `Qwen/Qwen3-Embedding-4B` input=859 output=0 total=859 source=`ragent.llm.openai.openai_embed`
140. `2026-05-20T23:22:58` `chat` / `deepseek-v4-flash` input=3224 output=1336 total=4560 source=`ragent.llm.openai.openai_complete_if_cache`
141. `2026-05-20T23:23:02` `embedding` / `Qwen/Qwen3-Embedding-4B` input=112 output=0 total=112 source=`ragent.llm.openai.openai_embed`
142. `2026-05-20T23:23:27` `chat` / `deepseek-v4-flash` input=2545 output=2046 total=4591 source=`ragent.llm.openai.openai_complete_if_cache`
143. `2026-05-20T23:23:48` `embedding` / `Qwen/Qwen3-Embedding-4B` input=924 output=0 total=924 source=`ragent.llm.openai.openai_embed`
144. `2026-05-20T23:24:07` `chat` / `deepseek-v4-flash` input=3296 output=1805 total=5101 source=`ragent.llm.openai.openai_complete_if_cache`
145. `2026-05-20T23:24:12` `embedding` / `Qwen/Qwen3-Embedding-4B` input=911 output=0 total=911 source=`ragent.llm.openai.openai_embed`
146. `2026-05-20T23:24:27` `chat` / `deepseek-v4-flash` input=3267 output=1361 total=4628 source=`ragent.llm.openai.openai_complete_if_cache`
147. `2026-05-20T23:24:29` `embedding` / `Qwen/Qwen3-Embedding-4B` input=870 output=0 total=870 source=`ragent.llm.openai.openai_embed`
148. `2026-05-20T23:24:41` `chat` / `deepseek-v4-flash` input=3237 output=1063 total=4300 source=`ragent.llm.openai.openai_complete_if_cache`
149. `2026-05-20T23:24:43` `embedding` / `Qwen/Qwen3-Embedding-4B` input=963 output=0 total=963 source=`ragent.llm.openai.openai_embed`
150. `2026-05-20T23:25:03` `chat` / `deepseek-v4-flash` input=3334 output=1729 total=5063 source=`ragent.llm.openai.openai_complete_if_cache`
151. `2026-05-20T23:25:04` `embedding` / `Qwen/Qwen3-Embedding-4B` input=925 output=0 total=925 source=`ragent.llm.openai.openai_embed`
152. `2026-05-20T23:25:19` `chat` / `deepseek-v4-flash` input=3284 output=1515 total=4799 source=`ragent.llm.openai.openai_complete_if_cache`
153. `2026-05-20T23:25:29` `embedding` / `Qwen/Qwen3-Embedding-4B` input=873 output=0 total=873 source=`ragent.llm.openai.openai_embed`
154. `2026-05-20T23:26:02` `chat` / `deepseek-v4-flash` input=3233 output=3130 total=6363 source=`ragent.llm.openai.openai_complete_if_cache`
155. `2026-05-20T23:26:13` `embedding` / `Qwen/Qwen3-Embedding-4B` input=936 output=0 total=936 source=`ragent.llm.openai.openai_embed`
156. `2026-05-20T23:26:36` `chat` / `deepseek-v4-flash` input=3304 output=2277 total=5581 source=`ragent.llm.openai.openai_complete_if_cache`
157. `2026-05-20T23:26:39` `embedding` / `Qwen/Qwen3-Embedding-4B` input=130 output=0 total=130 source=`ragent.llm.openai.openai_embed`
158. `2026-05-20T23:26:59` `chat` / `deepseek-v4-flash` input=2558 output=1965 total=4523 source=`ragent.llm.openai.openai_complete_if_cache`
159. `2026-05-20T23:27:00` `embedding` / `Qwen/Qwen3-Embedding-4B` input=83 output=0 total=83 source=`ragent.llm.openai.openai_embed`
160. `2026-05-20T23:27:44` `chat` / `deepseek-v4-flash` input=2512 output=4012 total=6524 source=`ragent.llm.openai.openai_complete_if_cache`
161. `2026-05-20T23:27:45` `embedding` / `Qwen/Qwen3-Embedding-4B` input=111 output=0 total=111 source=`ragent.llm.openai.openai_embed`
162. `2026-05-20T23:28:45` `chat` / `deepseek-v4-flash` input=2548 output=5624 total=8172 source=`ragent.llm.openai.openai_complete_if_cache`
163. `2026-05-20T23:28:47` `embedding` / `Qwen/Qwen3-Embedding-4B` input=875 output=0 total=875 source=`ragent.llm.openai.openai_embed`
164. `2026-05-20T23:29:20` `chat` / `deepseek-v4-flash` input=3262 output=3146 total=6408 source=`ragent.llm.openai.openai_complete_if_cache`
165. `2026-05-20T23:29:23` `embedding` / `Qwen/Qwen3-Embedding-4B` input=931 output=0 total=931 source=`ragent.llm.openai.openai_embed`
166. `2026-05-20T23:30:50` `chat` / `deepseek-v4-flash` input=3291 output=7525 total=10816 source=`ragent.llm.openai.openai_complete_if_cache`
167. `2026-05-20T23:30:53` `embedding` / `Qwen/Qwen3-Embedding-4B` input=860 output=0 total=860 source=`ragent.llm.openai.openai_embed`
168. `2026-05-20T23:31:48` `chat` / `deepseek-v4-flash` input=3233 output=4764 total=7997 source=`ragent.llm.openai.openai_complete_if_cache`
169. `2026-05-20T23:31:49` `embedding` / `Qwen/Qwen3-Embedding-4B` input=950 output=0 total=950 source=`ragent.llm.openai.openai_embed`
170. `2026-05-20T23:32:09` `chat` / `deepseek-v4-flash` input=3305 output=1844 total=5149 source=`ragent.llm.openai.openai_complete_if_cache`
171. `2026-05-20T23:32:10` `embedding` / `Qwen/Qwen3-Embedding-4B` input=932 output=0 total=932 source=`ragent.llm.openai.openai_embed`
172. `2026-05-20T23:32:26` `chat` / `deepseek-v4-flash` input=3291 output=1516 total=4807 source=`ragent.llm.openai.openai_complete_if_cache`
173. `2026-05-20T23:32:27` `embedding` / `Qwen/Qwen3-Embedding-4B` input=956 output=0 total=956 source=`ragent.llm.openai.openai_embed`
174. `2026-05-20T23:33:24` `chat` / `deepseek-v4-flash` input=3322 output=4702 total=8024 source=`ragent.llm.openai.openai_complete_if_cache`
175. `2026-05-20T23:33:25` `embedding` / `Qwen/Qwen3-Embedding-4B` input=510 output=0 total=510 source=`ragent.llm.openai.openai_embed`
176. `2026-05-20T23:34:05` `chat` / `deepseek-v4-flash` input=2906 output=3789 total=6695 source=`ragent.llm.openai.openai_complete_if_cache`
177. `2026-05-20T23:34:06` `embedding` / `Qwen/Qwen3-Embedding-4B` input=114 output=0 total=114 source=`ragent.llm.openai.openai_embed`
178. `2026-05-20T23:34:45` `chat` / `deepseek-v4-flash` input=2551 output=2977 total=5528 source=`ragent.llm.openai.openai_complete_if_cache`
179. `2026-05-20T23:34:47` `embedding` / `Qwen/Qwen3-Embedding-4B` input=919 output=0 total=919 source=`ragent.llm.openai.openai_embed`
180. `2026-05-20T23:35:19` `chat` / `deepseek-v4-flash` input=3287 output=2158 total=5445 source=`ragent.llm.openai.openai_complete_if_cache`
181. `2026-05-20T23:35:21` `embedding` / `Qwen/Qwen3-Embedding-4B` input=860 output=0 total=860 source=`ragent.llm.openai.openai_embed`
182. `2026-05-20T23:35:57` `chat` / `deepseek-v4-flash` input=3223 output=3141 total=6364 source=`ragent.llm.openai.openai_complete_if_cache`
183. `2026-05-20T23:35:59` `embedding` / `Qwen/Qwen3-Embedding-4B` input=940 output=0 total=940 source=`ragent.llm.openai.openai_embed`
184. `2026-05-20T23:36:21` `chat` / `deepseek-v4-flash` input=3299 output=1904 total=5203 source=`ragent.llm.openai.openai_complete_if_cache`
185. `2026-05-20T23:36:23` `embedding` / `Qwen/Qwen3-Embedding-4B` input=912 output=0 total=912 source=`ragent.llm.openai.openai_embed`
186. `2026-05-20T23:37:03` `chat` / `deepseek-v4-flash` input=3288 output=3403 total=6691 source=`ragent.llm.openai.openai_complete_if_cache`
187. `2026-05-20T23:37:07` `embedding` / `Qwen/Qwen3-Embedding-4B` input=886 output=0 total=886 source=`ragent.llm.openai.openai_embed`
188. `2026-05-20T23:37:33` `chat` / `deepseek-v4-flash` input=3241 output=2027 total=5268 source=`ragent.llm.openai.openai_complete_if_cache`
189. `2026-05-20T23:37:36` `embedding` / `Qwen/Qwen3-Embedding-4B` input=919 output=0 total=919 source=`ragent.llm.openai.openai_embed`
190. `2026-05-20T23:38:26` `chat` / `deepseek-v4-flash` input=3276 output=3907 total=7183 source=`ragent.llm.openai.openai_complete_if_cache`
191. `2026-05-20T23:38:28` `embedding` / `Qwen/Qwen3-Embedding-4B` input=931 output=0 total=931 source=`ragent.llm.openai.openai_embed`
192. `2026-05-20T23:38:52` `chat` / `deepseek-v4-flash` input=3295 output=2086 total=5381 source=`ragent.llm.openai.openai_complete_if_cache`
193. `2026-05-20T23:38:53` `embedding` / `Qwen/Qwen3-Embedding-4B` input=298 output=0 total=298 source=`ragent.llm.openai.openai_embed`
194. `2026-05-20T23:39:13` `chat` / `deepseek-v4-flash` input=2712 output=1712 total=4424 source=`ragent.llm.openai.openai_complete_if_cache`
195. `2026-05-20T23:39:17` `embedding` / `Qwen/Qwen3-Embedding-4B` input=392 output=0 total=392 source=`ragent.llm.openai.openai_embed`
196. `2026-05-20T23:39:41` `chat` / `deepseek-v4-flash` input=2793 output=2012 total=4805 source=`ragent.llm.openai.openai_complete_if_cache`
197. `2026-05-20T23:39:43` `embedding` / `Qwen/Qwen3-Embedding-4B` input=328 output=0 total=328 source=`ragent.llm.openai.openai_embed`
198. `2026-05-20T23:40:38` `chat` / `deepseek-v4-flash` input=2736 output=5199 total=7935 source=`ragent.llm.openai.openai_complete_if_cache`
199. `2026-05-20T23:40:56` `embedding` / `Qwen/Qwen3-Embedding-4B` input=301 output=0 total=301 source=`ragent.llm.openai.openai_embed`
200. `2026-05-20T23:41:25` `chat` / `deepseek-v4-flash` input=2713 output=2837 total=5550 source=`ragent.llm.openai.openai_complete_if_cache`
201. `2026-05-20T23:41:27` `embedding` / `Qwen/Qwen3-Embedding-4B` input=361 output=0 total=361 source=`ragent.llm.openai.openai_embed`
202. `2026-05-20T23:42:04` `chat` / `deepseek-v4-flash` input=2765 output=2649 total=5414 source=`ragent.llm.openai.openai_complete_if_cache`
203. `2026-05-20T23:42:10` `embedding` / `Qwen/Qwen3-Embedding-4B` input=45 output=0 total=45 source=`ragent.llm.openai.openai_embed`
204. `2026-05-20T23:42:39` `chat` / `deepseek-v4-flash` input=2488 output=2640 total=5128 source=`ragent.llm.openai.openai_complete_if_cache`
205. `2026-05-20T23:42:40` `embedding` / `Qwen/Qwen3-Embedding-4B` input=157 output=0 total=157 source=`ragent.llm.openai.openai_embed`
206. `2026-05-20T23:43:00` `chat` / `deepseek-v4-flash` input=2592 output=1706 total=4298 source=`ragent.llm.openai.openai_complete_if_cache`
207. `2026-05-20T23:43:02` `embedding` / `Qwen/Qwen3-Embedding-4B` input=141 output=0 total=141 source=`ragent.llm.openai.openai_embed`
208. `2026-05-20T23:43:19` `chat` / `deepseek-v4-flash` input=2578 output=1764 total=4342 source=`ragent.llm.openai.openai_complete_if_cache`
209. `2026-05-20T23:43:21` `embedding` / `Qwen/Qwen3-Embedding-4B` input=163 output=0 total=163 source=`ragent.llm.openai.openai_embed`
210. `2026-05-20T23:43:59` `chat` / `deepseek-v4-flash` input=2591 output=3594 total=6185 source=`ragent.llm.openai.openai_complete_if_cache`
211. `2026-05-20T23:44:07` `embedding` / `Qwen/Qwen3-Embedding-4B` input=166 output=0 total=166 source=`ragent.llm.openai.openai_embed`
212. `2026-05-20T23:44:36` `chat` / `deepseek-v4-flash` input=2590 output=2720 total=5310 source=`ragent.llm.openai.openai_complete_if_cache`
213. `2026-05-20T23:44:40` `embedding` / `Qwen/Qwen3-Embedding-4B` input=775 output=0 total=775 source=`ragent.llm.openai.openai_embed`
214. `2026-05-20T23:45:17` `chat` / `deepseek-v4-flash` input=3217 output=3521 total=6738 source=`ragent.llm.openai.openai_complete_if_cache`
215. `2026-05-20T23:45:19` `embedding` / `Qwen/Qwen3-Embedding-4B` input=745 output=0 total=745 source=`ragent.llm.openai.openai_embed`
216. `2026-05-20T23:46:33` `chat` / `deepseek-v4-flash` input=3185 output=5843 total=9028 source=`ragent.llm.openai.openai_complete_if_cache`
217. `2026-05-20T23:46:35` `embedding` / `Qwen/Qwen3-Embedding-4B` input=302 output=0 total=302 source=`ragent.llm.openai.openai_embed`
218. `2026-05-20T23:47:06` `chat` / `deepseek-v4-flash` input=2733 output=2713 total=5446 source=`ragent.llm.openai.openai_complete_if_cache`
