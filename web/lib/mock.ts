// Mock SSE events — simulate full research pipeline without backend.
// Enable via NEXT_PUBLIC_MOCK=true env var, or `npm run dev:mock`.

import type { ClarifyResult, RefineResult, ResearchEvent } from "./api";

const MOCK_BRIEF = "对比 Transformer、Mamba 和 RWKV 三种架构在长文本建模任务上的效率与性能";

const MOCK_REPORT = `# Transformer、Mamba 与 RWKV 架构长文本建模对比

## 摘要

本报告对比三种序列建模架构在长文本任务上的表现。Transformer 凭借自注意力机制在性能上领先，但计算复杂度为 $O(n^2)$；Mamba 通过状态空间模型实现线性复杂度；RWKV 结合 RNN 与 Transformer 优势，在效率与性能间取得平衡。

## 1. Transformer 架构

Transformer 的自注意力机制使其能够捕捉任意距离的依赖关系，但序列长度 $n$ 增加时，计算和内存开销以 $O(n^2)$ 增长。稀疏注意力 [1] 和 FlashAttention [2] 等优化技术在一定程度上缓解了这一问题。

### 1.1 复杂度分析

标准 Transformer 的注意力计算需要 $n \\times n$ 的矩阵乘法。当 $n$ 超过 8K 时，单卡显存往往不足以容纳注意力矩阵。

## 2. Mamba 架构

Mamba 基于结构化状态空间模型（SSM），通过选择性扫描机制实现输入感知的序列建模 [3]。其计算复杂度为 $O(n)$，在长序列上具有显著效率优势。

### 2.1 核心机制

Mamba 的关键创新在于将 SSM 的参数与输入关联，使模型能够根据当前 token 动态调整状态转移。这使得 Mamba 在保留线性复杂度的同时，获得了接近 Transformer 的建模能力。

## 3. RWKV 架构

RWKV 采用线性注意力与时间混合机制，将传统 RNN 的训练效率与 Transformer 的并行性结合 [4]。其 WKV 算子实现线性复杂度下的全局依赖捕捉。

## 4. 对比分析

| 架构 | 复杂度 | 长文本效率 | 建模质量 | 生态成熟度 |
|------|--------|-----------|---------|-----------|
| Transformer | $O(n^2)$ | 低 | 最高 | 最成熟 |
| Mamba | $O(n)$ | 高 | 接近 Transformer | 快速发展 |
| RWKV | $O(n)$ | 高 | 良好 | 中等 |

在 Long Range Arena 基准上，Mamba 在大多数任务中达到或超过 Transformer 性能，同时推理速度提升 5-10 倍 [5]。

## 结论

对于长文本建模任务，Mamba 和 RWKV 在效率上具有明显优势，但 Transformer 在模型生态和工具链上更为成熟。实际应用中可根据任务需求在效率与性能间权衡。

## Sources

[1] Child et al. "Generating Long Sequences with Sparse Transformers." arXiv:1904.10509
[2] Dao et al. "FlashAttention: Fast and Memory-Efficient Exact Attention." NeurIPS 2022
[3] Gu & Dao. "Mamba: Linear-Time Sequence Modeling with Selective State Spaces." arXiv:2312.00752
[4] Peng et al. "RWKV: Reinventing RNNs for the Transformer Era." EMNLP 2023
[5] Tay et al. "Long Range Arena: A Benchmark for Efficient Transformers." ICLR 2021
`;

export function mockClarify(_query: string): Promise<ClarifyResult> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        is_clear: false,
        brief: null,
        directions: [
          "对比三种架构在长文本（8K+ token）上的推理速度和显存占用",
          "分析它们在 Long Range Arena 等基准测试上的性能差异",
          "调查各架构在生产环境中的实际部署情况和生态成熟度",
        ],
        message: "这是个很好的研究方向！我有几个建议方向供你参考，你也可以输入自己的具体关注点：",
      });
    }, 1200);
  });
}

export function mockRefine(_query: string, _response: string): Promise<RefineResult> {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({ brief: MOCK_BRIEF });
    }, 2000);
  });
}

let _mockRunning = false;

