# Afterlight：一次有真实记录的 VibeLens 调试

浏览器前端、Python 后端与 SQLite 组成一个图片审核项目。上传者替换图片后，审核者仍在旧页面点击通过；首版错误地发布了新图片。演示沿实际图定位缺少的版本比较，再复测修复结果。

[打开二维、三维演示](https://li-bruce.github.io/VibeLens/demo.html?lang=zh-CN) · [英文说明](README.md) · [模拟开发对话](review/dialogue.md)

在仓库根目录运行：

```sh
python -m pip install -r examples/exhibition-review/requirements.txt
python tools/setup_adapters.py
python examples/exhibition-review/run.py --port 8894
```

打开[项目页面](http://127.0.0.1:8894/app)和[VibeLens 图](http://127.0.0.1:8894/graph)。默认启动修复版，每次创建独立目录，Ctrl+C 停止。

操作顺序：上传 PNG → 审核者打开 → 上传者替换 PNG → 审核者在旧页面通过。修复版会返回 `stale_review`；重新打开最新版再通过，才会出现在展览中。在图中开始录制、完成操作、停止录制，即可回放参数、判定、状态与 SQL 操作。

页面有“确认、记录、定位、修改、复测”五个阶段，涵盖 API、业务、状态、判定、函数参数、数据操作、数据结构和源码八层。二维适合追踪局部链路，三维适合分开观察图层。源码从局部开始，可切换到完整源码结构。

首版缺陷为演示预设，对话为模拟；浏览器操作、数据库写入、运行事件和状态快照都实际执行。Pages 回放的是导出的真实记录，本地项目可以录制新操作。示例身份固定为上传者和审核者，没有登录系统；图片检查仅演示 PNG 头识别。

完整重跑命令和源码职责见[英文说明](README.md)，失败、修复、复测和截图见[验收材料](../../docs/review/pages-case/README.md)。
