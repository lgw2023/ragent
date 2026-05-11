# Model Usage Report: parse

- Task label: `pdf_insert`
- Started at: `2026-04-07T03:32:59`
- Ended at: `2026-04-07T03:36:24`
- Metadata:
  - `pdf_file_path`: `/Users/liguowei/ubuntu/ragent/example/GBT22106-2008dz.pdf`
  - `project_dir`: `/Users/liguowei/ubuntu/ragent/example/demo_diet_kg`
  - `stage`: `all`

## Summary By Model Type

| Type | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| chat | 178 | 411035 | 87373 | 498408 | 0 |
| embedding | 198 | 61481 | 0 | 61481 | 0 |
| rerank | 0 | 0 | 0 | 0 | 0 |
| image | 2 | 0 | 0 | 0 | 2 |
| total | 378 | 472516 | 87373 | 559889 | 2 |

## Summary By Model

### chat

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3.5-flash | 178 | 411035 | 87373 | 498408 | 0 |

### embedding

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| text-embedding-v3 | 198 | 61481 | 0 | 61481 | 0 |

### image

| Model | Calls | Input Tokens | Output Tokens | Total Tokens | Missing Usage |
| --- | ---: | ---: | ---: | ---: | ---: |
| qwen3-vl-flash | 2 | 0 | 0 | 0 | 2 |

## Call Events

