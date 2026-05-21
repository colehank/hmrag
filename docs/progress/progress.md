# HiMGA 研究进度日志

> 本文档记录每周计划与完成情况，以及 AAAI 2026 投稿倒推计划。
> 所有技术决策的依据见 `claim.md`。
> 格式：每周新增一个 `## Week N` 节，标注计划状态（⬜ 待完成 / ✅ 已完成 / 🔄 进行中 / ❌ 未完成）。

---

## 论文章节速查

> 各章节在全文中的位置、核心内容与字数目标一览。供每周写作时快速定位。

| 章节 | 标题 | 字数目标 | 核心内容简介 |
|------|------|---------|------------|
| Abstract | 摘要 | 200 词 | 四句话结构：①对话 RAG 面临的三类挑战 ②现有方法的共同缺口 ③HiMGA 的方法概括（类型化超图 + 冲突仲裁）④关键性能数字（LoCoMo / LongMemEval）。最后写，包含最终实验数字。 |
| §1 | Introduction | 600 词 | 五段式展开：①对话数据三属性打破文档 RAG 假设 ②现有方法各自的局限（MAGMA/HyperMem/Zep） ③HiMGA 的统一解法 ④四条 Contributions（含最终数字） ⑤论文结构。骨架在 Week 5 完成，数字在 Week 9 填入。 |
| §2 | Problem Formulation | 400 词 | 给出对话记忆 RAG 的任务形式化定义（输入/输出/目标），以及由对话数据三属性推导出的 P1–P4 四个核心研究问题，每条问题附一句现有证据引用。为后续方法章节的设计决策提供依据。 |
| §3 | **The HiMGA Framework**（方法）| — | 全文核心，分四个子节。先给出类型化超图的形式化基础，再依次描述写入、检索、冲突仲裁三个过程。合计约 1450 词 + 1 张算法框 + 2 张表。 |
| §3.1 | Typed Hypergraph | 400 词 + 定义框 + 表 | 给出 $\mathcal{H}=(V,E,\tau,\omega,\pi)$ 五元组正式定义，Topic-Episode-Fact 三层节点层次，四类超边（$T_{sem}/T_{temp}/T_{causal}/T_{entity}$）的语义定义表，形式约束（类型独立性、层级跨越规则、规模边界），以及置信度公式 $c_v$。本节是全文的形式化基础，Week 2 必须完稿。 |
| §3.2 | Memory Construction | 350 词 + 算法框 | 描述写入过程：三层切分（Episode 边界检测 → Topic 聚合 → Fact 抽取）→ 并行四类超边抽取 → 冲突检测（指向 §3.4）→ 置信度更新。配 Algorithm 1 伪代码。重点说明双流架构（同步快路径 $<$500ms + 异步慢路径）和因果超边的规模约束（$|e_{causal}| \geq 3$）。 |
| §3.3 | Intent-Driven Typed Retrieval | 350 词 | 描述检索流程：意图分析（$q \to \mathbf{r}$，轻量分类器 + LLM fallback）→ 类型门控（超边过滤）→ 时序过滤（$t_{valid}/t_{invalid}$ 窗口匹配）→ Topic-Episode-Fact 三层粗到细遍历 → 置信度加权最终打分。给出 WHY/WHEN/WHO 查询与类型激活权重的典型映射关系。 |
| §3.4 | Conflict-Aware Knowledge Evolution | 350 词 + 分类表 | 说明冲突感知写入机制：四类冲突（时序冲突/矛盾冲突/版本覆盖/正交并存）的触发条件与处理策略表，最小化修订原则（边节点不删除，仅通过 $t_{invalid}$ 和 confidence 衰减表达失效），以及面向弱模型鲁棒性的设计动机（本地部署 + 成本敏感场景）。 |
| §4 | **Experiments**（实验）| — | 分五个子节：实验配置、主结果、消融、跨类型分析、RQ1×RQ2 交互。合计约 1700 词 + 4 张表。需 M5–M6 全部完成后才能写完。 |
| §4.1 | Experimental Setup | 400 词 | 数据集（LoCoMo 的 5 个子集 + LongMemEval 的 knowledge-update 子集说明）、Baseline 系统（Full-Context / MAGMA / HyperMem / Zep）、两套评测配置（LoCoMo 对齐 HyperMem；LongMemEval 对齐 Zep）、开源 fallback 配置（Qwen3-32B），以及 LLM-as-judge 协议与 bootstrapped 95% CI 说明。 |
| §4.2 | Main Results | 400 词 + 2 张主表 | 两张主表：① LoCoMo 全系统对比（5 子集 + Overall）；② LongMemEval knowledge-update（gpt-4o-mini / gpt-4o 双配置）。叙述重点：HiMGA 在 cross-type 相关子集上的增益、knowledge-update 上消除 Zep 弱模型退化的幅度。 |
| §4.3 | Ablation Study | 400 词 + 消融矩阵 | 六配置消融矩阵（HiMGA-Full / w/o Typing / w/o Hierarchy / w/o Conflict / w/o all / HyperMem reproduction），分别隔离 P1（类型化）、P2（层次）、P4（冲突感知）的贡献。需显式讨论三者之间是协同还是抵消，并说明 "w/o Typing vs HyperMem reproduction" 差异的归因逻辑。 |
| §4.4 | Cross-type Query Analysis | 300 词 + 案例框 | 描述 50 个跨类型查询测试集（来源、标注方法、类型分布），报告 HiMGA vs HyperMem 单系统 vs HyperMem+MAGMA 串联的 Answer Accuracy + Evidence Recall，配 2 个具体案例说明联合激活多类超边的必要性。测试集将随论文开源。 |
| §4.5 | RQ1 × RQ2 Interaction | 200 词 | 分析类型化超图（RQ1）与冲突仲裁（RQ2）两个机制之间的交互效应，依据消融矩阵的交叉行（w/o Typing 保留 Conflict / w/o Conflict 保留 Typing）。明确声明两者是协同、独立还是部分抵消，不可隐藏意外结果。 |
| §5 | Related Work | 500 词 + 对比表 | 三条线索：①图记忆系统（MAGMA / Zep / A-MEM）②超图方法（HyperMem / HyperGraphRAG / Cog-RAG / Hyper-RAG）③知识演化（TemporalKG / Graphiti）。配超图方法对比表（分层 / 类型化 / 处理P4 / 性能）。明确声明 HiMGA 贡献为协议创新而非数据结构发明（Berge 1973）。 |
| §6 | Conclusion | 200 词 | 三段：①三条核心贡献总结（类型化超图协议 / 冲突感知仲裁 / cross-type 测试集开源）②局限性（评测覆盖范围 / LLM 依赖 / 可扩展性）③未来方向（多模态 / 大规模图 / 弱模型自动化冲突检测）。 |

