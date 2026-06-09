# AI 辅助市场研究工作流

面向快消母婴品类（IMF 婴幼儿配方奶粉）的消费者旅程研究工具，将 Brief 到洞察报告的全流程产品化，通过自动化采集、框架化分析、三元校验实现研究效率提升 50%+。

## 核心能力

| 模块 | 功能 | 说明 |
|------|------|------|
| BriefParser | Brief 解析 | YAML → 结构化研究目标 |
| DataCollector | 数据采集 | Adapter 接口，支持多数据源 |
| FrameworkAnalyzer | 框架化分析 | 人群分层/触点效率/决策路径/转化建议 四模块输出 |
| TripleValidator | 三元校验 | 源校验/交叉校验/逻辑校验 |
| ReportGenerator | 报告生成 | Jinja2 模板自动生成 HTML 报告 |

## 快速开始

```bash
pip install -e .

# 运行完整 Pipeline
PYTHONPATH=src python -m mrw.cli run \
  --brief examples/skincare_brief.yaml \
  --data examples/sample_comments.json \
  --output outputs

# 查看报告
open outputs/report.html
```

## Pipeline 架构

```
Brief → ResearchDesign → DataCollect → FrameworkAnalyze → TripleValidate → Report
```

5 个 stage 均为纯函数 + 标准 IO，便于后续接入 UI 层。

### 三元校验

每条洞察必须通过三重检验：

1. **源校验（Source Check）**：洞察是否绑定有效 source_id，原声是否真实存在
2. **交叉校验（Cross Check）**：同主题多条原声情感方向是否一致
3. **逻辑校验（Logic Check）**：检测过度推断（「100%」「所有用户」等）

置信度分级：
- high (≥0.75)：直接进入报告
- medium (0.5–0.75)：进入报告，标注置信度
- low (<0.5)：进入人工复核队列

## Demo 指标（IMF 奶粉品类）

- 样本量：65 条模拟舆情（小红书/抖音/妈妈群/电商等多触点）
- 洞察有源率：100%（每条洞察均绑定原声 source_id）
- 高/中置信洞察：60%（进入报告）
- 低置信洞察：40%（进入人工复核队列，系统正确拦截单源推断）
- 覆盖决策模式：深度学习型 / 适度研究型 / 快速决策型

## 项目结构

```
ai-research-workflow/
├── README.md
├── requirements.txt
├── pyproject.toml
├── src/
│   └── mrw/
│       ├── __init__.py
│       ├── cli.py
│       ├── pipeline.py
│       ├── stages/
│       │   ├── __init__.py
│       │   ├── brief_parser.py
│       │   ├── data_collector.py
│       │   ├── framework_analyzer.py
│       │   ├── triple_validator.py
│       │   └── report_generator.py
│       └── templates/
│           └── report.html
├── examples/
│   ├── imf_brief.yaml
│   └── sample_comments.json
├── outputs/
└── docs/
    └── methodology.md
```

## 可选 LLM 增强

设置环境变量启用 LLM（逻辑校验等）：

```bash
export OPENAI_API_KEY=sk-...
```

未配置时自动 fallback 到规则引擎。

## 局限性

- Phase 1 使用样例 JSON，非真实爬虫数据
- 分析引擎以规则 + 关键词为主，LLM 为可选增强
