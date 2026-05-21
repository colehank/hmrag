# Verification Report — claim.md 事实核验

> 核验日期：2026-05-21
> 核验源：`ref_methods/HyperMem/2604.08256v2.pdf`、`ref_methods/MAGMA/MAGMA.pdf`、arXiv 官方 abstract 页

## 1. 引用核验

| claim.md 声明 | 实际 | 状态 |
|---------------|------|------|
| MAGMA = arXiv:2601.03236, Jiang et al. | arXiv:2601.03236v2, Jiang/Li/Li/Li, U. Texas Dallas + U. Florida, 16 Apr 2026 | ✅ |
| HyperMem = arXiv:2604.08256, Yue et al. | arXiv:2604.08256v2, Yue/Hu/Sheng et al., IIE-CAS + EverMind AI, 10 Apr 2026 | ✅ |

两篇引用均真实存在、作者与标题准确。

## 2. MAGMA 数字核验

### 架构声明
| claim.md | 实际 (MAGMA paper §3) | 状态 |
|----------|--------------------|------|
| 四个正交图：时序、因果、语义、实体 | Temporal / Causal / Semantic / Entity (§3.2 边空间划分) | ✅ |
| 检索意图路由 WHY/WHEN/ENTITY | T_q ∈ {WHY, WHEN, ENTITY} (§3.3 Stage 1 Intent Classification) | ✅ |
| Adaptive Policy | "Adaptive Traversal Policy" with heuristic beam search (Algorithm 1) | ✅ |

### 消融数字（MAGMA Table 4，LoCoMo Judge 分数）

| claim.md | 实际 (Table 4) | 状态 |
|----------|---------------|------|
| 移除因果图：Judge −0.056 | 0.700 → 0.644，差值 -0.056 | ✅ |
| 移除时序图：Judge −0.053 | 0.700 → 0.647，差值 -0.053 | ✅ |
| 移除 Adaptive Policy：Judge −0.063 | 0.700 → 0.637，差值 -0.063 | ✅ |

补充：移除 Entity Links → 0.666，差值 -0.034（claim.md 未提及，可补充）。

### LongMemEval 数字（MAGMA Table 2）

| claim.md | 实际 | 状态 |
|----------|------|------|
| MAGMA knowledge-update 66.7% | 66.7% | ✅ |
| Full Context knowledge-update 78.2% | 78.2% | ✅ |
| MAGMA 总分 < Full Context | MAGMA 平均 61.2% > Full Context 55.0%（注意：总分上 MAGMA 反超） | ⚠️ 需注意 |

**关键修正**：claim.md 把 "knowledge-update 子集上 MAGMA 输给 Full Context" 描述为 "MAGMA 在 knowledge-update 类型上仅得 66.7%，而 Full Context 达 78.2%"——这是正确的。但隐含的"图记忆系统在该场景下有害"需要谨慎表述：MAGMA 在 **整体**（61.2%）和 **多数子类型**（如 multi-session 89.3% vs 73.3% 等）上仍优于 Full Context，**只有 knowledge-update 一个子集**是退化。这不削弱 P4 的存在性，但避免过度泛化。

## 3. HyperMem 数字核验

### 架构声明
| claim.md | 实际 (HyperMem paper §3) | 状态 |
|----------|--------------------|------|
| 三层节点：Topic-Episode-Fact | 完全一致 (§3.1) | ✅ |
| 超边类型：仅 "语义聚合"（topic-episode、episode-fact） | E^E 连接 topic 下所有 episode；E^F 连接 episode 下所有 fact——均为"属于同一上层"的聚合关系 | ✅ |
| 超边只有语义一种类型 | 论文明确只有 episode hyperedge 和 fact hyperedge，无因果/时序/实体类型 | ✅ |

### 主结果（HyperMem Table 1，LoCoMo Overall）

| claim.md | 实际 | 状态 |
|----------|------|------|
| HyperMem 92.73% | 92.73% | ✅ |
| HyperGraphRAG 86.49% | 86.49% | ✅ |
| LightRAG 79.87% | 79.87% | ✅ |

### 消融数字（HyperMem Table 2 + Figure 3）⚠️ 错误来源

**claim.md 原文：**
> "移除 Episode Context 导致整体 −3.76%、Multi-Hop −5.68%"

**实际情况：**
- `w/o EC`（移除 Episode Context）：Overall −3.76%、**Temporal −5.61%**（不是 Multi-Hop）
- `w/o TR & ER`（移除 Topic Retrieval + Episode Retrieval，扁平化为 Fact-only）：**Multi-Hop −5.68%**