---

## 投稿截止日

| 节点 | 日期 | 状态 |
|------|------|------|
| AAAI 2026 摘要截止 | **2026-07-21** | ⬜ |
| AAAI 2026 全文截止 | **2026-07-28** | ⬜ |
| AAAI 2026 补充材料截止 | **2026-07-31** | ⬜ |

---

## 总体里程碑

| 里程碑 | 目标 | 对应周次 | 状态 |
|--------|------|---------|------|
| M0 | 研究纲领定稿（`claim.md`） | Week 1 | ✅ |
| M1 | 基础架构：类型化超图数据结构 | Week 2 | ⬜ |
| M2 | 图构建管线：对话 → 类型化超图 | Week 3 | ⬜ |
| M3 | 检索模块：意图路由 + 层次遍历 | Week 4 | ⬜ |
| M4 | 写入机制：冲突检测 + 时效性管理（RQ2） | Week 5 | ⬜ |
| M5-a | LoCoMo 评测（HiMGA vs HyperMem vs MAGMA） | Week 6 | ⬜ |
| M5-b | LongMemEval 评测（knowledge-update 子集） | Week 7 | ⬜ |
| M6 | 消融实验：6 配置 × 2 数据集 + cross-type 专项 | Week 8 | ⬜ |
| M7 | 论文整合定稿与提交 | Week 9–10 | ⬜ |

---

## AAAI 2026 全文撰写倒推计划

