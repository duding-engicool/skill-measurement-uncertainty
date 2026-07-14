# 测量不确定度（MU）评定（measurement-uncertainty）

> 面向实验室/计量工程师的混合式双版技能。按 GUM 法评定测量不确定度（A 类/B 类分量合成），输出规范的不确定度评定报告（Markdown + HTML 双版）。

## 适用角色

- 实验室 / 计量工程师、授权签字人
- 质量工程师（关键尺寸/物理量可靠性量化）

## 核心能力

1. **A 类评定**：输入重复测量列，自动算均值、实验标准差与 u_A = s/√n。
2. **B 类评定**：逐项录入不确定度来源（半宽 a、分布类型、灵敏度 c），按分布换算标准不确定度。
3. **合成与扩展**：u_c = √(u_A² + Σu_B²)，U = k·u_c（k 默认 2，约 95%）。
4. 一键产出双版本：`不确定度评定报告.md` 与 `不确定度评定报告.html`（主色 #C8102E）。

## 目录结构

```
measurement-uncertainty/
├── SKILL.md
├── README.md
├── references/
└── scripts/
    └── build_report.py     # 双版报告生成器（含内置小样本）
```

## 快速使用

```bash
python scripts/build_report.py --demo
python scripts/build_report.py --input result.json \
    --md-out 不确定度评定报告.md --html-out 不确定度评定报告.html
```

## 与 MSA 的区别（重要）

- **MU（本技能）**：量化单次测量结果的**不确定度**（计量学，GUM）。
- **MSA**（`msa-analysis` / `msa-calculator`）：评价**测量系统**本身的变异（Gage R&R / 偏倚 / 线性 / 稳定性）。
- 两者目的不同，不可互相替代；校准证书不确定度可作本技能 B 类分量输入。

## 防幻觉声明

- 不编造测量数据、校准不确定度、分布参数；缺失标注「待企业补充」。
- 最终评定须由授权计量人员确认，本技能为辅助计算与模板。
