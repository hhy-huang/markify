import json
import os
from pathlib import Path

from huggingface_hub import snapshot_download as hf_download
from modelscope.hub.snapshot_download import snapshot_download as ms_download

DEFAULT_CONFIG_NAME = "magic-pdf.json"
GITHUB_TEMPLATE_URL = "https://raw.githubusercontent.com/opendatalab/MinerU/master/magic-pdf.template.json"
MODEL_REPOS = {
    'main': 'opendatalab/PDF-Extract-Kit-1.0',
    'layout': 'hantian/layoutreader'
}


class ModelConfigurator:
    """模型配置管理器"""

    def __init__(self, device='cpu', models_dir=None, use_modelscope=True):
        self.device = device
        self.use_modelscope = use_modelscope
        self.models_dir = models_dir
        self.config_path = self._get_config_path()
        self.mineru_patterns = [
            "models/Layout/LayoutLMv3/*",
            "models/Layout/YOLO/*",
            "models/MFD/YOLO/*",
            "models/MFR/unimernet_small_2501/*",
            "models/TabRec/TableMaster/*",
            "models/TabRec/StructEqTable/*",
        ]
        if self.use_modelscope:
            MODEL_REPOS['layout'] = 'ppaanngggg/layoutreader'

    def _get_cache_dir(self, model_type):
        """获取符合各库规范的缓存目录"""
        if self.models_dir:
            custom_dir = Path(self.models_dir).expanduser().resolve()
            return custom_dir / model_type

        # 自动识别默认缓存路径
        if self.use_modelscope:
            return Path.home() / ".cache/modelscope/hub" / MODEL_REPOS[model_type]
        else:
            return Path.home() / ".cache/huggingface/hub" / MODEL_REPOS[model_type]

    def _get_config_path(self):
        """获取配置文件路径"""
        env_path = os.getenv('MINERU_TOOLS_CONFIG_JSON')
        return Path(env_path) if env_path else Path.home() / DEFAULT_CONFIG_NAME

    def setup_environment(self):
        """配置环境并下载模型"""
        self._download_models()
        self._generate_config()
        os.environ['MINERU_TOOLS_CONFIG_JSON'] = str(self.config_path)

    def _download_models(self):
        """改进后的下载方法"""
        downloader = ms_download if self.use_modelscope else hf_download

        model_paths = {}
        for model_type in ['main', 'layout']:
            cache_dir = self._get_cache_dir(model_type)

            print(f"下载 {model_type} 模型到: {cache_dir}")

            # 保留库的默认缓存行为，仅在指定--models-dir时覆盖
            download_args = {
                'repo_id': MODEL_REPOS[model_type],
                'local_dir': str(cache_dir),  # 新增参数确保文件存储在指定位置
                'allow_patterns': self.mineru_patterns if model_type == 'main' else None  # 添加过滤规则
            }

            # 仅在自定义路径时覆盖缓存目录
            if self.models_dir:
                download_args['cache_dir'] = str(cache_dir.parent)

            snapshot_path = downloader(**download_args)

            # 处理特殊目录结构
            if model_type == 'main':
                self.main_model_path = Path(snapshot_path) / 'models'
            else:
                self.layout_model_path = Path(snapshot_path)

        return model_paths

    def _generate_config(self):
        """生成配置文件"""
        template_path = "assets/magic-pdf-template.json"
        try:
            with open(template_path, "r") as f:
                template_config = json.load(f)
            print(f"成功加载模板配置: {template_path}")
        except Exception as e:
            print(f"加载模板配置失败，使用默认值: {e}")
            template_config = {}

        custom_config = {
            "device-mode": self.device,
            "models-dir": str(self.main_model_path),
            "layoutreader-model-dir": str(self.layout_model_path),
        }
        template_config.update(custom_config)
        config = template_config

        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                existing_config = json.load(f)
            existing_config.update(custom_config)
            config = existing_config

        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