> **倒推逻辑**：全文 8 页，约 5000 有效词 + 方法图 + 实验表格。
> 实验结果（M5-M6）是关键路径瓶颈，非实验内容须在 Week 5 前全部完成草稿，以确保 Week 8 后专注整合。

### 论文结构与章节字数目标

| 章节 | 预计篇幅 | 可开始写作的最早时间 | 必须完稿时间 |
|------|---------|------------------|------------|
| §1 Introduction | 600 词 | Week 2（骨架）| Week 9 |
| §2 Problem Formulation | 400 词 | Week 2 | Week 5 |
| §3.1 Typed Hypergraph（形式化）| 400 词 + 定义框 | **立即（Week 2）** | Week 2 |
| §3.2 Memory Construction（写入过程）| 350 词 + 算法框 | Week 3 | Week 3 |
| §3.3 Intent-Driven Retrieval（检索）| 350 词 | Week 4 | Week 4 |
| §3.4 Conflict-Aware Evolution（冲突仲裁）| 350 词 + 分类表 | Week 5 | Week 5 |
| §4.1 Experimental Setup | 400 词 | Week 4 | Week 5 |
| §4.2 Main Results | 400 词 + 2 张主表 | Week 7（骨架）| Week 8 |
| §4.3 Ablation Study | 400 词 + 消融矩阵 | Week 8 | Week 8 |
| §4.4 Cross-type Analysis | 300 词 + 案例 | Week 8 | Week 8 |
| §4.5 RQ1×RQ2 Interaction | 200 词 | Week 8 | Week 8 |
| §5 Related Work | 500 词 + 对比表 | Week 3 | Week 6 |
| §6 Conclusion | 200 词 | Week 9 | Week 9 |
| Abstract | 200 词 | Week 9 | **2026-07-21** |

---

### 各周稿件任务详解

#### Week 2（2026-05-26 ~ 06-01）

**实现里程碑**：M1 — `TypedHypergraph` 核心数据结构

> 实现与写作并行：先理清形式化定义再实现，两者互相校验。

**必须完成的稿件内容**：

**§3.1 Typed Hypergraph — 完整可提交草稿**（~400 词 + 正式定义）

需包含以下具体内容：

- **段落 1（动机段）**：一段话说明为什么单类型超边（HyperMem）和无超边的多图（MAGMA）各自不足，
  引出"类型化超边"统一表示的必要性。核心论点：*关系维度区分（"拆"）与高阶元素绑定（"合"）在同一表示内统一，是现有方法未做到的。*

- **Definition 1 框**（正式定义）：
  $$\mathcal{H} = (V, E, \tau, \omega, \pi)$$
  五个分量逐一定义（$V^T \cup V^E \cup V^F$、超边 $E$、类型映射 $\tau$、权重 $\omega$、元数据 $\pi$）。

- **Table 1**（四类超边的语义定义表）：
  | 类型 | 符号 | 绑定语义 | 规模约束 |
  $T_{sem}$、$T_{temp}$、$T_{causal}$（$|e| \geq 3$）、$T_{entity}$ 各行填写。

- **形式约束段**：类型独立性（同一组节点可同时属于不同类型超边）+ 层级跨越规则（默认同层，跨层须以 topic 节点为锚）+ 实践边界（$|e| \leq 16$）。

- **§3.1 末尾**：Confidence score 公式（$c_v = \alpha c^{extract} + \beta c^{degree} + \gamma c^{time}$），三个因子解释。

**§2 Problem Formulation — 骨架草稿**（~200 词，后续补充）：
  - 对话记忆 RAG 的任务定义（一段话 + 1 个公式）
  - P1-P4 的一句话表述（指向 §1 和 §3 的详细展开）

---

#### Week 3（2026-06-02 ~ 06-08）

**实现里程碑**：M2 — 图构建管线（四类超边抽取器 + Topic-Episode-Fact 切分）

**必须完成的稿件内容**：

**§3.2 Memory Construction — 完整可提交草稿**（~350 词 + 算法框）

- **段落 1（三层切分）**：Episode 边界检测 → Topic 聚合 → Fact 抽取，一句话说明沿用 HyperMem §3.2 协议，重点在后续如何并行构建四类超边。