**问题诊断**：claim.md 把两个不同消融条件的数字拼到了一起。Multi-Hop −5.68% 对应的是"完全扁平化为 Fact-only"，而非"移除 Episode Context"。

**修正建议（claim_refined.md 中采用）**：

> "移除 Episode 层（w/o EC）导致 Overall −3.76%、Temporal −5.61%；将层次结构完全扁平化为 Fact-only（w/o TR & ER）则导致 Multi-Hop −5.68%。两者共同验证了三层层次结构对不同类型推理的贡献——Episode 层主要承载时序连贯性，而 Topic/Episode 检索路径主要支撑多跳推理。"

这个修正反而**强化**了原论证——因为它把"层次结构"的贡献拆得更细致：Episode 层不仅服务多跳，更核心地支撑时序推理；完整层次结构服务多跳。

## 4. 其他相关工作覆盖检查

claim.md 仅讨论 MAGMA 和 HyperMem 两个基线。从两篇论文的 Related Work 章节看，对话记忆 RAG 领域至少还有以下重要工作需在 claim_refined.md 中至少简要提及：

### 4.1 同期超图方法
- **Hyper-RAG** (Feng et al., 2026, arXiv:2504.08758)：超图检索增强生成，但针对静态文档库
- **Cog-RAG** (Hu et al., 2026, arXiv:2511.13201)：认知启发的双超图 + 主题对齐
- **HyperGraphRAG** (Luo et al., 2025, arXiv:2503.21322)：HyperMem 的主要对比基线，86.49%

### 4.2 记忆系统（非超图）
- **MemGPT** (Packer et al., 2023)：OS 启发的分页记忆
- **Mem0** (Chhikara et al., 2025)：生产级长期记忆
- **A-MEM** (Xu et al., 2025, arXiv:2502.12110)：Zettelkasten 启发的自演化记忆
- **Zep** (Rasmussen et al., 2025, arXiv:2501.13956)：时序知识图谱记忆服务
- **Nemori** (Nan et al., 2025, arXiv:2508.03341)：认知启发的 episode 分段
- **MemoryOS / MemOS** (Kang/Li et al., 2025)：分层记忆操作系统
- **MIRIX** (Wang & Chen, 2025, arXiv:2507.07957)：多 mcp__agent 共享记忆

### 4.3 同作者后续工作
- **MAGMA 团队**有一篇 companion paper：*Anatomy of Agentic Memory: Taxonomy and Empirical Analysis*, arXiv:2601.09320（2026）——是 agentic memory 的系统性 taxonomy 综述，可作为 claim_refined.md 的领域定位参考。
- **MAGMA 团队**另一篇：*Hippocampus: An efficient and scalable memory module*, arXiv:2602.13594（2026）。

### 4.4 RQ2（知识演化）相关工作
claim.md 在 RQ2 上没有引用任何处理时效性/冲突的工作。需要补充：
- **Zep** (Rasmussen 2025) **明确处理时序知识演化**——这是一个直接竞争者，必须在 claim_refined.md 中讨论
- **MemoryBank** (Zhong 2024) 有"遗忘曲线"机制
- **A-MEM** 有"自演化"机制
- **MemInsight, Mem1, Memory-R1, Mem-α** 等通过 RL 优化记忆存储/检索策略

**RQ2 的真正定位需要修正**：不是"没人做过"，而是"现有方法做得不够好/不够正交"，需要明确 HiMGA 相对 Zep 等的差异。

## 5. 核验结论

| 项 | 数量 |
|----|------|
| 引用真实性 | 2/2 ✅ |
| 架构声明 | 全部正确 ✅ |
| MAGMA 数字 | 5/5 正确 ✅ |
| HyperMem 数字 | 3/3 主结果正确 ✅；消融数字 **1 处张冠李戴** ⚠️ |
| 关键概念错误 | 0 |
| 相关工作覆盖 | 不足，需扩展（特别是 Zep 对 RQ2 的影响）⚠️ |

**总体评估**：claim.md 的核心逻辑链可靠，但需要：
1. 修正 HyperMem 消融数字的归属错误
2. 在 RQ2 章节增加对 Zep 等时序知识图谱方法的讨论与差异化论证
3. 扩展相关工作覆盖至少到 5-8 个代表方法
4. 对 "MAGMA 输给 Full Context" 的论述更精确（仅限 knowledge-update 子集，非整体）
