import json
import os
import sys
import requests
import subprocess
from pathlib import Path

from mineru.utils.enum_class import ModelPath
from mineru.utils.models_download_utils import auto_download_and_get_model_root_path


def download_json(url):
    """下载JSON文件"""
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def download_and_modify_json(url, local_filename, modifications):
    """下载JSON并修改内容"""
    if os.path.exists(local_filename):
        data = json.load(open(local_filename))
        config_version = data.get('config_version', '0.0.0')
        if config_version < '1.3.0':
            data = download_json(url)
    else:
        data = download_json(url)

    # 修改内容
    for key, value in modifications.items():
        if key in data:
            if isinstance(data[key], dict):
                # 如果是字典，合并新值
                data[key].update(value)
            else:
                # 否则直接替换
                data[key] = value

    # 保存修改后的内容
    with open(local_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def configure_model(model_dir, model_type):
    """配置模型"""
    json_url = 'https://gcore.jsdelivr.net/gh/opendatalab/MinerU@master/mineru.template.json'
    config_file_name = os.getenv('MINERU_TOOLS_CONFIG_JSON', 'mineru.json')
    home_dir = os.path.expanduser('~')
    config_file = os.path.join(home_dir, config_file_name)

    json_mods = {
        'models-dir': {
            f'{model_type}': model_dir
        }
    }

    download_and_modify_json(json_url, config_file, json_mods)
    print(f'The configuration file has been successfully configured, the path is: {config_file}')

def download_models(model_source, model_type):
    """Download MinerU model files.

    Supports downloading pipeline or VLM models from ModelScope or HuggingFace.
    """
    # 如果未显式指定则交互式输入下载来源
    if model_source is None:
        # model_source = click.prompt(
        #     "Please select the model download source: ",
        #     type=click.Choice(['huggingface', 'modelscope']),
        #     default='huggingface'
        # )
        return
    if os.getenv('MINERU_MODEL_SOURCE', None) is None:
        os.environ['MINERU_MODEL_SOURCE'] = model_source

    # 如果未显式指定则交互式输入模型类型
    if model_type is None:
        # model_type = click.prompt(
        #     "Please select the model type to download: ",
        #     type=click.Choice(['pipeline', 'vlm', 'all']),
        #     default='all'
        # )
        return

    # click.echo(f"Downloading {model_type} model from {os.getenv('MINERU_MODEL_SOURCE', None)}...")

    def download_pipeline_models():
        """下载Pipeline模型"""
        model_paths = [
            ModelPath.doclayout_yolo,
            ModelPath.yolo_v8_mfd,
            ModelPath.unimernet_small,
            ModelPath.pytorch_paddle,
            ModelPath.layout_reader,
            ModelPath.slanet_plus
        ]
        download_finish_path = ""
        for model_path in model_paths:
            # click.echo(f"Downloading model: {model_path}")
            download_finish_path = auto_download_and_get_model_root_path(model_path, repo_mode='pipeline')
        # click.echo(f"Pipeline models downloaded successfully to: {download_finish_path}")
        configure_model(download_finish_path, "pipeline")

    def download_vlm_models():
        """下载VLM模型"""
        download_finish_path = auto_download_and_get_model_root_path("/", repo_mode='vlm')
        # click.echo(f"VLM models downloaded successfully to: {download_finish_path}")
        configure_model(download_finish_path, "vlm")

    try:
        if model_type == 'pipeline':
            download_pipeline_models()
        elif model_type == 'vlm':
            download_vlm_models()
        elif model_type == 'all':
            download_pipeline_models()
            download_vlm_models()
        else:
            # click.echo(f"Unsupported model type: {model_type}", err=True)
            sys.exit(1)

    except Exception as e:
        # click.echo(f"Download failed: {str(e)}", err=True)
        sys.exit(1)


def run_pdf_parser_gui():
    """运行PDF解析器GUI"""
    try:
        # 使用subprocess替代os.system
        python_exe = Path('.') / 'env' / 'python.exe'
        script_path = Path('.') / 'pdf_parser_gui.py'
        
        if not python_exe.exists():
            print(f"错误: Python可执行文件不存在 - {python_exe}")
            sys.exit(1)
            
        if not script_path.exists():
            print(f"错误: PDF解析器脚本不存在 - {script_path}")
            sys.exit(1)
            
        print(f"正在启动PDF解析器: {script_path}")
        os.system(f"{str(python_exe)} {str(script_path)}") 
        # subprocess.run([str(python_exe), str(script_path)], check=True)
    except Exception as e:
        print(f"启动PDF解析器时发生未知错误: {e}")
        sys.exit(1)

def get_config_file_path():
    """获取配置文件路径"""
    config_file_name = os.getenv('MINERU_TOOLS_CONFIG_JSON', 'mineru.json')
    home_dir = os.path.expanduser('~')
    return os.path.join(home_dir, config_file_name)

if __name__ == '__main__':
    # 构建nineru.json配置文件路径
    # config_file_name = os.getenv('MINERU_TOOLS_CONFIG_JSON', 'mineru.json')
    # home_dir = os.path.expanduser('~')
    # local_filename = os.path.join(home_dir, config_file_name)
    # # 判断用户是否存在，表示模型是否下载好
    # if not os.path.exists(local_filename):
    #     download_models("modelscope", "pipeline")

    # if os.path.exists(local_filename):
    #     os.system(".\env\python.exe .\pdf_parser_gui.py") 

    # 检查配置文件是否存在，判断模型是否下载好
    config_file = get_config_file_path()
    if not os.path.exists(config_file):
        print("检测到未配置的环境，开始下载模型...")
        download_models("modelscope", "pipeline")
    else:
        print(f"找到现有配置文件: {config_file}")

    # 无论模型是否下载，都尝试启动GUI
    print("启动PDF解析器...")
    run_pdf_parser_gui()