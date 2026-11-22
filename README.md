# Argus 舵机云台建模

Argus 用 build123d 参数化生成支架、底座和云台头。尺寸、草图轮廓和装配位姿定义在 `src/argus/models/` 下各零件子包的 `parameters.py` 中。修改对应参数后重新运行主命令即可导出。

## 运行

在项目根目录使用 Python 3.11 或 3.12 和 Poetry。

```bash
poetry install
poetry run argus
```

主命令直接使用 Python 参数，在 `model-bin/parametric-parts` 中生成 `gimbal_bracket`、`gimbal_base` 和 `gimbal_head` 的 STEP 和 3MF。STEP 使用代码定义的装配位姿，3MF 按打印朝向居中贴床。该流程可以在没有源 STEP 的环境运行。

底座的底板和两组安装孔共用卡环中心。每组孔的 `offset` 表示一个孔相对中心的 XY 偏移，程序按 90° 旋转生成该组四个孔。

支架以局部 `X=0` 为左右对称面，安装框、双臂、减重窗和卡片由单侧轮廓生成。安装窗以框体为中心，卡片按 `tab_pitch` 上下排列。左侧定位销和右侧轴孔共用 `shaft_axis` 定义的轴线，分别使用各自的配合尺寸。

打印支架复用原支架的参数和装配位姿。两臂下方及前框下方补实到圆端最低点，安装窗、减重窗和轴孔保留。运行 `poetry run argus --bracket-print` 单独导出 `gimbal_bracket_print.step` 和 `gimbal_bracket_print.3mf`。3MF 沿用原支架的安装面贴床朝向。

打印云台头复用原云台头的参数和装配位姿。两侧挡板和最低的小挡块按原有投影向下补到主板底边，主板下方的两个外圆角补成直角，矩形通孔保持贯通。运行 `poetry run argus --head-print` 导出 `gimbal_head_print.step` 和 `gimbal_head_print.3mf`。3MF 沿用原云台头的贴床朝向。

```bash
poetry run argus --output-dir /path/to/output
```

也可以用 `ARGUS_OUTPUT_DIR` 指定输出目录。原有的 `poetry run python scripts/build_gimbal.py` 和主命令调用同一流程。

运行 `poetry run python scripts/export_structural_parts.py` 可以从装配直接导出三个源件，输出到 `model-bin/structural-parts`。这条路径使用源件几何，供拟合结果核对。

## 网页模型工作台

网页需要 Node.js、pnpm 和 Poetry。按锁文件安装后，从仓库根目录构建前端并启动本机服务。

```bash
poetry install
pnpm --dir src/web install --frozen-lockfile
pnpm --dir src/web run build
poetry run uvicorn argus.web.app:app --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000/` 默认进入底座。底座、支架和云台头可通过 `/models/base`、`/models/bracket` 和 `/models/head` 访问，打印版本对应 `/models/bracket-print` 和 `/models/head-print`。切换零件与浏览器前进、后退同步。

修改常用尺寸后点击「重新生成」，生成成功会替换视口里的结果。各零件的参数草稿和预览结果保存在当前网页会话，刷新后留在当前零件，从 Python 默认参数重新开始。

点击模型标题旁的「导出」，可同时选择多个配件和 STEP、3MF、STL 格式。已预览的配件采用各自上次成功生成的尺寸，尚未预览的配件采用默认尺寸。一个文件直接下载，多个文件打包为 `argus-models.zip`。STEP 使用装配位姿，3MF 和 STL 使用居中贴床的打印朝向，STL 使用毫米坐标。

FastAPI 同时提供预览接口并托管 `src/web/dist`。VS Code 的 `backend` 调试配置会先按锁文件安装前端依赖并构建。首次安装需要访问包源，安装或构建报错时会在启动后端前停止。

```bash
pnpm --dir src/web run lint
pnpm --dir src/web run build
pnpm --dir src/web run test
```

浏览器回归使用本机 Google Chrome。

## 可选的源件校准

使用 `--source /path/to/assembly.step` 或 `ARGUS_SOURCE` 可从指定装配量测特征并生成一批拟合结果。装配顶层应包含 `舵机云台-1`、`舵机云台底座-1` 和 `舵机云台头-1`，各有一个有效实体。尺寸变更应沿用零件的局部坐标系和特征结构。

校准流程逐件检查双向布尔差集、边界及圆柱尺寸。差集体积之和须在源件体积的 0.05% 以内，包围盒和边界采样点的偏差、圆柱轴线及直径偏差须在 0.05 mm 以内。

## 发布和验证

同批文件全部通过导出回读检查后发布。发生输入、建模、拟合或回读错误时，命令以非零状态退出并报告原因。

同一输出目录的发布会串行执行。发布锁放在输出目录的同级，文件名为 `.<输出目录名>.argus.lock`。文件替换报错时会回滚已经替换的文件。

运行测试可使用 `poetry run python -m unittest discover`。主入口的测试在无源 STEP 的目录中运行。本地有原装配 STEP 时，测试还会验证原件导出和修改孔径后的校准结果。

## 代码结构

- `assembly.py` 负责零件标签、文件名、打印朝向和装配 STEP 读取。
- `models/base/`、`models/bracket/` 和 `models/head/` 分别维护底座、支架和云台头的建模逻辑与参数。
- `models/bracket_print/` 和 `models/head_print/` 复用原件特征及参数，生成补平后的打印版本。
- `models/common.py` 提供各模型共用的 CAD 原语。
- `fitting.py` 负责从参考几何量测参数及验收拟合结果。
- `exporting.py` 负责装配位姿、打印朝向转换，以及 STEP 和 3MF 写入和回读。
- `workflow.py` 串联这些步骤，管理临时文件、整批发布和回滚。
- `argus.web` 提供模型预览接口和静态托管，`src/web` 实现三维视口和参数表单。