- **Algorithm 1 框**（写入过程伪代码）：
  输入：新对话 $x_t$；输出：更新后的 $\mathcal{H}$。
  步骤：三层切分 → 并行调用四个 type-specific 抽取器 → 冲突检测（指向 §3.4）→ 置信度更新。

- **段落 2（双流架构）**：同步快路径（$T_{sem}$ + $T_{temp}$，目标 < 500ms）+ 异步慢路径（$T_{causal}$ + 冲突检测）。说明设计动机（MAGMA dual-stream 的延迟经验）。

- **段落 3（因果超边的特殊说明）**：$|e_{causal}| \geq 3$ 约束的理由（二元因果用 pairwise 边即可，超边仅用于多元汇聚/发散场景）；无法满足时退化为 $T_{temp}$。

**§5 Related Work — 第一稿**（~500 词 + 对比表）

- **§5.1 图记忆系统**（~150 词）：MAGMA（P1 但无超边）→ Zep（P4 但弱模型退化）→ A-MEM（无结构化知识冲突处理）。
- **§5.2 超图方法**（~150 词）：HyperGraphRAG → Cog-RAG → Hyper-RAG → HyperMem。重点：HyperMem 是最强基线，单类型超边是其局限。
- **§5.3 知识演化**（~100 词）：TemporalKG + Graphiti（Zep 底层）在知识时效性上的工作。
- **Table X**（超图方法对比表）：分层 / 类型化 / 处理 P4 / LoCoMo 成绩，填入 HyperGraphRAG / Hyper-RAG / Cog-RAG / HyperMem / HiMGA 各行。
- 末尾明确一句话：*"HiMGA 的贡献不在于类型化超图数据结构的发明（Berge 1973），而在于其在对话记忆 RAG 中的首次系统化协议设计。"*（应对 DA-1 审稿人攻击）

---

#### Week 4（2026-06-09 ~ 06-15）

**实现里程碑**：M3 — 检索模块（意图路由 + 类型门控 + 层次遍历）

**必须完成的稿件内容**：

**§3.3 Intent-Driven Typed Retrieval — 完整可提交草稿**（~350 词）

- **段落 1（意图分析）**：$q \to (\mathbf{r}, [t_s, t_e], q_{key}, q_{dense})$，其中 $\mathbf{r} \in \Delta^{|\mathcal{T}|}$。实现：轻量级分类器为主路径，置信度低时回退至 LLM zero-shot 分类（对齐 MAGMA 意图路由设计）。WHY/WHEN/WHO 查询的典型激活权重映射表。

- **段落 2（类型门控 + 时序过滤）**：$\sum_T r_T \cdot \mathbb{1}[\tau(e)=T] > \theta$ 的门控条件；$[t_s, t_e] \cap [t_{valid}(e), t_{invalid}(e)] \neq \emptyset$ 的时序条件。说明两步过滤的顺序设计动机。

- **段落 3（层次粗到细遍历）**：Topic → Episode → Fact 三层检索（沿用 HyperMem §3.3 协议），逐层缩小候选集。最终得分 $S(e) = w_e \cdot c_e \cdot \text{sim}(q, e)$。

**§4.1 Experimental Setup — 完整可提交草稿**（~400 词）

- **数据集段**：LoCoMo（描述 + 5 子集：Multi-Hop / Temporal / Open-Domain / Single-Hop / Adversarial）+ LongMemEval（描述 + 6 类型，重点说明 knowledge-update 子集 ~83 题及统计功效说明）。
- **Baseline 段**：Full-Context / MAGMA / HyperMem / Zep 各一句话描述 + 关键配置。
- **配置对齐段**（两个配置分开说明）：
  - LoCoMo 配置：Qwen3-Embedding-4B + Qwen3-Reranker-4B + GPT-4.1-mini，对齐 HyperMem 92.73%；
  - LongMemEval 配置：gpt-4o-mini + gpt-4o 双配置，对齐 Zep 74.4% / 83.3%；
  - 开源 fallback：Qwen3-32B（保障可重复性）。
