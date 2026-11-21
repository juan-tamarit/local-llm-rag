from huggingface_hub import snapshot_download
from src.model_paths import MODELS_DIR

REPOS = ["Qwen/Qwen2.5-Coder-1.5B-Instruct", "intfloat/multilingual-e5-small"]

for repo in REPOS:
    target = MODELS_DIR / repo.replace("/", "--")
    print("Descargando", repo, "->", target)
    snapshot_download(
        repo_id=repo, local_dir=target,
        ignore_patterns=["*.onnx", "onnx/*", "openvino/*", "*.msgpack", "*.h5", "*.ot"],
    )