export function startMockResearch(
  _brief: string,
  onEvent: (event: ResearchEvent) => void,
): () => void {
  if (_mockRunning) {
    console.warn("Mock research already running — skipping duplicate start");
    return () => {};
  }
  _mockRunning = true;
  let cancelled = false;
  const timers: ReturnType<typeof setTimeout>[] = [];

  function schedule(delay: number, fn: () => void) {
    const t = setTimeout(() => {
      if (!cancelled) fn();
    }, delay);
    timers.push(t);
  }

  // 1. Plan — after 1.5s (clarify settled → brief shown → plan)
  schedule(1500, () => {
    onEvent({
      type: "plan",
      sub_questions: [
        { label: "长文本推理效率", question: "对比 Transformer、Mamba、RWKV 在 8K+ token 序列上的推理速度和显存占用" },
        { label: "基准测试性能", question: "分析三种架构在 Long Range Arena 等长文本基准测试上的性能差异" },
        { label: "生产部署成熟度", question: "调查各架构在生产环境中的实际部署情况、工具链和社区生态" },
      ],
    });
  });

  // 2. Research events — ~4s apart to show each sub-question completing
  schedule(4500, () => {
    onEvent({
      type: "research",
      question: "对比 Transformer、Mamba、RWKV 在 8K+ token 序列上的推理速度和显存占用",
      preview: "FlashAttention 将标准自注意力的显存占用从 O(n²) 降到 O(n)。Mamba 的选择性扫描在 16K token 时推理速度比 FlashAttention-2 Transformer 快 5 倍...",
      tool_call_counts: {
        "mcp__brave-search__brave_web_search": 2,
        "mcp__fetch__fetch": 2,
        "rag_search": 1,
        "mcp__paper-search__search_arxiv": 1,
      },
    });
  });

  schedule(8500, () => {
    onEvent({
      type: "research",
      question: "分析三种架构在 Long Range Arena 等长文本基准测试上的性能差异",
      preview: "在 LRA 基准的 Pathfinder-256 任务上，Mamba 达到 94.2% 准确率（Transformer 92.8%），在 ListOps 任务上 S4 变体达到 59.7%...",
      tool_call_counts: {
        "mcp__brave-search__brave_web_search": 1,
        "mcp__paper-search__search_google_scholar": 1,
        "mcp__paper-search__read_arxiv_paper": 1,
        "mcp__fetch__fetch": 1,
      },
    });
  });

  schedule(12500, () => {
    onEvent({
      type: "research",
      question: "调查各架构在生产环境中的实际部署情况、工具链和社区生态",
      preview: "HuggingFace Transformers 已支持 Mamba 模型，RWKV 官方提供 .pth 权重可直接加载。Mamba 的 CUDA 实现已合并到官方仓库...",
      tool_call_counts: {
        "mcp__brave-search__brave_web_search": 2,
        "mcp__github__search_repositories": 1,
        "mcp__github__get_file_contents": 1,
        "mcp__fetch__fetch": 1,
        "rag_search": 1,
      },
    });
  });

  // 3. Review — after all research done, show "审查中" shimmer briefly
  schedule(16500, () => {
    onEvent({
      type: "review",
      round: 1,
      review_summary: [
        {
          question: "对比 Transformer、Mamba、RWKV 在 8K+ token 序列上的推理速度和显存占用",
          verdict: "approved",
          failed: {},
          evidence: {
            relevance: "内容直接对比三种架构的推理效率 ✓",
            depth: "包含 FlashAttention 等具体优化技术 ✓",
            citations: "4 处数据引用满足阈值 ✓",
            sources: "arxiv + web 多源交叉验证 ✓",
            completeness: "覆盖推理速度、显存占用两个维度 ✓",
          },
        },
        {
          question: "分析三种架构在 Long Range Arena 等长文本基准测试上的性能差异",
          verdict: "approved",
          failed: {},
          evidence: {
            relevance: "LRA 基准对比为核心内容 ✓",
            depth: "含具体任务和数值 ✓",
            citations: "足够的数据支撑 ✓",
            sources: "多源验证 ✓",
            completeness: "覆盖 Pathfinder、ListOps 等主要子任务 ✓",
          },
        },
        {
          question: "调查各架构在生产环境中的实际部署情况、工具链和社区生态",
          verdict: "approved",
          failed: {},
          evidence: {
            relevance: "部署和生态分析切题 ✓",
            depth: "涵盖 HF 支持、GitHub、CUDA 实现 ✓",
            citations: "引用充分 ✓",
            sources: "GitHub + web 多源 ✓",
            completeness: "覆盖工具链、社区、生产部署三个层面 ✓",
          },
        },
      ],
    });
  });

  // 4. Write — report after review settles
  schedule(20000, () => {
    onEvent({ type: "write", report: MOCK_REPORT });
  });

  // 5. Stats
  schedule(21000, () => {
    onEvent({
      type: "stats",
      total_calls: 14,
      prompt_tokens: 38500,
      completion_tokens: 8200,
      total_tokens: 46700,
    });
  });

  return () => {
    cancelled = true;
    _mockRunning = false;
    timers.forEach(clearTimeout);
  };
}