- **评测指标段**：LLM-as-judge（GPT-4o-mini / GPT-4o）+ 3 次独立运行均值 + bootstrapped 95% CI（应对 R1-S3 统计功效质疑）。

---

#### Week 5（2026-06-16 ~ 06-22）

**实现里程碑**：M4 — 冲突检测模块（4 类冲突 + 置信度衰减 + 最小化修订）

**必须完成的稿件内容**：

**§3.4 Conflict-Aware Knowledge Evolution — 完整可提交草稿**（~350 词 + 分类表）

- **段落 1（问题定位）**：引用 Zep 在 gpt-4o-mini 下退化（74.4% < 76.9%）作为动机，说明 HiMGA 将冲突检测负担从单次 LLM 仲裁转移到结构化类型检测，降低对仲裁模型能力的依赖。

- **Table Y**（4 类冲突分类表）：

  | 冲突类型 | 触发条件 | 处理策略 |
  |---------|---------|---------|
  | 时序冲突 | 同一实体 + 同一谓词 + 时序超边内时间窗口重叠 | 旧断言 $t_{invalid}$ 设为新断言 $t_{valid}$ |
  | 矛盾冲突 | 同一实体 + 相反谓词 + 语义超边内共现 | 标记待仲裁，LLM 仲裁，保留两版本附置信度 |
  | 版本覆盖 | 同一实体 + 相同类型 + 时序更近 | 旧断言置信度衰减（不删除） |
  | 正交并存 | 同一实体 + 不同属性断言 | 共存，无操作 |

- **段落 2（最小化修订原则）**：边/节点不物理删除，仅通过 $t_{invalid}$ 和 confidence 衰减表达失效；history 字段 append-only 记录修订时间戳；超过保留窗口且 $c < c_{min}$ 的节点周期性压缩为 summary 节点。

- **段落 3（弱模型场景的 motivation）**：明确写出两个 evergreen 应用场景——①本地/隐私部署（7B-13B 开源模型）永久需要弱模型鲁棒性；②成本敏感的大规模部署（gpt-4o → gpt-4o-mini 约十倍成本差）。（应对 DA-3 攻击）

**§1 Introduction — 完整骨架**（5 段占位，含关键论点句，无数字填充）：

- 段 1：对话数据的三个内生属性打破文档 RAG 的假设（属性 A/B/C）
- 段 2：现有方法各解决一部分：MAGMA（P1）、HyperMem（P2+P3）、Zep（P4 但弱模型退化）
- 段 3：HiMGA 以类型化超图统一 P1+P2+P3，以类型感知冲突仲裁解决 P4
- 段 4：Contributions（4 条，末尾括号 `[待数字填充]`）
- 段 5：论文组织

**§2 Problem Formulation — 完稿**（~400 词）：
- 对话记忆 RAG 的完整任务定义
- P1-P4 问题定义段（每条两句话：直观描述 + 现有证据引用）

---

#### Week 6（2026-06-23 ~ 06-29）

**实现里程碑**：M5-a — LoCoMo 评测（HiMGA + HyperMem 基线复现）

**必须完成的稿件内容**：

**Cross-type Query 测试集构造**（研究产出，非正文，但 §4.4 的前提）：

- 从 LoCoMo multi-hop + temporal 子集中筛选约 100 个候选查询
- 2 名标注者独立标注所需激活类型组合 $\mathbf{r}^*$，保留 $\|\mathbf{r}^*\|_0 \geq 2$ 的查询（预期 30-50 个）
- 若数量不足，从 LoCoMo 对话历史中以 LLM 生成并人工筛选至 50 个
- 人工标注 golden answer + 必需证据节点

**§5 Related Work — 终稿**（在 Week 3 草稿基础上修订）：
- 补充与 Cog-RAG / Hyper-RAG 的差异化对比（应对 R2-S2）
- 在对比表中补全 HiMGA 列

**进度检查**：本周应拿到第一批 LoCoMo 数字，用于 sanity check 实现正确性，若 HyperMem 复现分 ≠ 92.73% ± 1%，则本周内排查实现偏差。

---

#### Week 7（2026-06-30 ~ 07-06）

**实现里程碑**：M5-b — LongMemEval knowledge-update 评测（gpt-4o-mini + gpt-4o）

