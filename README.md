# Argus 舵机云台建模

Argus 用 build123d 参数化生成支架、底座、云台头和舵盘。尺寸和装配位姿定义在 `src/argus/models/` 下各零件子包中。修改对应参数后重新运行主命令即可导出。

## 运行

在项目根目录使用 Python 3.11 或 3.12 和 Poetry。

```bash
poetry install
poetry run argus
```

主命令直接使用 Python 参数，在 `model-bin/parametric-parts` 中生成支架、分体底座、云台头和两处装配所用舵盘的 STEP 和 3MF，分体底座也同时生成 STL。STEP 使用代码定义的装配位姿，3MF 和 STL 按打印朝向居中贴床。该流程可以在没有源 STEP 的环境运行。

分体底座把舵盘四臂夹在上下两层之间。默认使用 PETG 卡扣，两侧悬臂从下座边缘的释放口按入后可解扣，另有两处刚性定位键承担上下层相对转动时的载荷。每侧扣头宽 6.0 mm，默认单边间隙 0.25 mm 时咬合 0.65 mm。上盖的外表面平贴打印平台，使卡臂沿打印层展开。实际间隙和带载换向后的松动情况需通过试打确认。装配时先将舵盘放入下座并合盖，再从上方放入舵机，通过下座中央的 Ø4.8 mm 工具通道拧紧舵机原有的中心螺钉。

用 `poetry run argus --split-base` 单独导出上下层，用 `poetry run argus --sg90s` 导出按所选底部舵盘适配输出轴的 SG90S，用 `poetry run argus --assembly` 导出保留零件名称和位姿的 `argus_gimbal_assembly.step`。加入 `--base-connection m3` 可切换到四颗 M3×6 螺栓和 M3×3×Ø4.2 热熔螺母连接。M3 版热熔底孔为 Ø4.0 mm、深 4.2 mm，可按螺母和试熔尺寸调整。底部可用 `--horn-profile equal` 切换为等臂舵盘。整机的两颗舵机按各自舵盘的花键尺寸生成，网页独立舵机采用仓库参考轴的尺寸。原装配中上部舵机与云台头的配合面有约 0.25 mm 的几何重叠，本版沿用这处装配关系。

底座的底板和两组安装孔共用卡环中心。每组孔的 `offset` 表示一个孔相对中心的 XY 偏移，程序按 90° 旋转生成该组四个孔。

舵盘槽底盘共用 42 × 42 mm 的底板和 30 mm 的四角安装孔距，凹槽与固定孔按选择的舵盘生成。默认长短臂舵盘采用 33.58 mm 长跨距、2.25 mm 臂厚、4.62 mm 总厚、Ø6.74 mm 凸台、Ø1.45 mm 臂孔和 Ø2.36 mm 中心孔。短向跨距按图估为 19.8 mm，未标注的孔距按图估算，端孔间距采用标注的 2.43 mm。底盘默认板厚 6.2 mm，槽单边留 0.2 mm，以长臂倒数第二孔和短臂外孔为固定孔位。

两款舵盘均可单独预览和导出。长短臂的内花键暂沿用 20 齿，以图示 Ø4.65 mm 作为齿顶径试装值。等臂 MG90S 版为 26.25 mm 等臂十字，内花键沿用仓库参考轴的 20 齿、Ø4.80 mm 齿顶径和 Ø4.10 mm 齿根径。实物花键配合以试装为准。

运行 `poetry run argus --base-servo --servo-horn` 单独导出默认底盘和长短臂舵盘，文件名分别为 `gimbal_base_servo` 和 `servo_horn_long`。加上 `--horn-profile equal` 可切换至等臂底盘和 `mg90s_servo_horn`。

支架以局部 `X=0` 为左右对称面，安装框、双臂、减重窗和卡片由单侧轮廓生成。左侧定位销和右侧凸台通孔共用 `shaft_axis`。右臂外侧按单臂舵盘的 21.3 mm 总长、2.08 mm 臂厚和 Ø6.76 mm 凸台生成凹槽，默认槽深 2.30 mm、单边间隙 0.20 mm，固定孔对应舵盘倒数第二个臂孔。

单臂舵盘总厚 4.82 mm，中心通孔 Ø2.36 mm，臂孔 Ø1.45 mm，端部两孔间距 2.43 mm。外轮廓以总长 21.3 mm 和凸台 Ø6.76 mm 为准。图中未标注的臂端宽度和中间孔距按图估算。内花键以图示 Ø4.54 mm 作为名义齿顶径，齿数暂用仓库的 20 齿，实物配合以试装为准。工作台可打开 `/models/servo-horn-single`，或用 `poetry run argus --single-horn` 单独导出。

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

打开 `http://127.0.0.1:8000/` 默认进入「分体底座」`/models/base-split`。参数面板的「连接方式」默认选中「PETG 卡扣」，可切换到「M3 热熔螺母」。调整参数后点击「重新生成」，即可查看闭合底座、上盖或下座。「整机装配」`/models/gimbal-assembly` 与分体底座共用同一份参数和已生成结果。上下层可分别导出 STEP、3MF 或 STL，整机可导出 STEP。

单体舵盘槽底盘保留在 `/models/base-servo`，原底座在 `/models/base`。两款舵盘分别在 `/models/servo-horn-long` 和 `/models/servo-horn`，SG90S 舵机在 `/models/sg90s`。支架和云台头继续使用 `/models/bracket` 和 `/models/head`，打印版在 `/models/bracket-print` 和 `/models/head-print`。

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
