"""
修复 hybrid_model.pkl 中的模块路径问题。

当 pkl 文件是通过直接运行 `python hybrid.py` 保存时，
pickle 会把类路径记录为 `__main__.HybridRecommender`，
导致在 Flask 应用中无法加载。

此脚本通过 pickle 的 Unpickler 钩子，将 __main__ 路径重定向到正确的模块，
然后重新保存模型。在 backend/ 目录下运行：
    python fix_pkl.py
"""

import pickle
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ml.hybrid import HybridRecommender
from ml.train_mf import MatrixFactorizationALS
from ml.content_based import ContentBasedRecommender


CLASS_MAP = {
    ("__main__", "HybridRecommender"): HybridRecommender,
    ("__main__", "MatrixFactorizationALS"): MatrixFactorizationALS,
    ("__main__", "ContentBasedRecommender"): ContentBasedRecommender,
}


class FixedUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        key = (module, name)
        if key in CLASS_MAP:
            print(f"  重定向: {module}.{name}  ->  {CLASS_MAP[key].__module__}.{name}")
            return CLASS_MAP[key]
        return super().find_class(module, name)


def fix_pkl(input_path, output_path=None):
    if output_path is None:
        output_path = input_path

    print(f"加载: {input_path}")
    with open(input_path, "rb") as f:
        model = FixedUnpickler(f).load()

    print(f"加载成功")
    print(f"  模型类型: {type(model).__module__}.{type(model).__name__}")
    print(f"  alpha:    {model.alpha}")
    print(f"  ALS 类型: {type(model.als_model).__module__}.{type(model.als_model).__name__}")
    print(f"  Content:  {type(model.content_model).__module__}.{type(model.content_model).__name__}")

    print(f"\n重新保存: {output_path}")
    with open(output_path, "wb") as f:
        pickle.dump(model, f)

    print("完成！再次启动后端即可正常加载 ML 推荐系统。")


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pkl_path = os.path.join(base, "data", "output5", "hybrid_model.pkl")
    fix_pkl(pkl_path)