**必须完成的稿件内容**：

**§4.2 Main Results — 结果骨架**（随数字陆续填写）

- **Table 2**（LoCoMo 主结果表）：行 = 系统，列 = Single-Hop / Multi-Hop / Temporal / Open-Domain / Adversarial / Overall；每个 HiMGA 数字到位后立即填入。
- **Table 3**（LongMemEval 结果表）：行 = 系统，列 = knowledge-update (4o-mini) / (4o) / Overall；Zep 的对照数字从 claim.md §5.3 核验后复制。
- **叙述段草稿**：为每张表写 3-4 句话的叙述（核心结论句，数字处用 `XX.X%` 占位）。

---

#### Week 8（2026-07-07 ~ 07-13）

**实现里程碑**：M6 — 消融实验（6 配置）+ Cross-type 专项评测

**必须完成的稿件内容**：

**§4.3 Ablation Study — 完稿**（~400 词 + 消融矩阵）

- **Table 4**（消融矩阵）：6 行（HiMGA-Full / w/o Typing / w/o Hierarchy / w/o Conflict / w/o all / HyperMem reproduction）× 关键指标列；附注说明 "w/o Typing vs HyperMem reproduction" 差异的归因逻辑（应对 R1-S1）。
- **逐行分析段**：P1（Typing）贡献、P2（Hierarchy）贡献、P4（Conflict）贡献的独立分析；重点讨论三者是否叠加、是否抵消（应对 DA-4）。

**§4.4 Cross-type Query Analysis — 完稿**（~300 词）

- 测试集描述（50 个查询的分布：需激活 2 类 / 3 类 / 4 类超边各多少）
- HiMGA vs HyperMem 单系统 vs HyperMem+MAGMA 串联 的 Answer Accuracy + Evidence Recall 对比
- 2 个具体案例（一个需同时激活因果+时序超边，一个需同时激活实体+时序超边），配框格或图示
- 末尾一句：*"本测试集将随论文开源，为后续研究提供专项评测工具。"*（将 cross-type 稀缺性转化为贡献，应对 DA-2）

**§4.5 RQ1 × RQ2 Interaction Effects — 完稿**（~200 词）

- 分析 "w/o Typing（保留 Conflict）" vs "w/o Conflict（保留 Typing）" 两行的结果
- 明确说明两者是协同、独立还是部分抵消
- 若出现意外交互（如 Typing 降低了 Conflict 的效果），正面讨论而非回避

---

#### Week 9（2026-07-14 ~ 07-20）

**实现里程碑**：M7 开始 — 论文全文整合

**必须完成的稿件内容**：

**§1 Introduction — 终稿**（用最终数字填充占位符）：
- 贡献列表填入具体数字：LoCoMo ≥ 91.5%，LongMemEval gpt-4o-mini ≥ 77%，gpt-4o ≥ 84%
- 确认与 §4 结果一致

**§6 Conclusion — 完稿**（~200 词）：
- 段 1：三条核心贡献总结（类型化超图协议 / 冲突感知仲裁 / cross-type 测试集）
- 段 2：局限性（评测仅覆盖 LoCoMo + LongMemEval / LLM 依赖 / 可扩展性）
- 段 3：未来工作（多模态对话 / 更大规模图 / 弱模型自动化冲突检测）

**Abstract — 第一稿**（200 词，结构化四段）：
- 句 1-2：对话 RAG 的挑战（属性 A/B/C）
- 句 3-4：现有方法缺口（MAGMA/HyperMem/Zep 各一句）
- 句 5-6：HiMGA 方法概括（类型化超图 + 冲突仲裁）
- 句 7-8：关键结果（LoCoMo / LongMemEval 数字）

**全文通读**：检查各章节引用是否一致，消融数字与主结果表交叉核对。

> **July 21（周二）：AAAI 摘要截止 — 提交 Abstract**

---

#### Week 10（2026-07-22 ~ 07-28）

**必须完成的稿件内容**：

