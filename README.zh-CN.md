<p align="center"><a href="https://liblog.vip/VibeLens/?lang=zh-CN"><img src="docs/media/overview-zh-CN.svg" alt="VibeLens — 看清 AI 写出的程序。连接业务、状态、规则、入口、工程结构、代码执行与存储结构。" width="100%"></a></p>

<p align="center">
<a href="README.md">English</a> ·
<a href="https://liblog.vip/VibeLens/?lang=zh-CN">了解 VibeLens</a> ·
<a href="https://liblog.vip/VibeLens/demo.html?lang=zh-CN">体验交互演示</a> ·
<a href="#开始使用">安装</a>
</p>

<p align="center">
<a href="https://github.com/li-bruce/VibeLens/releases/latest"><img src="https://img.shields.io/github/v/release/li-bruce/VibeLens?color=087f80" alt="最新版本"></a>
<a href="https://github.com/li-bruce/VibeLens/actions/workflows/check.yml"><img src="https://github.com/li-bruce/VibeLens/actions/workflows/check.yml/badge.svg?branch=main" alt="仓库检查"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-526b71" alt="MIT 开源协议"></a>
</p>

# 界面能用了，内部逻辑看清了吗

AI 可以很快写出一个应用。权限在哪里判断，状态为什么改变，一次操作经过了哪些函数，这些细节仍然需要开发者掌握。

**VibeLens 把你确认的模型、AI 写出的代码和程序的实际运行连接在一张图上。** 沿着一次业务操作，找到解释它的参数、函数和查询。

## 先看懂模型，再开始开发

> “使用 $vibelens 梳理这个项目。先画出业务流、状态和规则，让我确认它应该怎样运行。”

VibeLens 通过对话构建相互关联的**业务网、状态网和规则网**。确认关键细节、看清图，再进入开发。选择 **Drive**，基于可执行的状态声明开发；选择 **Observe**，观察项目自身的逻辑。

不同业务流、不同对象的状态机可以各自建模。既能单独查看一项能力，也能沿着图看清它与其他能力的衔接。多个模型引用同一个函数时，可以追溯到同一处源码。

## 沿着运行，找到问题所在

录下操作，回放状态和数值的变化。在自定义视图中保留相关链路，展开判定和输入参数，再打开高亮的源码。

[![自定义视图将接收者、操作者、删除操作与影响行数连接到高亮的 SQL 源码](docs/site/images/source-zh-CN.png)](https://liblog.vip/VibeLens/demo.html?lang=zh-CN#drill)

把发现的问题告诉 coding agent。修改过程中，VibeLens 同步维护模型、源码映射和检查。再次运行，查看修改后的实际结果。

[**体验交互演示 →**](https://liblog.vip/VibeLens/demo.html?lang=zh-CN)

## 同一张图，按需深入

[![三维视图连接业务行为、状态和代码中的实际参数](docs/site/images/layers-zh-CN.png)](https://liblog.vip/VibeLens/?lang=zh-CN#explore)

| 你想了解什么 | 沿着图去看 |
|---|---|
| 程序应该怎样运行 | 业务动作、对象状态、共享规则 |
| 具体在哪里实现 | 入口 → 目录与文件 → 函数与参数 |
| 这次运行改变了什么 | 采集到的输入、判定、状态、查询和实际效果 |
| 这轮修改需要关注哪里 | 保存的自定义视图、局部录制和同步时间轴 |

切换 **2D / 3D**，逐层展开，筛选节点与关系。代码迭代后，继续沿用你的布局和批注。实时观察、录制与回放都围绕同一张图展开。

## 开始使用

### Codex

将完整 Skill 安装到项目：

```bash
npx skills add li-bruce/VibeLens --skill vibelens
```

**v0.15.0** 的 Skill ZIP 约 **0.92 MB**。首次使用时下载查看器资源，后续直接复用；离线环境可使用[完整安装包](https://github.com/li-bruce/VibeLens/releases/download/v0.15.0/vibelens-offline-v0.15.0.zip)。

在项目对话中输入：

```text
使用 $vibelens 梳理这个项目。
实现前，先让我确认业务网、状态网和规则网。
```

### DeepSeek Harness

安装 [v0.15.0 中的插件包](https://github.com/li-bruce/VibeLens/releases/tag/v0.15.0)：

```bash
dsh plugin --profile web add https://github.com/li-bruce/VibeLens/releases/download/v0.15.0/dsh-vibelens-0.15.0.tgz
```

打开该 profile，在对话中以 `/vibelens` 开头描述项目。[Harness 安装与已测试兼容范围](docs/deepseek-harness.md)。

**Python · Node.js · React · Vue**，界面支持中英文切换。共享观察器使用 Python 3.11+，项目沿用原生语言。[安装、依赖与固定版本下载](docs/usage.zh-CN.md)。

也可通过 [SkillHub](https://skillhub.cn/skills/user_fbf26156/vibelens) 获取。

## 从界面到源码，都可以查看

完整源码、可运行示例和保留的检查材料，帮助你了解工具本身的实现与验证情况。

[源码结构](docs/source-guide.zh-CN.md) · [功能支持](docs/capabilities.md) · [验收记录](docs/review/release-v0.15.0/README.md) · [更新说明](docs/releases/v0.15.0.md) · [发布渠道](docs/distribution.md)

[MIT 开源协议](LICENSE) · [第三方许可](THIRD_PARTY_NOTICES.md)

查看器、路由与布局库用于本地调试工具；新项目只接入原生状态与采集适配器、项目声明。业务项目无需携带查看器依赖。[依赖与打包范围](skills/vibelens/references/dependency-distribution.md)。
