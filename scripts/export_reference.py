"""用 build123d 保留原始 STEP 的精确几何并重新导出，供核对。

这是几何导入导出，不是参数化特征重建。
"""
from pathlib import Path
from build123d import import_step, export_step

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'data-bin' / '舵机云台总装.step'
target = ROOT / 'model-bin' / '舵机云台_原版几何核对.step'
model = import_step(source)
target.parent.mkdir(exist_ok=True)
if not export_step(model, target):
    raise RuntimeError('STEP export failed')
reloaded = import_step(target)
original = model.solids()
result = reloaded.solids()
assert len(original) == len(result), '实体数量不一致'
for a, b in zip(original, result):
    assert abs(a.volume - b.volume) < max(1e-5, a.volume * 1e-6), '实体体积不一致'
print(f'导出成功：{target}；实体数：{len(result)}；体积核对通过')