- **语言润色**：逐段检查表达精确性，特别是形式化章节（§3.1 定义措辞须与 Berge 1973 等引用一致）
- **格式合规检查**：页数（≤ 8 页正文）、图表分辨率（≥ 300 dpi）、参考文献格式（AAAI 格式）
- **系统图**（Method 图，预留 §3 开头）：HiMGA 整体架构图（写入流 + 检索流 + 冲突检测），建议 2-column 宽
- **Final proofreading**：与至少一名共同作者 / 同行对读

> **July 28（周二）：AAAI 全文截止 — 提交完整论文**

---

#### 补充材料（2026-07-29 ~ 07-31）

> 补充材料不计入页数限制，但需在 July 31 前提交。

- **Appendix A**：Cross-type Query 测试集完整题目 + 标注说明（50 个查询）
- **Appendix B**：扩展消融表（包含每个子集的详细数字）
- **Appendix C**：开源模型 Fallback 配置的完整结果（Qwen3-32B）
- **Code 压缩包**：`hmrag` 包 + 评测脚本 + 复现说明（`README`）

---

## 稿件完成进度追踪

| 章节 | 草稿完成 | 可提交完稿 |
|------|---------|----------|
| §2 Problem Formulation | ⬜ Week 2 骨架 / Week 5 完稿 | ⬜ |
| §3.1 Typed Hypergraph | ⬜ Week 2 | ⬜ |
| §3.2 Memory Construction | ⬜ Week 3 | ⬜ |
| §3.3 Intent-Driven Retrieval | ⬜ Week 4 | ⬜ |
| §3.4 Conflict-Aware Evolution | ⬜ Week 5 | ⬜ |
| §4.1 Experimental Setup | ⬜ Week 4 | ⬜ |
| §5 Related Work | ⬜ Week 3 草稿 / Week 6 终稿 | ⬜ |
| §1 Introduction | ⬜ Week 5 骨架 / Week 9 终稿 | ⬜ |
| §4.2 Main Results | ⬜ Week 7 | ⬜ |
| §4.3 Ablation Study | ⬜ Week 8 | ⬜ |
| §4.4 Cross-type Analysis | ⬜ Week 8 | ⬜ |
| §4.5 RQ1×RQ2 Interaction | ⬜ Week 8 | ⬜ |
| §6 Conclusion | ⬜ Week 9 | ⬜ |
| Abstract | ⬜ Week 9 | ⬜ **July 21 截止** |

---

## Week 1（2026-05-19 ~ 2026-05-25）

**本周目标**：研究纲领定稿（M0）

### 计划

- ✅ 精读 HyperMem (arXiv:2604.08256)，核验架构细节与消融结果
- ✅ 精读 MAGMA (arXiv:2601.03236)，核验 knowledge-update 失败根因
- ✅ 扫描相关工作：Zep (arXiv:2501.13956)、A-MEM、HyperGraphRAG 等
- ✅ 完成 `claim.md` 定稿（基于 ARS 学术流水线：核验 → 诊断 → 草稿 → 审查 → 修订）
- ✅ 搭建项目基础结构（scaffold + CLAUDE.md）

### 关键发现

- **HyperMem 消融数字归属**：Episode Context 影响的是 Temporal −5.61%；Multi-Hop −5.68% 对应的是完全扁平化（w/o TR & ER）消融。已在 `claim.md` 中修正。
- **Zep 部分解决了 P4**：gpt-4o 配置下 knowledge-update 83.3% > Full Context 78.2%，但 gpt-4o-mini 下 74.4% < 76.9%（退化）。HiMGA 的 RQ2 目标修正为"弱模型下也稳健超越"。
- **协议贡献定位**：类型化超图作为数据结构早已存在（Berge 1973），HiMGA 的贡献在**协议层**（类型语义对齐 + 意图驱动激活 + 类型感知冲突仲裁），非数据结构发明。

### 过程文件（根目录）

| 文件 | 内容 |
|------|------|
| `disc/verification_report.md` | arXiv 编号 / 数字 / 架构声明的逐条核验 |
| `disc/diagnosis.md` | claim.md 逻辑漏洞 / 可行性风险 / 缺失要素诊断（A-F 类共 18 项） |
| `disc/review_critique.md` | 3 位模拟审稿人 + Devil's Advocate 评议（7 项必修 + 8 项应改） |

---
