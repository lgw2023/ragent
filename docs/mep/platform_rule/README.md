# MEP Platform Rule References

这个目录保存 MEP 平台规则、问答、样例组件和本项目离线验证脚本。它是参考资料集合，不是单一权威规格。判断时效性时同时看两类信号：

- 文件修改时间：来自当前仓库文件系统时间。
- 文档内维护日期：部分 WIKI 导出文本包含创建/最后修改时间。

截至 2026-05-23，建议按下面顺序使用。

## 当前可执行

这些文件直接服务当前 Qwen3-Embedding-4B MEP 离线交付链路，优先级最高。

| 文件 | 时间信号 | 用途 | 时效性判断 |
|---|---:|---|---|
| [Validated_ragent-mep-test_docker_full_chain.sh](Validated_ragent-mep-test_docker_full_chain.sh) | 2026-05-22 21:33 | Ascend/vLLM 镜像内完整组件链路验证 | 当前可执行脚本 |
| [Validated_ragent-mep-test_docker_vllm.sh](Validated_ragent-mep-test_docker_vllm.sh) | 2026-05-22 17:41 | 单独验证 vLLM embedding 服务 | 当前可执行脚本 |
| [Validated_ragent-mep-test_docker_vllm_requirements.freeze.txt](Validated_ragent-mep-test_docker_vllm_requirements.freeze.txt) | 2026-05-12 19:51 | 已验证容器的 Python freeze 快照 | 当前环境快照，随镜像变化需重采集 |

## 近期结论

这些文件是 2026-05 中旬围绕 `qwen_vllm_async_copilot` 和 MEP 异步链路整理出来的问题确认材料。它们比旧 WIKI 摘录更贴近当前项目实现。

| 文件 | 时间信号 | 用途 | 时效性判断 |
|---|---:|---|---|
| [MEP-QA/MEP-question.md](MEP-QA/MEP-question.md) | 2026-05-12 19:51 | 向平台同事确认的问题清单 | 背景问题清单 |
| [MEP-QA/MEP-answer/Answer_Q10.md](MEP-QA/MEP-answer/Answer_Q10.md) | 2026-05-19 09:51 | `recommendResult.content` 与 `generatePath/gen.json` 的消费关系 | 近期结论，优先参考 |
| [MEP-QA/MEP-answer/](MEP-QA/MEP-answer/) | 2026-05-12 至 2026-05-19 | 路径、生命周期、vLLM、SFS、返回结构等问答 | 近期结论，遇到平台实测冲突时以实测为准 |
| [组件包项目样例-qwen_vllm_async_copilot-README.md](组件包项目样例-qwen_vllm_async_copilot-README.md) | 2026-05-18 20:35 | 样例组件包结构和开发说明 | 近期样例说明 |
| [组件包项目样例-qwen_vllm_async_copilot-Response.md](组件包项目样例-qwen_vllm_async_copilot-Response.md) | 2026-05-12 19:51 | 对样例组件与异步模板差异的分析 | 近期分析材料 |
| [qwen_vllm_async_copilot/](qwen_vllm_async_copilot/) | 2026-05-12 19:51 | 样例组件核心入口文件摘录 | 近期样例代码摘录，不是本项目运行代码 |

## 平台参考

这些材料是平台文档或接口文档摘录。部分文件名较老，但文档内维护日期显示仍有 2025/2026 更新；使用时应优先采纳接口契约、目录约定和生命周期描述，不要直接照搬旧示例代码。

| 文件 | 文档内时间或文件时间 | 用途 | 时效性判断 |
|---|---:|---|---|
| [others/异步场景组件包开发指南 异步场景组件包接口说明 WIKI2021101206450.txt](others/异步场景组件包开发指南%20异步场景组件包接口说明%20WIKI2021101206450.txt) | 文件 2026-05-18 20:36 | SFS 异步组件接口说明 | 近期导入，旧 WIKI 编号不等于失效 |
| [others/(3) 异步推理框架使用指导 .md](others/%283%29%20异步推理框架使用指导%20.md) | 2026-05-18 21:00 | 异步推理框架使用说明 | 近期导入，适合作为 MSG/SFS 流程参考 |
| [others/MEP Python异步推理框架调用示例 .md](others/MEP%20Python异步推理框架调用示例%20.md) | 2026-05-18 21:00 | Python 异步框架调用示例 | 近期导入，示例需结合当前契约复核 |
| [others/MEP Python非SFS异步框架容器接口文档.txt](others/MEP%20Python非SFS异步框架容器接口文档.txt) | 文档内最后修改 2025-11-12，文件 2026-05-19 | 非 SFS 异步接口 | 辅助参考，不是当前 SFS 主路径 |
| [others/异步推理框架MSG以及POD_IP调用示例.txt](others/异步推理框架MSG以及POD_IP调用示例.txt) | 2026-05-19 09:41 | MSG/POD_IP 调用示例 | 近期导入，适合核对业务调用链 |
| [others/模型调测.txt](others/模型调测.txt) | 2026-05-19 09:41 | 平台模型调测流程 | 近期导入，按目标平台版本复核 |

## 历史背景

这些文件主要用于理解平台历史语义和包结构来源，不能直接作为当前实现的唯一依据。

| 文件 | 文档内时间或文件时间 | 用途 | 时效性判断 |
|---|---:|---|---|
| [others/3.2 模型包 WIKI2022030301666.txt](others/3.2%20模型包%20WIKI2022030301666.txt) | 创建 2022-03-03，最后修改 2025-03-31 | 模型包和云化部署背景 | 历史规格，有 2025 更新但需复核 |
| [others/3.3 代码组件包 WIKI2021101206391.txt](others/3.3%20代码组件包%20WIKI2021101206391.txt) | 创建 2021-03-30，最后修改 2026-03-16 | 组件包基本生命周期 | 老文档但近期维护，可参考生命周期 |
| [others/异步场景组件包接口说明.txt](others/异步场景组件包接口说明.txt) | 2026-05-12 19:51 | 旧异步接口摘录 | 被近期开发指南和 Q10 结论覆盖时以后者为准 |
| [组件包 异步场景.txt](组件包%20异步场景.txt) | 2026-05-12 19:51 | 异步组件返回结构和 SFS 示例 | 历史基础规范，需结合 MSG 新结论 |
| [模型包及pipeline部署.txt](模型包及pipeline部署.txt) | 2026-05-12 19:51 | 模型包和 pipeline 部署背景 | 历史背景 |

## 注意事项

- [MEP_running.yaml](MEP_running.yaml) 是运行环境变量快照，包含平台环境和凭据形态信息；不要把它当作当前部署配置或对外分享材料。
- `qwen_vllm_async_copilot/` 是平台样例代码摘录，不参与本项目运行和打包。
- 遇到本文档与真实 MEP 平台联调结果冲突时，以最新实测记录和 [../offline_full_chain_runbook.md](../offline_full_chain_runbook.md) 为准。
