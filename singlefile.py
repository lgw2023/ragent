import sys
import asyncio
import os
import logging
try:
    # Package execution (e.g., python -m ragent.singlefile)
    from .integrations import (
        pdf_insert,
        build_enhanced_md,
        index_md_to_rag,
        inference_one_hop_problem,
        inference_multi_hop_problem,
    )
    from .ragent.utils import logger
except ImportError:
    # Script execution (e.g., python singlefile.py ...)
    from integrations import (
        pdf_insert,
        build_enhanced_md,
        index_md_to_rag,
        inference_one_hop_problem,
        inference_multi_hop_problem,
    )
    from ragent.utils import logger

class RagentApp:
    def __init__(self, project_dir: str | None = None, mineru_output_dir: str | None = None):
        self.project_dir = project_dir
        self.mineru_output_dir = mineru_output_dir

    async def parse(
        self,
        pdf_file_path: str,
        mineru_output_dir: str | None = None,
        project_dir: str | None = None,
        stage: str = "auto",
        keep_pdf_subdir: bool = True,
    ):
        target_output_dir = mineru_output_dir or self.mineru_output_dir
        target_project_dir = project_dir or self.project_dir
        valid_stages = {"auto", "all", "md", "rag"}
        if stage not in valid_stages:
            raise ValueError("Invalid stage. Use one of: auto | all | md | rag")

        if not pdf_file_path:
            raise ValueError("Missing required argument: pdf_file_path")

        if stage in {"auto", "all", "md"} and not target_output_dir:
            raise ValueError("Missing required argument for md stage: mineru_output_dir")

        if stage in {"all", "rag"} and not target_project_dir:
            raise ValueError("Missing required argument for rag stage: project_dir")

        resolved_stage = stage
        if stage == "auto":
            # 自动规则：
            # 1) 未提供 project_dir -> 仅做 md
            # 2) 提供 project_dir 且已有对应 md -> 仅做 rag
            # 3) 提供 project_dir 且无 md -> 做 all
            if not target_project_dir:
                resolved_stage = "md"
            else:
                md_path = self._resolve_existing_md_path(
                    pdf_file_path,
                    target_output_dir,
                    keep_pdf_subdir=keep_pdf_subdir,
                )
                resolved_stage = "rag" if md_path else "all"
            logger.info(f"自动推断阶段: {resolved_stage}")

        if resolved_stage == "all":
            logger.info("开始提取PDF并构建知识库...")
            await pdf_insert(
                pdf_file_path,
                target_output_dir,
                target_project_dir,
                keep_pdf_subdir=keep_pdf_subdir,
            )
            logger.info("PDF提取与知识库构建完成。")
            return

        if resolved_stage == "md":
            logger.info("开始提取PDF并生成增强 md...")
            artifacts = await build_enhanced_md(
                pdf_file_path,
                target_output_dir,
                keep_pdf_subdir=keep_pdf_subdir,
            )
            logger.info(f"增强 md 生成完成: {artifacts['md_path']}")
            return

        # resolved_stage == "rag"
        # 仅构建 RAG/KG：依赖已经存在的最终 md 文件
        md_path = self._resolve_existing_md_path(
            pdf_file_path,
            target_output_dir,
            keep_pdf_subdir=keep_pdf_subdir,
        )
        if not md_path:
            pdf_name = os.path.basename(pdf_file_path).rsplit(".", 1)[0]
            md_path_new = os.path.join(target_output_dir, "txt", f"{pdf_name}.md")
            md_path_old = os.path.join(target_output_dir, pdf_name, "txt", f"{pdf_name}.md")
            raise FileNotFoundError(
                f"未找到最终 md 文件，请先执行 md 阶段: {md_path_new} 或 {md_path_old}"
            )
        logger.info(f"开始基于最终 md 构建知识库: {md_path}")
        await index_md_to_rag(pdf_file_path, target_project_dir, md_path)
        logger.info("知识库构建完成。")

    @staticmethod
    def _resolve_existing_md_path(
        pdf_file_path: str,
        mineru_output_dir: str | None,
        keep_pdf_subdir: bool = True,
    ) -> str | None:
        if not mineru_output_dir:
            return None

        pdf_name = os.path.basename(pdf_file_path).rsplit(".", 1)[0]
        candidate_paths = []
        if keep_pdf_subdir:
            candidate_paths.append(os.path.join(mineru_output_dir, pdf_name, "txt", f"{pdf_name}.md"))
            candidate_paths.append(os.path.join(mineru_output_dir, "txt", f"{pdf_name}.md"))
        else:
            candidate_paths.append(os.path.join(mineru_output_dir, "txt", f"{pdf_name}.md"))
            candidate_paths.append(os.path.join(mineru_output_dir, pdf_name, "txt", f"{pdf_name}.md"))

        for md_path in candidate_paths:
            if os.path.exists(md_path):
                return md_path
        return None

    async def onehop(self, simple_query: str | None = None, project_dir: str | None = None, mode: str = "hybrid"):
        target_project_dir = project_dir or self.project_dir
        if not target_project_dir:
            raise ValueError("Missing required argument: project_dir")
        query = "文档的主要主题是什么？" if not simple_query else simple_query
        answer = await inference_one_hop_problem(target_project_dir, query, mode=mode)
        logger.info(f"查询: {query}")
        logger.info(f"答案: {answer}")
        return answer

    async def multihop(self, complex_query: str | None = None, project_dir: str | None = None):
        target_project_dir = project_dir or self.project_dir
        if not target_project_dir:
            raise ValueError("Missing required argument: project_dir")
        query = "比较第2节和第3节中描述的方法，它们的主要区别是什么？" if not complex_query else complex_query
        answer = await inference_multi_hop_problem(target_project_dir, query)
        logger.info(f"查询: {query}")
        logger.info(f"答案: {answer}")
        return answer