1. `2026-04-07T03:33:29` `image` / `qwen3-vl-flash` input=0 output=0 total=0 source=`integrations.multimodal_image_analysis_with_context_sync`
2. `2026-04-07T03:33:31` `image` / `qwen3-vl-flash` input=0 output=0 total=0 source=`integrations.multimodal_image_analysis_with_context_sync`
3. `2026-04-07T03:33:33` `embedding` / `text-embedding-v3` input=19 output=0 total=19 source=`ragent.llm.openai.openai_embed`
4. `2026-04-07T03:33:33` `embedding` / `text-embedding-v3` input=37 output=0 total=37 source=`ragent.llm.openai.openai_embed`
5. `2026-04-07T03:33:33` `embedding` / `text-embedding-v3` input=91 output=0 total=91 source=`ragent.llm.openai.openai_embed`
6. `2026-04-07T03:33:33` `embedding` / `text-embedding-v3` input=50 output=0 total=50 source=`ragent.llm.openai.openai_embed`
7. `2026-04-07T03:33:33` `embedding` / `text-embedding-v3` input=83 output=0 total=83 source=`ragent.llm.openai.openai_embed`
8. `2026-04-07T03:33:33` `embedding` / `text-embedding-v3` input=252 output=0 total=252 source=`ragent.llm.openai.openai_embed`
9. `2026-04-07T03:33:33` `embedding` / `text-embedding-v3` input=234 output=0 total=234 source=`ragent.llm.openai.openai_embed`
10. `2026-04-07T03:33:33` `embedding` / `text-embedding-v3` input=32 output=0 total=32 source=`ragent.llm.openai.openai_embed`
11. `2026-04-07T03:33:34` `embedding` / `text-embedding-v3` input=39 output=0 total=39 source=`ragent.llm.openai.openai_embed`
12. `2026-04-07T03:33:34` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
13. `2026-04-07T03:33:34` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
14. `2026-04-07T03:33:34` `embedding` / `text-embedding-v3` input=41 output=0 total=41 source=`ragent.llm.openai.openai_embed`
15. `2026-04-07T03:33:34` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
16. `2026-04-07T03:33:34` `embedding` / `text-embedding-v3` input=56 output=0 total=56 source=`ragent.llm.openai.openai_embed`
17. `2026-04-07T03:33:34` `embedding` / `text-embedding-v3` input=38 output=0 total=38 source=`ragent.llm.openai.openai_embed`
18. `2026-04-07T03:33:34` `embedding` / `text-embedding-v3` input=38 output=0 total=38 source=`ragent.llm.openai.openai_embed`
19. `2026-04-07T03:33:34` `embedding` / `text-embedding-v3` input=44 output=0 total=44 source=`ragent.llm.openai.openai_embed`
20. `2026-04-07T03:33:34` `embedding` / `text-embedding-v3` input=39 output=0 total=39 source=`ragent.llm.openai.openai_embed`
21. `2026-04-07T03:33:34` `embedding` / `text-embedding-v3` input=58 output=0 total=58 source=`ragent.llm.openai.openai_embed`
22. `2026-04-07T03:33:34` `embedding` / `text-embedding-v3` input=46 output=0 total=46 source=`ragent.llm.openai.openai_embed`
23. `2026-04-07T03:33:34` `embedding` / `text-embedding-v3` input=51 output=0 total=51 source=`ragent.llm.openai.openai_embed`
24. `2026-04-07T03:33:34` `embedding` / `text-embedding-v3` input=41 output=0 total=41 source=`ragent.llm.openai.openai_embed`
25. `2026-04-07T03:33:36` `chat` / `qwen3.5-flash` input=2427 output=223 total=2650 source=`ragent.llm.openai.openai_complete_if_cache`
26. `2026-04-07T03:33:36` `chat` / `qwen3.5-flash` input=2408 output=311 total=2719 source=`ragent.llm.openai.openai_complete_if_cache`
27. `2026-04-07T03:33:36` `chat` / `qwen3.5-flash` input=2424 output=265 total=2689 source=`ragent.llm.openai.openai_complete_if_cache`
28. `2026-04-07T03:33:37` `chat` / `qwen3.5-flash` input=2432 output=206 total=2638 source=`ragent.llm.openai.openai_complete_if_cache`
29. `2026-04-07T03:33:37` `chat` / `qwen3.5-flash` input=2417 output=353 total=2770 source=`ragent.llm.openai.openai_complete_if_cache`
30. `2026-04-07T03:33:37` `chat` / `qwen3.5-flash` input=2424 output=277 total=2701 source=`ragent.llm.openai.openai_complete_if_cache`
31. `2026-04-07T03:33:37` `chat` / `qwen3.5-flash` input=2461 output=218 total=2679 source=`ragent.llm.openai.openai_complete_if_cache`
32. `2026-04-07T03:33:37` `chat` / `qwen3.5-flash` input=2420 output=271 total=2691 source=`ragent.llm.openai.openai_complete_if_cache`
33. `2026-04-07T03:33:37` `chat` / `qwen3.5-flash` input=2427 output=292 total=2719 source=`ragent.llm.openai.openai_complete_if_cache`
34. `2026-04-07T03:33:37` `chat` / `qwen3.5-flash` input=2433 output=503 total=2936 source=`ragent.llm.openai.openai_complete_if_cache`
35. `2026-04-07T03:33:37` `chat` / `qwen3.5-flash` input=2437 output=356 total=2793 source=`ragent.llm.openai.openai_complete_if_cache`
36. `2026-04-07T03:33:38` `chat` / `qwen3.5-flash` input=2423 output=278 total=2701 source=`ragent.llm.openai.openai_complete_if_cache`
37. `2026-04-07T03:33:38` `chat` / `qwen3.5-flash` input=2421 output=372 total=2793 source=`ragent.llm.openai.openai_complete_if_cache`
38. `2026-04-07T03:33:38` `chat` / `qwen3.5-flash` input=2428 output=379 total=2807 source=`ragent.llm.openai.openai_complete_if_cache`
39. `2026-04-07T03:33:38` `chat` / `qwen3.5-flash` input=2420 output=399 total=2819 source=`ragent.llm.openai.openai_complete_if_cache`
40. `2026-04-07T03:33:38` `chat` / `qwen3.5-flash` input=2450 output=393 total=2843 source=`ragent.llm.openai.openai_complete_if_cache`
41. `2026-04-07T03:33:38` `chat` / `qwen3.5-flash` input=2422 output=330 total=2752 source=`ragent.llm.openai.openai_complete_if_cache`
42. `2026-04-07T03:33:38` `chat` / `qwen3.5-flash` input=2423 output=455 total=2878 source=`ragent.llm.openai.openai_complete_if_cache`
43. `2026-04-07T03:33:39` `chat` / `qwen3.5-flash` input=2425 output=488 total=2913 source=`ragent.llm.openai.openai_complete_if_cache`
44. `2026-04-07T03:33:39` `chat` / `qwen3.5-flash` input=3143 output=346 total=3489 source=`ragent.llm.openai.openai_complete_if_cache`
45. `2026-04-07T03:33:40` `chat` / `qwen3.5-flash` input=3074 output=399 total=3473 source=`ragent.llm.openai.openai_complete_if_cache`
46. `2026-04-07T03:33:41` `chat` / `qwen3.5-flash` input=3194 output=456 total=3650 source=`ragent.llm.openai.openai_complete_if_cache`
47. `2026-04-07T03:33:41` `chat` / `qwen3.5-flash` input=3243 output=427 total=3670 source=`ragent.llm.openai.openai_complete_if_cache`
48. `2026-04-07T03:33:41` `chat` / `qwen3.5-flash` input=2437 output=657 total=3094 source=`ragent.llm.openai.openai_complete_if_cache`
49. `2026-04-07T03:33:41` `chat` / `qwen3.5-flash` input=3125 output=612 total=3737 source=`ragent.llm.openai.openai_complete_if_cache`
50. `2026-04-07T03:33:41` `chat` / `qwen3.5-flash` input=3113 output=591 total=3704 source=`ragent.llm.openai.openai_complete_if_cache`
51. `2026-04-07T03:33:41` `chat` / `qwen3.5-flash` input=3115 output=450 total=3565 source=`ragent.llm.openai.openai_complete_if_cache`
52. `2026-04-07T03:33:42` `chat` / `qwen3.5-flash` input=3217 output=534 total=3751 source=`ragent.llm.openai.openai_complete_if_cache`
53. `2026-04-07T03:33:42` `chat` / `qwen3.5-flash` input=3062 output=502 total=3564 source=`ragent.llm.openai.openai_complete_if_cache`
54. `2026-04-07T03:33:42` `chat` / `qwen3.5-flash` input=3231 output=549 total=3780 source=`ragent.llm.openai.openai_complete_if_cache`
55. `2026-04-07T03:33:42` `chat` / `qwen3.5-flash` input=3143 output=656 total=3799 source=`ragent.llm.openai.openai_complete_if_cache`
56. `2026-04-07T03:33:42` `chat` / `qwen3.5-flash` input=3125 output=564 total=3689 source=`ragent.llm.openai.openai_complete_if_cache`
57. `2026-04-07T03:33:42` `chat` / `qwen3.5-flash` input=3302 output=522 total=3824 source=`ragent.llm.openai.openai_complete_if_cache`
58. `2026-04-07T03:33:43` `chat` / `qwen3.5-flash` input=3176 output=473 total=3649 source=`ragent.llm.openai.openai_complete_if_cache`
59. `2026-04-07T03:33:44` `chat` / `qwen3.5-flash` input=3217 output=872 total=4089 source=`ragent.llm.openai.openai_complete_if_cache`
60. `2026-04-07T03:33:44` `chat` / `qwen3.5-flash` input=3337 output=631 total=3968 source=`ragent.llm.openai.openai_complete_if_cache`
61. `2026-04-07T03:33:45` `chat` / `qwen3.5-flash` input=3103 output=1090 total=4193 source=`ragent.llm.openai.openai_complete_if_cache`
62. `2026-04-07T03:33:47` `chat` / `qwen3.5-flash` input=3518 output=1033 total=4551 source=`ragent.llm.openai.openai_complete_if_cache`
63. `2026-04-07T03:33:48` `chat` / `qwen3.5-flash` input=2655 output=1553 total=4208 source=`ragent.llm.openai.openai_complete_if_cache`
64. `2026-04-07T03:33:49` `chat` / `qwen3.5-flash` input=2591 output=2276 total=4867 source=`ragent.llm.openai.openai_complete_if_cache`
65. `2026-04-07T03:33:53` `chat` / `qwen3.5-flash` input=3267 output=730 total=3997 source=`ragent.llm.openai.openai_complete_if_cache`
66. `2026-04-07T03:33:53` `chat` / `qwen3.5-flash` input=3360 output=746 total=4106 source=`ragent.llm.openai.openai_complete_if_cache`
67. `2026-04-07T03:34:00` `chat` / `qwen3.5-flash` input=4632 output=1776 total=6408 source=`ragent.llm.openai.openai_complete_if_cache`
68. `2026-04-07T03:34:26` `chat` / `qwen3.5-flash` input=5291 output=4369 total=9660 source=`ragent.llm.openai.openai_complete_if_cache`
69. `2026-04-07T03:34:27` `chat` / `qwen3.5-flash` input=223 output=65 total=288 source=`ragent.llm.openai.openai_complete_if_cache`
70. `2026-04-07T03:34:27` `chat` / `qwen3.5-flash` input=219 output=70 total=289 source=`ragent.llm.openai.openai_complete_if_cache`
71. `2026-04-07T03:34:27` `chat` / `qwen3.5-flash` input=248 output=71 total=319 source=`ragent.llm.openai.openai_complete_if_cache`
72. `2026-04-07T03:34:27` `chat` / `qwen3.5-flash` input=236 output=84 total=320 source=`ragent.llm.openai.openai_complete_if_cache`
73. `2026-04-07T03:34:28` `chat` / `qwen3.5-flash` input=356 output=106 total=462 source=`ragent.llm.openai.openai_complete_if_cache`
74. `2026-04-07T03:34:28` `chat` / `qwen3.5-flash` input=231 output=107 total=338 source=`ragent.llm.openai.openai_complete_if_cache`
75. `2026-04-07T03:34:28` `chat` / `qwen3.5-flash` input=291 output=120 total=411 source=`ragent.llm.openai.openai_complete_if_cache`
76. `2026-04-07T03:34:28` `chat` / `qwen3.5-flash` input=543 output=198 total=741 source=`ragent.llm.openai.openai_complete_if_cache`
77. `2026-04-07T03:34:29` `chat` / `qwen3.5-flash` input=249 output=64 total=313 source=`ragent.llm.openai.openai_complete_if_cache`
78. `2026-04-07T03:34:29` `chat` / `qwen3.5-flash` input=363 output=80 total=443 source=`ragent.llm.openai.openai_complete_if_cache`
79. `2026-04-07T03:34:29` `embedding` / `text-embedding-v3` input=232 output=0 total=232 source=`ragent.llm.openai.openai_embed`
80. `2026-04-07T03:34:29` `embedding` / `text-embedding-v3` input=177 output=0 total=177 source=`ragent.llm.openai.openai_embed`
81. `2026-04-07T03:34:29` `embedding` / `text-embedding-v3` input=472 output=0 total=472 source=`ragent.llm.openai.openai_embed`
82. `2026-04-07T03:34:29` `embedding` / `text-embedding-v3` input=386 output=0 total=386 source=`ragent.llm.openai.openai_embed`
83. `2026-04-07T03:34:29` `embedding` / `text-embedding-v3` input=159 output=0 total=159 source=`ragent.llm.openai.openai_embed`
84. `2026-04-07T03:34:29` `embedding` / `text-embedding-v3` input=826 output=0 total=826 source=`ragent.llm.openai.openai_embed`
85. `2026-04-07T03:34:29` `embedding` / `text-embedding-v3` input=219 output=0 total=219 source=`ragent.llm.openai.openai_embed`
86. `2026-04-07T03:34:30` `embedding` / `text-embedding-v3` input=203 output=0 total=203 source=`ragent.llm.openai.openai_embed`
87. `2026-04-07T03:34:30` `embedding` / `text-embedding-v3` input=357 output=0 total=357 source=`ragent.llm.openai.openai_embed`
88. `2026-04-07T03:34:30` `embedding` / `text-embedding-v3` input=259 output=0 total=259 source=`ragent.llm.openai.openai_embed`
89. `2026-04-07T03:34:30` `embedding` / `text-embedding-v3` input=362 output=0 total=362 source=`ragent.llm.openai.openai_embed`
90. `2026-04-07T03:34:30` `embedding` / `text-embedding-v3` input=377 output=0 total=377 source=`ragent.llm.openai.openai_embed`
91. `2026-04-07T03:34:30` `embedding` / `text-embedding-v3` input=1654 output=0 total=1654 source=`ragent.llm.openai.openai_embed`
92. `2026-04-07T03:34:30` `embedding` / `text-embedding-v3` input=1036 output=0 total=1036 source=`ragent.llm.openai.openai_embed`
93. `2026-04-07T03:34:30` `embedding` / `text-embedding-v3` input=330 output=0 total=330 source=`ragent.llm.openai.openai_embed`
94. `2026-04-07T03:34:30` `embedding` / `text-embedding-v3` input=355 output=0 total=355 source=`ragent.llm.openai.openai_embed`
95. `2026-04-07T03:34:30` `embedding` / `text-embedding-v3` input=384 output=0 total=384 source=`ragent.llm.openai.openai_embed`
96. `2026-04-07T03:34:30` `embedding` / `text-embedding-v3` input=225 output=0 total=225 source=`ragent.llm.openai.openai_embed`
97. `2026-04-07T03:34:30` `embedding` / `text-embedding-v3` input=316 output=0 total=316 source=`ragent.llm.openai.openai_embed`
98. `2026-04-07T03:34:30` `embedding` / `text-embedding-v3` input=356 output=0 total=356 source=`ragent.llm.openai.openai_embed`
99. `2026-04-07T03:34:31` `embedding` / `text-embedding-v3` input=296 output=0 total=296 source=`ragent.llm.openai.openai_embed`
100. `2026-04-07T03:34:31` `embedding` / `text-embedding-v3` input=368 output=0 total=368 source=`ragent.llm.openai.openai_embed`
101. `2026-04-07T03:34:31` `embedding` / `text-embedding-v3` input=314 output=0 total=314 source=`ragent.llm.openai.openai_embed`
102. `2026-04-07T03:34:31` `embedding` / `text-embedding-v3` input=307 output=0 total=307 source=`ragent.llm.openai.openai_embed`
103. `2026-04-07T03:34:31` `embedding` / `text-embedding-v3` input=300 output=0 total=300 source=`ragent.llm.openai.openai_embed`
104. `2026-04-07T03:34:31` `embedding` / `text-embedding-v3` input=322 output=0 total=322 source=`ragent.llm.openai.openai_embed`
105. `2026-04-07T03:34:31` `embedding` / `text-embedding-v3` input=295 output=0 total=295 source=`ragent.llm.openai.openai_embed`
106. `2026-04-07T03:34:31` `embedding` / `text-embedding-v3` input=319 output=0 total=319 source=`ragent.llm.openai.openai_embed`
107. `2026-04-07T03:34:31` `embedding` / `text-embedding-v3` input=368 output=0 total=368 source=`ragent.llm.openai.openai_embed`
108. `2026-04-07T03:34:31` `embedding` / `text-embedding-v3` input=343 output=0 total=343 source=`ragent.llm.openai.openai_embed`
109. `2026-04-07T03:34:31` `embedding` / `text-embedding-v3` input=343 output=0 total=343 source=`ragent.llm.openai.openai_embed`
110. `2026-04-07T03:34:31` `embedding` / `text-embedding-v3` input=331 output=0 total=331 source=`ragent.llm.openai.openai_embed`
111. `2026-04-07T03:34:31` `embedding` / `text-embedding-v3` input=308 output=0 total=308 source=`ragent.llm.openai.openai_embed`
112. `2026-04-07T03:34:31` `embedding` / `text-embedding-v3` input=286 output=0 total=286 source=`ragent.llm.openai.openai_embed`
113. `2026-04-07T03:34:32` `embedding` / `text-embedding-v3` input=344 output=0 total=344 source=`ragent.llm.openai.openai_embed`
114. `2026-04-07T03:34:32` `embedding` / `text-embedding-v3` input=287 output=0 total=287 source=`ragent.llm.openai.openai_embed`
115. `2026-04-07T03:34:32` `embedding` / `text-embedding-v3` input=364 output=0 total=364 source=`ragent.llm.openai.openai_embed`
116. `2026-04-07T03:34:32` `embedding` / `text-embedding-v3` input=372 output=0 total=372 source=`ragent.llm.openai.openai_embed`
117. `2026-04-07T03:34:32` `embedding` / `text-embedding-v3` input=321 output=0 total=321 source=`ragent.llm.openai.openai_embed`
118. `2026-04-07T03:34:32` `embedding` / `text-embedding-v3` input=298 output=0 total=298 source=`ragent.llm.openai.openai_embed`
119. `2026-04-07T03:34:32` `embedding` / `text-embedding-v3` input=330 output=0 total=330 source=`ragent.llm.openai.openai_embed`
120. `2026-04-07T03:34:32` `embedding` / `text-embedding-v3` input=357 output=0 total=357 source=`ragent.llm.openai.openai_embed`
121. `2026-04-07T03:34:32` `embedding` / `text-embedding-v3` input=369 output=0 total=369 source=`ragent.llm.openai.openai_embed`
122. `2026-04-07T03:34:32` `embedding` / `text-embedding-v3` input=299 output=0 total=299 source=`ragent.llm.openai.openai_embed`
123. `2026-04-07T03:34:32` `embedding` / `text-embedding-v3` input=345 output=0 total=345 source=`ragent.llm.openai.openai_embed`
124. `2026-04-07T03:34:32` `embedding` / `text-embedding-v3` input=354 output=0 total=354 source=`ragent.llm.openai.openai_embed`
125. `2026-04-07T03:34:32` `embedding` / `text-embedding-v3` input=357 output=0 total=357 source=`ragent.llm.openai.openai_embed`
126. `2026-04-07T03:34:33` `embedding` / `text-embedding-v3` input=531 output=0 total=531 source=`ragent.llm.openai.openai_embed`
127. `2026-04-07T03:34:35` `embedding` / `text-embedding-v3` input=220 output=0 total=220 source=`ragent.llm.openai.openai_embed`
128. `2026-04-07T03:34:39` `chat` / `qwen3.5-flash` input=2579 output=618 total=3197 source=`ragent.llm.openai.openai_complete_if_cache`
129. `2026-04-07T03:34:46` `chat` / `qwen3.5-flash` input=3621 output=781 total=4402 source=`ragent.llm.openai.openai_complete_if_cache`
130. `2026-04-07T03:34:46` `chat` / `qwen3.5-flash` input=222 output=73 total=295 source=`ragent.llm.openai.openai_complete_if_cache`
131. `2026-04-07T03:34:47` `embedding` / `text-embedding-v3` input=504 output=0 total=504 source=`ragent.llm.openai.openai_embed`
132. `2026-04-07T03:34:47` `embedding` / `text-embedding-v3` input=115 output=0 total=115 source=`ragent.llm.openai.openai_embed`
133. `2026-04-07T03:34:47` `embedding` / `text-embedding-v3` input=359 output=0 total=359 source=`ragent.llm.openai.openai_embed`
134. `2026-04-07T03:34:49` `embedding` / `text-embedding-v3` input=45 output=0 total=45 source=`ragent.llm.openai.openai_embed`
135. `2026-04-07T03:34:49` `embedding` / `text-embedding-v3` input=54 output=0 total=54 source=`ragent.llm.openai.openai_embed`
136. `2026-04-07T03:34:49` `embedding` / `text-embedding-v3` input=25 output=0 total=25 source=`ragent.llm.openai.openai_embed`
137. `2026-04-07T03:34:49` `embedding` / `text-embedding-v3` input=223 output=0 total=223 source=`ragent.llm.openai.openai_embed`
138. `2026-04-07T03:34:49` `embedding` / `text-embedding-v3` input=41 output=0 total=41 source=`ragent.llm.openai.openai_embed`
139. `2026-04-07T03:34:49` `embedding` / `text-embedding-v3` input=48 output=0 total=48 source=`ragent.llm.openai.openai_embed`
140. `2026-04-07T03:34:50` `embedding` / `text-embedding-v3` input=29 output=0 total=29 source=`ragent.llm.openai.openai_embed`
141. `2026-04-07T03:34:52` `chat` / `qwen3.5-flash` input=2411 output=271 total=2682 source=`ragent.llm.openai.openai_complete_if_cache`
142. `2026-04-07T03:34:52` `chat` / `qwen3.5-flash` input=2427 output=347 total=2774 source=`ragent.llm.openai.openai_complete_if_cache`
143. `2026-04-07T03:34:53` `chat` / `qwen3.5-flash` input=2436 output=403 total=2839 source=`ragent.llm.openai.openai_complete_if_cache`
144. `2026-04-07T03:34:53` `chat` / `qwen3.5-flash` input=2434 output=455 total=2889 source=`ragent.llm.openai.openai_complete_if_cache`
145. `2026-04-07T03:34:54` `chat` / `qwen3.5-flash` input=2564 output=459 total=3023 source=`ragent.llm.openai.openai_complete_if_cache`
146. `2026-04-07T03:34:54` `chat` / `qwen3.5-flash` input=2413 output=381 total=2794 source=`ragent.llm.openai.openai_complete_if_cache`
147. `2026-04-07T03:34:55` `chat` / `qwen3.5-flash` input=2448 output=568 total=3016 source=`ragent.llm.openai.openai_complete_if_cache`
148. `2026-04-07T03:34:56` `chat` / `qwen3.5-flash` input=3106 output=405 total=3511 source=`ragent.llm.openai.openai_complete_if_cache`
149. `2026-04-07T03:34:58` `chat` / `qwen3.5-flash` input=3263 output=696 total=3959 source=`ragent.llm.openai.openai_complete_if_cache`
150. `2026-04-07T03:34:58` `chat` / `qwen3.5-flash` input=3218 output=535 total=3753 source=`ragent.llm.openai.openai_complete_if_cache`
151. `2026-04-07T03:34:58` `chat` / `qwen3.5-flash` input=3313 output=600 total=3913 source=`ragent.llm.openai.openai_complete_if_cache`
152. `2026-04-07T03:34:59` `chat` / `qwen3.5-flash` input=3447 output=673 total=4120 source=`ragent.llm.openai.openai_complete_if_cache`
153. `2026-04-07T03:35:00` `chat` / `qwen3.5-flash` input=3198 output=931 total=4129 source=`ragent.llm.openai.openai_complete_if_cache`
154. `2026-04-07T03:35:02` `chat` / `qwen3.5-flash` input=3440 output=758 total=4198 source=`ragent.llm.openai.openai_complete_if_cache`
155. `2026-04-07T03:35:03` `chat` / `qwen3.5-flash` input=245 output=144 total=389 source=`ragent.llm.openai.openai_complete_if_cache`
156. `2026-04-07T03:35:04` `chat` / `qwen3.5-flash` input=348 output=165 total=513 source=`ragent.llm.openai.openai_complete_if_cache`
157. `2026-04-07T03:35:04` `chat` / `qwen3.5-flash` input=514 output=182 total=696 source=`ragent.llm.openai.openai_complete_if_cache`
158. `2026-04-07T03:35:05` `chat` / `qwen3.5-flash` input=311 output=92 total=403 source=`ragent.llm.openai.openai_complete_if_cache`
159. `2026-04-07T03:35:05` `embedding` / `text-embedding-v3` input=300 output=0 total=300 source=`ragent.llm.openai.openai_embed`
160. `2026-04-07T03:35:06` `embedding` / `text-embedding-v3` input=467 output=0 total=467 source=`ragent.llm.openai.openai_embed`
161. `2026-04-07T03:35:06` `embedding` / `text-embedding-v3` input=1270 output=0 total=1270 source=`ragent.llm.openai.openai_embed`
162. `2026-04-07T03:35:06` `embedding` / `text-embedding-v3` input=263 output=0 total=263 source=`ragent.llm.openai.openai_embed`
163. `2026-04-07T03:35:06` `embedding` / `text-embedding-v3` input=353 output=0 total=353 source=`ragent.llm.openai.openai_embed`
164. `2026-04-07T03:35:06` `embedding` / `text-embedding-v3` input=916 output=0 total=916 source=`ragent.llm.openai.openai_embed`
165. `2026-04-07T03:35:06` `embedding` / `text-embedding-v3` input=355 output=0 total=355 source=`ragent.llm.openai.openai_embed`
166. `2026-04-07T03:35:06` `embedding` / `text-embedding-v3` input=314 output=0 total=314 source=`ragent.llm.openai.openai_embed`
167. `2026-04-07T03:35:06` `embedding` / `text-embedding-v3` input=385 output=0 total=385 source=`ragent.llm.openai.openai_embed`
168. `2026-04-07T03:35:06` `embedding` / `text-embedding-v3` input=461 output=0 total=461 source=`ragent.llm.openai.openai_embed`
169. `2026-04-07T03:35:06` `embedding` / `text-embedding-v3` input=178 output=0 total=178 source=`ragent.llm.openai.openai_embed`
170. `2026-04-07T03:35:06` `embedding` / `text-embedding-v3` input=448 output=0 total=448 source=`ragent.llm.openai.openai_embed`
171. `2026-04-07T03:35:06` `embedding` / `text-embedding-v3` input=420 output=0 total=420 source=`ragent.llm.openai.openai_embed`
172. `2026-04-07T03:35:08` `embedding` / `text-embedding-v3` input=333 output=0 total=333 source=`ragent.llm.openai.openai_embed`
173. `2026-04-07T03:35:12` `chat` / `qwen3.5-flash` input=2671 output=428 total=3099 source=`ragent.llm.openai.openai_complete_if_cache`
174. `2026-04-07T03:35:20` `chat` / `qwen3.5-flash` input=3523 output=1014 total=4537 source=`ragent.llm.openai.openai_complete_if_cache`
175. `2026-04-07T03:35:22` `chat` / `qwen3.5-flash` input=349 output=175 total=524 source=`ragent.llm.openai.openai_complete_if_cache`
176. `2026-04-07T03:35:22` `chat` / `qwen3.5-flash` input=258 output=194 total=452 source=`ragent.llm.openai.openai_complete_if_cache`
177. `2026-04-07T03:35:23` `embedding` / `text-embedding-v3` input=359 output=0 total=359 source=`ragent.llm.openai.openai_embed`
178. `2026-04-07T03:35:23` `embedding` / `text-embedding-v3` input=737 output=0 total=737 source=`ragent.llm.openai.openai_embed`
179. `2026-04-07T03:35:23` `embedding` / `text-embedding-v3` input=355 output=0 total=355 source=`ragent.llm.openai.openai_embed`
180. `2026-04-07T03:35:25` `embedding` / `text-embedding-v3` input=210 output=0 total=210 source=`ragent.llm.openai.openai_embed`
181. `2026-04-07T03:35:25` `embedding` / `text-embedding-v3` input=48 output=0 total=48 source=`ragent.llm.openai.openai_embed`
182. `2026-04-07T03:35:25` `embedding` / `text-embedding-v3` input=233 output=0 total=233 source=`ragent.llm.openai.openai_embed`
183. `2026-04-07T03:35:25` `embedding` / `text-embedding-v3` input=56 output=0 total=56 source=`ragent.llm.openai.openai_embed`
184. `2026-04-07T03:35:25` `embedding` / `text-embedding-v3` input=29 output=0 total=29 source=`ragent.llm.openai.openai_embed`
185. `2026-04-07T03:35:26` `embedding` / `text-embedding-v3` input=255 output=0 total=255 source=`ragent.llm.openai.openai_embed`
186. `2026-04-07T03:35:26` `embedding` / `text-embedding-v3` input=421 output=0 total=421 source=`ragent.llm.openai.openai_embed`
187. `2026-04-07T03:35:26` `embedding` / `text-embedding-v3` input=464 output=0 total=464 source=`ragent.llm.openai.openai_embed`
188. `2026-04-07T03:35:26` `embedding` / `text-embedding-v3` input=56 output=0 total=56 source=`ragent.llm.openai.openai_embed`
189. `2026-04-07T03:35:26` `embedding` / `text-embedding-v3` input=29 output=0 total=29 source=`ragent.llm.openai.openai_embed`
190. `2026-04-07T03:35:26` `embedding` / `text-embedding-v3` input=426 output=0 total=426 source=`ragent.llm.openai.openai_embed`
191. `2026-04-07T03:35:26` `embedding` / `text-embedding-v3` input=29 output=0 total=29 source=`ragent.llm.openai.openai_embed`
192. `2026-04-07T03:35:26` `embedding` / `text-embedding-v3` input=451 output=0 total=451 source=`ragent.llm.openai.openai_embed`
193. `2026-04-07T03:35:26` `embedding` / `text-embedding-v3` input=29 output=0 total=29 source=`ragent.llm.openai.openai_embed`
194. `2026-04-07T03:35:26` `embedding` / `text-embedding-v3` input=56 output=0 total=56 source=`ragent.llm.openai.openai_embed`
195. `2026-04-07T03:35:26` `embedding` / `text-embedding-v3` input=305 output=0 total=305 source=`ragent.llm.openai.openai_embed`
196. `2026-04-07T03:35:27` `embedding` / `text-embedding-v3` input=29 output=0 total=29 source=`ragent.llm.openai.openai_embed`
197. `2026-04-07T03:35:27` `embedding` / `text-embedding-v3` input=34 output=0 total=34 source=`ragent.llm.openai.openai_embed`
198. `2026-04-07T03:35:27` `embedding` / `text-embedding-v3` input=40 output=0 total=40 source=`ragent.llm.openai.openai_embed`
199. `2026-04-07T03:35:27` `embedding` / `text-embedding-v3` input=36 output=0 total=36 source=`ragent.llm.openai.openai_embed`
200. `2026-04-07T03:35:27` `embedding` / `text-embedding-v3` input=29 output=0 total=29 source=`ragent.llm.openai.openai_embed`
201. `2026-04-07T03:35:27` `embedding` / `text-embedding-v3` input=279 output=0 total=279 source=`ragent.llm.openai.openai_embed`
202. `2026-04-07T03:35:27` `embedding` / `text-embedding-v3` input=46 output=0 total=46 source=`ragent.llm.openai.openai_embed`
203. `2026-04-07T03:35:27` `embedding` / `text-embedding-v3` input=102 output=0 total=102 source=`ragent.llm.openai.openai_embed`
204. `2026-04-07T03:35:27` `embedding` / `text-embedding-v3` input=34 output=0 total=34 source=`ragent.llm.openai.openai_embed`
205. `2026-04-07T03:35:27` `embedding` / `text-embedding-v3` input=32 output=0 total=32 source=`ragent.llm.openai.openai_embed`
206. `2026-04-07T03:35:27` `embedding` / `text-embedding-v3` input=82 output=0 total=82 source=`ragent.llm.openai.openai_embed`
207. `2026-04-07T03:35:27` `embedding` / `text-embedding-v3` input=79 output=0 total=79 source=`ragent.llm.openai.openai_embed`
208. `2026-04-07T03:35:27` `embedding` / `text-embedding-v3` input=98 output=0 total=98 source=`ragent.llm.openai.openai_embed`
209. `2026-04-07T03:35:27` `embedding` / `text-embedding-v3` input=45 output=0 total=45 source=`ragent.llm.openai.openai_embed`
210. `2026-04-07T03:35:28` `embedding` / `text-embedding-v3` input=70 output=0 total=70 source=`ragent.llm.openai.openai_embed`
211. `2026-04-07T03:35:28` `embedding` / `text-embedding-v3` input=50 output=0 total=50 source=`ragent.llm.openai.openai_embed`
212. `2026-04-07T03:35:28` `chat` / `qwen3.5-flash` input=2433 output=282 total=2715 source=`ragent.llm.openai.openai_complete_if_cache`
213. `2026-04-07T03:35:29` `chat` / `qwen3.5-flash` input=2573 output=346 total=2919 source=`ragent.llm.openai.openai_complete_if_cache`
214. `2026-04-07T03:35:29` `chat` / `qwen3.5-flash` input=2433 output=346 total=2779 source=`ragent.llm.openai.openai_complete_if_cache`
215. `2026-04-07T03:35:29` `chat` / `qwen3.5-flash` input=2413 output=306 total=2719 source=`ragent.llm.openai.openai_complete_if_cache`
216. `2026-04-07T03:35:29` `chat` / `qwen3.5-flash` input=2447 output=350 total=2797 source=`ragent.llm.openai.openai_complete_if_cache`
217. `2026-04-07T03:35:29` `chat` / `qwen3.5-flash` input=2725 output=332 total=3057 source=`ragent.llm.openai.openai_complete_if_cache`
218. `2026-04-07T03:35:30` `chat` / `qwen3.5-flash` input=2577 output=467 total=3044 source=`ragent.llm.openai.openai_complete_if_cache`
219. `2026-04-07T03:35:30` `chat` / `qwen3.5-flash` input=2425 output=332 total=2757 source=`ragent.llm.openai.openai_complete_if_cache`
220. `2026-04-07T03:35:30` `chat` / `qwen3.5-flash` input=2417 output=299 total=2716 source=`ragent.llm.openai.openai_complete_if_cache`
221. `2026-04-07T03:35:30` `chat` / `qwen3.5-flash` input=2413 output=307 total=2720 source=`ragent.llm.openai.openai_complete_if_cache`
222. `2026-04-07T03:35:30` `chat` / `qwen3.5-flash` input=2454 output=225 total=2679 source=`ragent.llm.openai.openai_complete_if_cache`
223. `2026-04-07T03:35:30` `chat` / `qwen3.5-flash` input=2417 output=444 total=2861 source=`ragent.llm.openai.openai_complete_if_cache`
224. `2026-04-07T03:35:30` `chat` / `qwen3.5-flash` input=2415 output=322 total=2737 source=`ragent.llm.openai.openai_complete_if_cache`
225. `2026-04-07T03:35:30` `chat` / `qwen3.5-flash` input=2631 output=407 total=3038 source=`ragent.llm.openai.openai_complete_if_cache`
226. `2026-04-07T03:35:31` `chat` / `qwen3.5-flash` input=2433 output=434 total=2867 source=`ragent.llm.openai.openai_complete_if_cache`
227. `2026-04-07T03:35:31` `chat` / `qwen3.5-flash` input=2422 output=161 total=2583 source=`ragent.llm.openai.openai_complete_if_cache`
228. `2026-04-07T03:35:31` `chat` / `qwen3.5-flash` input=2413 output=340 total=2753 source=`ragent.llm.openai.openai_complete_if_cache`
229. `2026-04-07T03:35:31` `chat` / `qwen3.5-flash` input=2417 output=395 total=2812 source=`ragent.llm.openai.openai_complete_if_cache`
230. `2026-04-07T03:35:31` `chat` / `qwen3.5-flash` input=2476 output=385 total=2861 source=`ragent.llm.openai.openai_complete_if_cache`
231. `2026-04-07T03:35:31` `chat` / `qwen3.5-flash` input=2615 output=489 total=3104 source=`ragent.llm.openai.openai_complete_if_cache`
232. `2026-04-07T03:35:31` `chat` / `qwen3.5-flash` input=2413 output=353 total=2766 source=`ragent.llm.openai.openai_complete_if_cache`
233. `2026-04-07T03:35:31` `chat` / `qwen3.5-flash` input=2425 output=402 total=2827 source=`ragent.llm.openai.openai_complete_if_cache`
234. `2026-04-07T03:35:31` `chat` / `qwen3.5-flash` input=2452 output=347 total=2799 source=`ragent.llm.openai.openai_complete_if_cache`
235. `2026-04-07T03:35:32` `chat` / `qwen3.5-flash` input=2448 output=368 total=2816 source=`ragent.llm.openai.openai_complete_if_cache`
236. `2026-04-07T03:35:32` `chat` / `qwen3.5-flash` input=2473 output=351 total=2824 source=`ragent.llm.openai.openai_complete_if_cache`
237. `2026-04-07T03:35:33` `chat` / `qwen3.5-flash` input=2436 output=570 total=3006 source=`ragent.llm.openai.openai_complete_if_cache`
238. `2026-04-07T03:35:33` `chat` / `qwen3.5-flash` input=2428 output=324 total=2752 source=`ragent.llm.openai.openai_complete_if_cache`
239. `2026-04-07T03:35:33` `chat` / `qwen3.5-flash` input=2425 output=494 total=2919 source=`ragent.llm.openai.openai_complete_if_cache`
240. `2026-04-07T03:35:33` `chat` / `qwen3.5-flash` input=2627 output=691 total=3318 source=`ragent.llm.openai.openai_complete_if_cache`
241. `2026-04-07T03:35:33` `chat` / `qwen3.5-flash` input=3203 output=414 total=3617 source=`ragent.llm.openai.openai_complete_if_cache`
242. `2026-04-07T03:35:33` `chat` / `qwen3.5-flash` input=3143 output=423 total=3566 source=`ragent.llm.openai.openai_complete_if_cache`
243. `2026-04-07T03:35:34` `chat` / `qwen3.5-flash` input=3139 output=482 total=3621 source=`ragent.llm.openai.openai_complete_if_cache`
244. `2026-04-07T03:35:34` `chat` / `qwen3.5-flash` input=2797 output=908 total=3705 source=`ragent.llm.openai.openai_complete_if_cache`
245. `2026-04-07T03:35:34` `chat` / `qwen3.5-flash` input=2753 output=838 total=3591 source=`ragent.llm.openai.openai_complete_if_cache`
246. `2026-04-07T03:35:34` `chat` / `qwen3.5-flash` input=3221 output=558 total=3779 source=`ragent.llm.openai.openai_complete_if_cache`
247. `2026-04-07T03:35:34` `chat` / `qwen3.5-flash` input=3103 output=443 total=3546 source=`ragent.llm.openai.openai_complete_if_cache`
248. `2026-04-07T03:35:35` `chat` / `qwen3.5-flash` input=3144 output=577 total=3721 source=`ragent.llm.openai.openai_complete_if_cache`
249. `2026-04-07T03:35:35` `chat` / `qwen3.5-flash` input=3161 output=494 total=3655 source=`ragent.llm.openai.openai_complete_if_cache`
250. `2026-04-07T03:35:35` `chat` / `qwen3.5-flash` input=3140 output=485 total=3625 source=`ragent.llm.openai.openai_complete_if_cache`
251. `2026-04-07T03:35:35` `chat` / `qwen3.5-flash` input=2764 output=1003 total=3767 source=`ragent.llm.openai.openai_complete_if_cache`
252. `2026-04-07T03:35:35` `chat` / `qwen3.5-flash` input=3177 output=439 total=3616 source=`ragent.llm.openai.openai_complete_if_cache`
253. `2026-04-07T03:35:36` `chat` / `qwen3.5-flash` input=3190 output=570 total=3760 source=`ragent.llm.openai.openai_complete_if_cache`
254. `2026-04-07T03:35:36` `chat` / `qwen3.5-flash` input=3240 output=519 total=3759 source=`ragent.llm.openai.openai_complete_if_cache`
255. `2026-04-07T03:35:36` `chat` / `qwen3.5-flash` input=3007 output=499 total=3506 source=`ragent.llm.openai.openai_complete_if_cache`
256. `2026-04-07T03:35:36` `chat` / `qwen3.5-flash` input=3181 output=513 total=3694 source=`ragent.llm.openai.openai_complete_if_cache`
257. `2026-04-07T03:35:36` `chat` / `qwen3.5-flash` input=3291 output=717 total=4008 source=`ragent.llm.openai.openai_complete_if_cache`
258. `2026-04-07T03:35:36` `chat` / `qwen3.5-flash` input=3223 output=588 total=3811 source=`ragent.llm.openai.openai_complete_if_cache`
259. `2026-04-07T03:35:36` `chat` / `qwen3.5-flash` input=3236 output=553 total=3789 source=`ragent.llm.openai.openai_complete_if_cache`
260. `2026-04-07T03:35:37` `chat` / `qwen3.5-flash` input=3251 output=649 total=3900 source=`ragent.llm.openai.openai_complete_if_cache`
261. `2026-04-07T03:35:37` `chat` / `qwen3.5-flash` input=3528 output=810 total=4338 source=`ragent.llm.openai.openai_complete_if_cache`
262. `2026-04-07T03:35:37` `chat` / `qwen3.5-flash` input=3468 output=657 total=4125 source=`ragent.llm.openai.openai_complete_if_cache`
263. `2026-04-07T03:35:37` `chat` / `qwen3.5-flash` input=3343 output=745 total=4088 source=`ragent.llm.openai.openai_complete_if_cache`
264. `2026-04-07T03:35:37` `chat` / `qwen3.5-flash` input=3285 output=634 total=3919 source=`ragent.llm.openai.openai_complete_if_cache`
265. `2026-04-07T03:35:38` `chat` / `qwen3.5-flash` input=3430 output=601 total=4031 source=`ragent.llm.openai.openai_complete_if_cache`
266. `2026-04-07T03:35:38` `chat` / `qwen3.5-flash` input=3343 output=748 total=4091 source=`ragent.llm.openai.openai_complete_if_cache`
267. `2026-04-07T03:35:39` `chat` / `qwen3.5-flash` input=3481 output=1039 total=4520 source=`ragent.llm.openai.openai_complete_if_cache`
268. `2026-04-07T03:35:40` `chat` / `qwen3.5-flash` input=3248 output=881 total=4129 source=`ragent.llm.openai.openai_complete_if_cache`
269. `2026-04-07T03:35:40` `chat` / `qwen3.5-flash` input=3176 output=697 total=3873 source=`ragent.llm.openai.openai_complete_if_cache`
270. `2026-04-07T03:35:40` `chat` / `qwen3.5-flash` input=3285 output=885 total=4170 source=`ragent.llm.openai.openai_complete_if_cache`
271. `2026-04-07T03:35:41` `chat` / `qwen3.5-flash` input=3462 output=930 total=4392 source=`ragent.llm.openai.openai_complete_if_cache`
272. `2026-04-07T03:35:41` `chat` / `qwen3.5-flash` input=4015 output=833 total=4848 source=`ragent.llm.openai.openai_complete_if_cache`
273. `2026-04-07T03:35:42` `chat` / `qwen3.5-flash` input=3742 output=1038 total=4780 source=`ragent.llm.openai.openai_complete_if_cache`
274. `2026-04-07T03:35:48` `chat` / `qwen3.5-flash` input=4129 output=1695 total=5824 source=`ragent.llm.openai.openai_complete_if_cache`
275. `2026-04-07T03:35:50` `chat` / `qwen3.5-flash` input=4191 output=1624 total=5815 source=`ragent.llm.openai.openai_complete_if_cache`
276. `2026-04-07T03:35:51` `chat` / `qwen3.5-flash` input=208 output=60 total=268 source=`ragent.llm.openai.openai_complete_if_cache`
277. `2026-04-07T03:35:51` `chat` / `qwen3.5-flash` input=256 output=101 total=357 source=`ragent.llm.openai.openai_complete_if_cache`
278. `2026-04-07T03:35:51` `chat` / `qwen3.5-flash` input=238 output=107 total=345 source=`ragent.llm.openai.openai_complete_if_cache`
279. `2026-04-07T03:35:51` `chat` / `qwen3.5-flash` input=237 output=104 total=341 source=`ragent.llm.openai.openai_complete_if_cache`
280. `2026-04-07T03:35:51` `chat` / `qwen3.5-flash` input=264 output=103 total=367 source=`ragent.llm.openai.openai_complete_if_cache`
281. `2026-04-07T03:35:51` `chat` / `qwen3.5-flash` input=249 output=133 total=382 source=`ragent.llm.openai.openai_complete_if_cache`
282. `2026-04-07T03:35:51` `chat` / `qwen3.5-flash` input=329 output=121 total=450 source=`ragent.llm.openai.openai_complete_if_cache`
283. `2026-04-07T03:35:51` `chat` / `qwen3.5-flash` input=384 output=131 total=515 source=`ragent.llm.openai.openai_complete_if_cache`
284. `2026-04-07T03:35:51` `chat` / `qwen3.5-flash` input=310 output=146 total=456 source=`ragent.llm.openai.openai_complete_if_cache`
285. `2026-04-07T03:35:51` `chat` / `qwen3.5-flash` input=362 output=154 total=516 source=`ragent.llm.openai.openai_complete_if_cache`
286. `2026-04-07T03:35:51` `chat` / `qwen3.5-flash` input=275 output=169 total=444 source=`ragent.llm.openai.openai_complete_if_cache`
287. `2026-04-07T03:35:51` `chat` / `qwen3.5-flash` input=462 output=173 total=635 source=`ragent.llm.openai.openai_complete_if_cache`
288. `2026-04-07T03:35:52` `chat` / `qwen3.5-flash` input=943 output=250 total=1193 source=`ragent.llm.openai.openai_complete_if_cache`
289. `2026-04-07T03:35:52` `chat` / `qwen3.5-flash` input=698 output=199 total=897 source=`ragent.llm.openai.openai_complete_if_cache`
290. `2026-04-07T03:35:53` `chat` / `qwen3.5-flash` input=336 output=97 total=433 source=`ragent.llm.openai.openai_complete_if_cache`
291. `2026-04-07T03:35:53` `chat` / `qwen3.5-flash` input=267 output=71 total=338 source=`ragent.llm.openai.openai_complete_if_cache`
292. `2026-04-07T03:35:53` `chat` / `qwen3.5-flash` input=614 output=99 total=713 source=`ragent.llm.openai.openai_complete_if_cache`
293. `2026-04-07T03:35:53` `chat` / `qwen3.5-flash` input=434 output=121 total=555 source=`ragent.llm.openai.openai_complete_if_cache`
294. `2026-04-07T03:35:53` `chat` / `qwen3.5-flash` input=304 output=107 total=411 source=`ragent.llm.openai.openai_complete_if_cache`
295. `2026-04-07T03:35:54` `chat` / `qwen3.5-flash` input=298 output=141 total=439 source=`ragent.llm.openai.openai_complete_if_cache`
296. `2026-04-07T03:35:59` `chat` / `qwen3.5-flash` input=1432 output=1250 total=2682 source=`ragent.llm.openai.openai_complete_if_cache`
297. `2026-04-07T03:35:59` `embedding` / `text-embedding-v3` input=260 output=0 total=260 source=`ragent.llm.openai.openai_embed`
298. `2026-04-07T03:35:59` `embedding` / `text-embedding-v3` input=832 output=0 total=832 source=`ragent.llm.openai.openai_embed`
299. `2026-04-07T03:35:59` `embedding` / `text-embedding-v3` input=437 output=0 total=437 source=`ragent.llm.openai.openai_embed`
300. `2026-04-07T03:35:59` `embedding` / `text-embedding-v3` input=475 output=0 total=475 source=`ragent.llm.openai.openai_embed`
301. `2026-04-07T03:35:59` `embedding` / `text-embedding-v3` input=465 output=0 total=465 source=`ragent.llm.openai.openai_embed`
302. `2026-04-07T03:35:59` `embedding` / `text-embedding-v3` input=397 output=0 total=397 source=`ragent.llm.openai.openai_embed`
303. `2026-04-07T03:35:59` `embedding` / `text-embedding-v3` input=614 output=0 total=614 source=`ragent.llm.openai.openai_embed`
304. `2026-04-07T03:35:59` `embedding` / `text-embedding-v3` input=354 output=0 total=354 source=`ragent.llm.openai.openai_embed`
305. `2026-04-07T03:36:00` `embedding` / `text-embedding-v3` input=368 output=0 total=368 source=`ragent.llm.openai.openai_embed`
306. `2026-04-07T03:36:00` `embedding` / `text-embedding-v3` input=276 output=0 total=276 source=`ragent.llm.openai.openai_embed`
307. `2026-04-07T03:36:00` `embedding` / `text-embedding-v3` input=330 output=0 total=330 source=`ragent.llm.openai.openai_embed`
308. `2026-04-07T03:36:00` `embedding` / `text-embedding-v3` input=335 output=0 total=335 source=`ragent.llm.openai.openai_embed`
309. `2026-04-07T03:36:00` `embedding` / `text-embedding-v3` input=1069 output=0 total=1069 source=`ragent.llm.openai.openai_embed`
310. `2026-04-07T03:36:00` `embedding` / `text-embedding-v3` input=295 output=0 total=295 source=`ragent.llm.openai.openai_embed`
311. `2026-04-07T03:36:00` `embedding` / `text-embedding-v3` input=361 output=0 total=361 source=`ragent.llm.openai.openai_embed`
312. `2026-04-07T03:36:00` `embedding` / `text-embedding-v3` input=2709 output=0 total=2709 source=`ragent.llm.openai.openai_embed`
313. `2026-04-07T03:36:00` `embedding` / `text-embedding-v3` input=341 output=0 total=341 source=`ragent.llm.openai.openai_embed`
314. `2026-04-07T03:36:00` `embedding` / `text-embedding-v3` input=374 output=0 total=374 source=`ragent.llm.openai.openai_embed`
315. `2026-04-07T03:36:00` `embedding` / `text-embedding-v3` input=270 output=0 total=270 source=`ragent.llm.openai.openai_embed`
316. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=337 output=0 total=337 source=`ragent.llm.openai.openai_embed`
317. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=525 output=0 total=525 source=`ragent.llm.openai.openai_embed`
318. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=304 output=0 total=304 source=`ragent.llm.openai.openai_embed`
319. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=464 output=0 total=464 source=`ragent.llm.openai.openai_embed`
320. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=362 output=0 total=362 source=`ragent.llm.openai.openai_embed`
321. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=306 output=0 total=306 source=`ragent.llm.openai.openai_embed`
322. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=385 output=0 total=385 source=`ragent.llm.openai.openai_embed`
323. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=288 output=0 total=288 source=`ragent.llm.openai.openai_embed`
324. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=319 output=0 total=319 source=`ragent.llm.openai.openai_embed`
325. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=384 output=0 total=384 source=`ragent.llm.openai.openai_embed`
326. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=323 output=0 total=323 source=`ragent.llm.openai.openai_embed`
327. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=394 output=0 total=394 source=`ragent.llm.openai.openai_embed`
328. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=289 output=0 total=289 source=`ragent.llm.openai.openai_embed`
329. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=307 output=0 total=307 source=`ragent.llm.openai.openai_embed`
330. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=278 output=0 total=278 source=`ragent.llm.openai.openai_embed`
331. `2026-04-07T03:36:01` `embedding` / `text-embedding-v3` input=359 output=0 total=359 source=`ragent.llm.openai.openai_embed`
332. `2026-04-07T03:36:02` `embedding` / `text-embedding-v3` input=414 output=0 total=414 source=`ragent.llm.openai.openai_embed`
333. `2026-04-07T03:36:02` `embedding` / `text-embedding-v3` input=335 output=0 total=335 source=`ragent.llm.openai.openai_embed`
334. `2026-04-07T03:36:02` `embedding` / `text-embedding-v3` input=335 output=0 total=335 source=`ragent.llm.openai.openai_embed`
335. `2026-04-07T03:36:02` `embedding` / `text-embedding-v3` input=349 output=0 total=349 source=`ragent.llm.openai.openai_embed`
336. `2026-04-07T03:36:02` `embedding` / `text-embedding-v3` input=375 output=0 total=375 source=`ragent.llm.openai.openai_embed`
337. `2026-04-07T03:36:02` `embedding` / `text-embedding-v3` input=329 output=0 total=329 source=`ragent.llm.openai.openai_embed`
338. `2026-04-07T03:36:02` `embedding` / `text-embedding-v3` input=397 output=0 total=397 source=`ragent.llm.openai.openai_embed`
339. `2026-04-07T03:36:02` `embedding` / `text-embedding-v3` input=372 output=0 total=372 source=`ragent.llm.openai.openai_embed`
340. `2026-04-07T03:36:02` `embedding` / `text-embedding-v3` input=358 output=0 total=358 source=`ragent.llm.openai.openai_embed`
341. `2026-04-07T03:36:02` `embedding` / `text-embedding-v3` input=360 output=0 total=360 source=`ragent.llm.openai.openai_embed`
342. `2026-04-07T03:36:02` `embedding` / `text-embedding-v3` input=311 output=0 total=311 source=`ragent.llm.openai.openai_embed`
343. `2026-04-07T03:36:02` `embedding` / `text-embedding-v3` input=330 output=0 total=330 source=`ragent.llm.openai.openai_embed`
344. `2026-04-07T03:36:02` `embedding` / `text-embedding-v3` input=350 output=0 total=350 source=`ragent.llm.openai.openai_embed`
345. `2026-04-07T03:36:02` `embedding` / `text-embedding-v3` input=349 output=0 total=349 source=`ragent.llm.openai.openai_embed`
346. `2026-04-07T03:36:02` `embedding` / `text-embedding-v3` input=381 output=0 total=381 source=`ragent.llm.openai.openai_embed`
347. `2026-04-07T03:36:03` `embedding` / `text-embedding-v3` input=746 output=0 total=746 source=`ragent.llm.openai.openai_embed`
348. `2026-04-07T03:36:03` `embedding` / `text-embedding-v3` input=734 output=0 total=734 source=`ragent.llm.openai.openai_embed`
349. `2026-04-07T03:36:05` `embedding` / `text-embedding-v3` input=80 output=0 total=80 source=`ragent.llm.openai.openai_embed`
350. `2026-04-07T03:36:05` `embedding` / `text-embedding-v3` input=53 output=0 total=53 source=`ragent.llm.openai.openai_embed`
351. `2026-04-07T03:36:05` `embedding` / `text-embedding-v3` input=32 output=0 total=32 source=`ragent.llm.openai.openai_embed`
352. `2026-04-07T03:36:05` `embedding` / `text-embedding-v3` input=83 output=0 total=83 source=`ragent.llm.openai.openai_embed`
353. `2026-04-07T03:36:05` `embedding` / `text-embedding-v3` input=74 output=0 total=74 source=`ragent.llm.openai.openai_embed`
354. `2026-04-07T03:36:07` `chat` / `qwen3.5-flash` input=2416 output=195 total=2611 source=`ragent.llm.openai.openai_complete_if_cache`
355. `2026-04-07T03:36:07` `chat` / `qwen3.5-flash` input=2453 output=217 total=2670 source=`ragent.llm.openai.openai_complete_if_cache`
356. `2026-04-07T03:36:08` `chat` / `qwen3.5-flash` input=2456 output=316 total=2772 source=`ragent.llm.openai.openai_complete_if_cache`
357. `2026-04-07T03:36:08` `chat` / `qwen3.5-flash` input=2465 output=346 total=2811 source=`ragent.llm.openai.openai_complete_if_cache`
358. `2026-04-07T03:36:10` `chat` / `qwen3.5-flash` input=2438 output=528 total=2966 source=`ragent.llm.openai.openai_complete_if_cache`
359. `2026-04-07T03:36:11` `chat` / `qwen3.5-flash` input=3094 output=379 total=3473 source=`ragent.llm.openai.openai_complete_if_cache`
360. `2026-04-07T03:36:12` `chat` / `qwen3.5-flash` input=3035 output=551 total=3586 source=`ragent.llm.openai.openai_complete_if_cache`
361. `2026-04-07T03:36:16` `chat` / `qwen3.5-flash` input=3235 output=1016 total=4251 source=`ragent.llm.openai.openai_complete_if_cache`
362. `2026-04-07T03:36:16` `chat` / `qwen3.5-flash` input=3196 output=901 total=4097 source=`ragent.llm.openai.openai_complete_if_cache`
363. `2026-04-07T03:36:17` `chat` / `qwen3.5-flash` input=3390 output=705 total=4095 source=`ragent.llm.openai.openai_complete_if_cache`
364. `2026-04-07T03:36:18` `chat` / `qwen3.5-flash` input=225 output=98 total=323 source=`ragent.llm.openai.openai_complete_if_cache`
365. `2026-04-07T03:36:18` `chat` / `qwen3.5-flash` input=259 output=87 total=346 source=`ragent.llm.openai.openai_complete_if_cache`
366. `2026-04-07T03:36:20` `chat` / `qwen3.5-flash` input=532 output=260 total=792 source=`ragent.llm.openai.openai_complete_if_cache`
367. `2026-04-07T03:36:21` `chat` / `qwen3.5-flash` input=264 output=83 total=347 source=`ragent.llm.openai.openai_complete_if_cache`
368. `2026-04-07T03:36:22` `embedding` / `text-embedding-v3` input=348 output=0 total=348 source=`ragent.llm.openai.openai_embed`
369. `2026-04-07T03:36:22` `embedding` / `text-embedding-v3` input=357 output=0 total=357 source=`ragent.llm.openai.openai_embed`
370. `2026-04-07T03:36:22` `embedding` / `text-embedding-v3` input=342 output=0 total=342 source=`ragent.llm.openai.openai_embed`
371. `2026-04-07T03:36:22` `embedding` / `text-embedding-v3` input=357 output=0 total=357 source=`ragent.llm.openai.openai_embed`
372. `2026-04-07T03:36:22` `embedding` / `text-embedding-v3` input=326 output=0 total=326 source=`ragent.llm.openai.openai_embed`
373. `2026-04-07T03:36:22` `embedding` / `text-embedding-v3` input=663 output=0 total=663 source=`ragent.llm.openai.openai_embed`
374. `2026-04-07T03:36:22` `embedding` / `text-embedding-v3` input=600 output=0 total=600 source=`ragent.llm.openai.openai_embed`
375. `2026-04-07T03:36:22` `embedding` / `text-embedding-v3` input=614 output=0 total=614 source=`ragent.llm.openai.openai_embed`
376. `2026-04-07T03:36:22` `embedding` / `text-embedding-v3` input=523 output=0 total=523 source=`ragent.llm.openai.openai_embed`
377. `2026-04-07T03:36:22` `embedding` / `text-embedding-v3` input=506 output=0 total=506 source=`ragent.llm.openai.openai_embed`
378. `2026-04-07T03:36:22` `embedding` / `text-embedding-v3` input=219 output=0 total=219 source=`ragent.llm.openai.openai_embed`