async def main(
    MODULE,
    PDF_FILE_PATH: str | None = None,
    MINERU_OUTPUT_DIR: str | None = None,
    PROJECT_DIR: str | None = None,
    simple_query: str | None = None,
    complex_query: str | None = None,
    stage: str = "auto",
    keep_pdf_subdir: bool = True,
):
    app = RagentApp(PROJECT_DIR, MINERU_OUTPUT_DIR)
    if MODULE == "parse":
        await app.parse(PDF_FILE_PATH, stage=stage, keep_pdf_subdir=keep_pdf_subdir)
        return
    elif MODULE == "onehop":
        return await app.onehop(simple_query)
    elif MODULE == "multihop":
        return await app.multihop(complex_query)
    else:
        raise ValueError(f"Invalid module: {MODULE}")

if __name__ == "__main__":
    MODULE, PDF_FILE_PATH, MINERU_OUTPUT_DIR, PROJECT_DIR, simple_query, complex_query, stage = None, None, None, None, None, None, "auto"
    BATCH_PARSE = False
    KEEP_PDF_SUBDIR = True
    MODULE = sys.argv[1] # : "parse" | "onehop" | "multihop"
    if MODULE == "parse":
        # 支持：
        # 1) parse <pdf_or_dir> <mineru_output_dir>
        #    - 自动推断 stage=md
        # 2) parse <pdf_or_dir> <mineru_output_dir> <project_dir>
        #    - 自动推断 stage=all/rag（有 md 即 rag，否则 all）
        # 3) parse <pdf_or_dir> <mineru_output_dir> [project_dir] [stage]
        #    - 可选手动覆盖 stage（auto/all/md/rag）
        if len(sys.argv) < 4:
            raise ValueError("Usage: parse <pdf_or_dir> <mineru_output_dir> [project_dir] [stage]")

        PDF_FILE_PATH = sys.argv[2] # "path/to/your/document.pdf"
        MINERU_OUTPUT_DIR = sys.argv[3] # "mineru_out"  # 存储解析结果的目录

        valid_stages = {"auto", "all", "md", "rag"}
        arg4 = sys.argv[4] if len(sys.argv) > 4 else None
        arg5 = sys.argv[5] if len(sys.argv) > 5 else None

        if arg4 in valid_stages:
            stage = arg4
            PROJECT_DIR = None
        else:
            PROJECT_DIR = arg4
            stage = arg5 if arg5 else "auto"

        if stage not in valid_stages:
            raise ValueError(f"Invalid stage: {stage}. Use one of: auto | all | md | rag")
        # 如果传入的是目录，则批量遍历解析其中的 PDF 文档
        if os.path.isdir(PDF_FILE_PATH):
            BATCH_PARSE = True
            KEEP_PDF_SUBDIR = True
            valid_exts = {".pdf"}
            file_list = []
            for root, dirs, files in os.walk(PDF_FILE_PATH):
                for name in files:
                    ext = os.path.splitext(name)[1].lower()
                    if ext in valid_exts:
                        file_list.append(os.path.join(root, name))
            if not file_list:
                logger.info(f"未在目录中找到可解析文件: {PDF_FILE_PATH}")
            else:
                logger.info(f"在目录中找到 {len(file_list)} 个待解析文件")
            for idx, fp in enumerate(sorted(file_list)):
                logger.info(f"[{idx + 1}/{len(file_list)}] 开始解析: {fp}")
                try:
                    # 目录模式下逐文件自动推断：
                    # 无 project_dir -> md；有 project_dir 时，已有 md -> rag，否则 all
                    per_file_stage = stage
                    if stage == "auto":
                        if PROJECT_DIR:
                            existing_md = RagentApp._resolve_existing_md_path(
                                fp,
                                MINERU_OUTPUT_DIR,
                                keep_pdf_subdir=True,
                            )
                            per_file_stage = "rag" if existing_md else "all"
                        else:
                            per_file_stage = "md"
                    asyncio.run(
                        main(
                            "parse",
                            fp,
                            MINERU_OUTPUT_DIR,
                            PROJECT_DIR,
                            None,
                            None,
                            per_file_stage,
                            keep_pdf_subdir=True,
                        )
                    )
                except Exception as e:
                    logger.error(f"解析失败: {fp} - {e}")
        else:
            KEEP_PDF_SUBDIR = False
    elif MODULE == "onehop":
        PROJECT_DIR = sys.argv[2] # "my_ragent_project"  # 存储知识库的目录
        simple_query = sys.argv[3] # "文档的主要主题是什么？"
    elif MODULE == "multihop":
        PROJECT_DIR = sys.argv[2] # "my_ragent_project"  # 存储知识库的目录
        complex_query = sys.argv[3] # "比较第2节和第3节中描述的方法，它们的主要区别是什么？"
    else:
        raise ValueError(f"Invalid module: {MODULE}")
    # 仅当不是目录批量模式时才调用一次
    if not BATCH_PARSE:
        asyncio.run(
            main(
                MODULE,
                PDF_FILE_PATH,
                MINERU_OUTPUT_DIR,
                PROJECT_DIR,
                simple_query,
                complex_query,
                stage,
                keep_pdf_subdir=KEEP_PDF_SUBDIR,
            )
        )