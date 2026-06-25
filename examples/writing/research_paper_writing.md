# Example: Research Paper Writing (Computer Science)

## User Request

```
Напиши методологию написания научной статьи для CS-конференции (structure, LaTeX template, peer review process).
```

## Reasoning

**Domain:** Writing (Academic writing, research methodology)
**Complexity:** Complex
**Model:** Opus

## Response

---

# Research Paper Writing Framework

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RESEARCH PAPER STRUCTURE (Standard CS Conference)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. TITLE & ABSTRACT (10% of writing time, 90% of impact)                  │
│     └─► Hook readers in 150 words                                           │
│                                                                              │
│  2. INTRODUCTION (15% of time)                                              │
│     ├─► Problem statement                                                   │
│     ├─► Motivation (why this matters)                                       │
│     ├─► Contributions (numbered list)                                       │
│     └─► Paper organization                                                  │
│                                                                              │
│  3. RELATED WORK (10% of time)                                              │
│     └─► Compare vs. prior art (table format)                                │
│                                                                              │
│  4. METHODOLOGY (25% of time)                                               │
│     ├─► System architecture (diagram)                                       │
│     ├─► Algorithms (pseudocode)                                             │
│     └─► Implementation details                                              │
│                                                                              │
│  5. EVALUATION (30% of time)                                                │
│     ├─► Experimental setup                                                  │
│     ├─► Benchmarks (graphs, tables)                                         │
│     └─► Analysis & discussion                                               │
│                                                                              │
│  6. CONCLUSION (5% of time)                                                 │
│     └─► Summarize contributions + future work                               │
│                                                                              │
│  7. REFERENCES (5% of time)                                                 │
│     └─► BibTeX entries (30-50 papers)                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## LaTeX Template (ACM SIGPLAN Style)

### File: paper.tex

```latex
\documentclass[sigplan,screen]{acmart}

% Conference metadata
\acmConference[ICSE'25]{47th International Conference on Software Engineering}{April 2025}{Ottawa, Canada}
\acmYear{2025}
\copyrightyear{2025}

% Packages
\usepackage{balance}
\usepackage{booktabs}
\usepackage{subcaption}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{listings}
\usepackage{xcolor}

% Code listing style
\lstset{
    basicstyle=\ttfamily\small,
    keywordstyle=\color{blue},
    commentstyle=\color{gray},
    stringstyle=\color{red},
    numbers=left,
    numberstyle=\tiny\color{gray},
    breaklines=true,
    frame=single
}

% Custom commands
\newcommand{\tool}[1]{\textsc{#1}}  % Tool names in small caps
\newcommand{\eg}{\textit{e.g.,}\xspace}
\newcommand{\ie}{\textit{i.e.,}\xspace}

% Paper metadata
\title{FastCache: A High-Performance In-Memory Caching System with Adaptive Eviction}

\author{John Doe}
\affiliation{%
  \institution{University of Example}
  \city{San Francisco}
  \state{CA}
  \country{USA}
}
\email{john.doe@example.edu}

\author{Jane Smith}
\affiliation{%
  \institution{Tech Corp}
  \city{Seattle}
  \state{WA}
  \country{USA}
}
\email{jane.smith@techcorp.com}

\begin{document}

% ----------------------------------------------------------------------------
% ABSTRACT (150-250 words)
% ----------------------------------------------------------------------------

\begin{abstract}
Modern web applications rely heavily on caching to achieve low latency and high throughput. However, existing caching systems use static eviction policies (\eg LRU, LFU) that fail to adapt to changing workload patterns, leading to suboptimal hit rates. We present \tool{FastCache}, a novel in-memory caching system that uses machine learning to predict future access patterns and dynamically adjust its eviction policy. \tool{FastCache} achieves 25-40\% higher hit rates compared to Redis and Memcached across diverse workloads while maintaining sub-millisecond latency. Our key contributions are: (1) an adaptive eviction algorithm based on temporal convolutional networks (TCNs), (2) a lightweight feature extraction pipeline that adds <5\% overhead, and (3) an open-source implementation compatible with existing Redis clients. Evaluation on production traces from Twitter, Wikipedia, and e-commerce sites demonstrates that \tool{FastCache} consistently outperforms state-of-the-art baselines. The system is publicly available at \url{https://github.com/example/fastcache}.
\end{abstract}

% CCS Concepts (ACM Classification)
\begin{CCSXML}
<ccs2012>
<concept>
<concept_id>10002951.10003260.10003282</concept_id>
<concept_desc>Information systems~Data management systems</concept_desc>
<concept_significance>500</concept_significance>
</concept>
<concept>
<concept_id>10010147.10010257</concept_id>
<concept_desc>Computing methodologies~Machine learning</concept_desc>
<concept_significance>300</concept_significance>
</concept>
</ccs2012>
\end{CCSXML}

\ccsdesc[500]{Information systems~Data management systems}
\ccsdesc[300]{Computing methodologies~Machine learning}

\keywords{Caching, Machine Learning, Performance Optimization}

\maketitle

% ----------------------------------------------------------------------------
% INTRODUCTION (2 pages)
% ----------------------------------------------------------------------------

\section{Introduction}
\label{sec:intro}

Web applications serve billions of users worldwide, requiring ultra-low latency and high throughput. In-memory caching is a critical component of modern web stacks, reducing database load by 80-95\%~\cite{redis-paper}. However, cache performance heavily depends on the \textbf{eviction policy}—the algorithm that decides which items to remove when the cache is full.

Traditional eviction policies like Least Recently Used (LRU) and Least Frequently Used (LFU) make \textit{static} decisions based on historical access patterns. These policies fail when workload characteristics change (\eg sudden traffic spikes, diurnal patterns, viral content). For example, LRU evicts items that haven't been accessed recently, even if they are likely to be accessed soon (Figure~\ref{fig:lru-failure}).

\begin{figure}[t]
\centering
\includegraphics[width=0.8\columnwidth]{figures/lru-failure.pdf}
\caption{LRU eviction fails on workloads with periodic access patterns (Twitter timeline cache). Items evicted at $t=100$ are immediately re-accessed at $t=120$, causing cache misses.}
\label{fig:lru-failure}
\end{figure}

\subsection{Motivation}

We analyzed production cache traces from three sources:
\begin{itemize}
    \item \textbf{Twitter:} 1.2 billion requests over 7 days
    \item \textbf{Wikipedia:} 800 million page views over 14 days
    \item \textbf{E-commerce:} 500 million product queries over 30 days
\end{itemize}

Our findings reveal:
\begin{enumerate}
    \item \textbf{Temporal patterns:} 65\% of cache misses occur for items evicted within the last 10 minutes (Figure~\ref{fig:recency}).
    \item \textbf{Predictability:} Access patterns exhibit strong temporal correlations ($r = 0.78$), making them predictable with ML models.
    \item \textbf{Overhead constraints:} Production caches tolerate <5\% CPU overhead for eviction decisions.
\end{enumerate}

\subsection{Our Approach: Adaptive Eviction with ML}

We propose \tool{FastCache}, an in-memory caching system that uses \textit{temporal convolutional networks (TCNs)} to predict future access probabilities. Key design decisions:

\begin{enumerate}
    \item \textbf{Lightweight model:} TCN architecture requires only 100KB memory and <100 $\mu$s inference time.
    \item \textbf{Online learning:} Model adapts to workload changes without offline retraining.
    \item \textbf{Compatibility:} Drop-in replacement for Redis—no application code changes.
\end{enumerate}

\subsection{Contributions}

This paper makes the following contributions:

\begin{enumerate}
    \item \textbf{Adaptive eviction algorithm} (Section~\ref{sec:algorithm}) that combines ML predictions with LRU fallback for robustness.
    \item \textbf{Feature extraction pipeline} (Section~\ref{sec:features}) that captures temporal patterns with <5\% overhead.
    \item \textbf{System implementation} (Section~\ref{sec:implementation}) compatible with Redis protocol (6K lines of C++).
    \item \textbf{Comprehensive evaluation} (Section~\ref{sec:evaluation}) on production traces and synthetic benchmarks.
\end{enumerate}

\subsection{Paper Organization}

The rest of this paper is organized as follows. Section~\ref{sec:related} surveys related work on caching and ML-based systems. Section~\ref{sec:overview} provides an overview of \tool{FastCache} architecture. Sections~\ref{sec:algorithm} and~\ref{sec:features} detail the adaptive eviction algorithm and feature extraction. Section~\ref{sec:implementation} describes implementation. Section~\ref{sec:evaluation} presents experimental results. Section~\ref{sec:conclusion} concludes.

% ----------------------------------------------------------------------------
% RELATED WORK (1.5 pages)
% ----------------------------------------------------------------------------

\section{Related Work}
\label{sec:related}

\subsection{Traditional Caching Policies}

Classical eviction policies fall into three categories:

\begin{itemize}
    \item \textbf{Recency-based:} LRU~\cite{lru}, CLOCK~\cite{clock}, MRU
    \item \textbf{Frequency-based:} LFU~\cite{lfu}, LRU-K~\cite{lru-k}
    \item \textbf{Hybrid:} ARC~\cite{arc}, LIRS~\cite{lirs}, TinyLFU~\cite{tinylfu}
\end{itemize}

Table~\ref{tab:policies} compares these policies. All use \textit{static} heuristics and cannot adapt to workload changes.

\begin{table}[t]
\centering
\caption{Comparison of eviction policies}
\label{tab:policies}
\begin{tabular}{lccc}
\toprule
Policy & Hit Rate & Overhead & Adaptivity \\
\midrule
LRU     & 68.2\% & O(1)     & No \\
LFU     & 72.1\% & O(log n) & No \\
ARC     & 75.3\% & O(1)     & Partial \\
\tool{FastCache} & \textbf{89.7\%} & O(1)     & \textbf{Yes} \\
\bottomrule
\end{tabular}
\end{table}

\subsection{ML-Based Caching}

Recent work explores using ML for cache management:

\begin{itemize}
    \item \textbf{LeCaR}~\cite{lecar}: Uses reinforcement learning but requires offline training.
    \item \textbf{Belady-ML}~\cite{belady-ml}: Predicts optimal eviction (Belady's algorithm) but assumes future knowledge.
    \item \textbf{LHD}~\cite{lhd}: Uses LSTM but incurs 15\% overhead (too high for production).
\end{itemize}

\tool{FastCache} differs by using lightweight TCNs with <5\% overhead and online learning.

% ----------------------------------------------------------------------------
% SYSTEM OVERVIEW (1 page)
% ----------------------------------------------------------------------------

\section{System Overview}
\label{sec:overview}

Figure~\ref{fig:architecture} shows \tool{FastCache} architecture. The system consists of:

\begin{enumerate}
    \item \textbf{Redis-compatible server:} Handles GET/SET/DEL commands.
    \item \textbf{Feature extractor:} Computes temporal features from access log.
    \item \textbf{TCN predictor:} Predicts future access probability for each cached item.
    \item \textbf{Eviction engine:} Selects victim using predicted probabilities + LRU fallback.
\end{enumerate}

\begin{figure*}[t]
\centering
\includegraphics[width=0.9\textwidth]{figures/architecture.pdf}
\caption{\tool{FastCache} architecture. Blue arrows show data flow for cache hits; red arrows show eviction flow when cache is full.}
\label{fig:architecture}
\end{figure*}

% ----------------------------------------------------------------------------
% ALGORITHM (3 pages)
% ----------------------------------------------------------------------------

\section{Adaptive Eviction Algorithm}
\label{sec:algorithm}

Algorithm~\ref{alg:eviction} shows the core eviction logic.

\begin{algorithm}[t]
\caption{Adaptive Eviction in \tool{FastCache}}
\label{alg:eviction}
\begin{algorithmic}[1]
\Require Cache $C$, item to insert $k$, predictor $P$
\Ensure Item $k$ inserted, victim evicted if cache full

\If{$|C| < \text{capacity}$}
    \State $C \gets C \cup \{k\}$ \Comment{Cache not full}
    \State \Return
\EndIf

\State $scores \gets \{\}$
\For{$item \in C$}
    \State $features \gets \text{ExtractFeatures}(item)$ \Comment{Section~\ref{sec:features}}
    \State $prob \gets P.\text{predict}(features)$ \Comment{Access probability}
    \State $scores[item] \gets prob \cdot \alpha + \text{LRU\_score}(item) \cdot (1 - \alpha)$
\EndFor

\State $victim \gets \arg\min_{item} scores[item]$ \Comment{Lowest score = evict}
\State $C \gets C \setminus \{victim\}$
\State $C \gets C \cup \{k\}$
\State \Return $victim$
\end{algorithmic}
\end{algorithm}

\subsection{Design Rationale}

\textbf{Hybrid scoring:} Line 7 combines ML prediction ($prob$) with LRU fallback using hyperparameter $\alpha \in [0, 1]$. This provides robustness: if predictor fails, LRU ensures reasonable performance.

\textbf{Complexity:} Algorithm runs in $O(n)$ time where $n = $ cache size. In practice, we optimize to $O(1)$ amortized by maintaining a heap (Section~\ref{sec:implementation}).

% ----------------------------------------------------------------------------
% FEATURE EXTRACTION (2 pages)
% ----------------------------------------------------------------------------

\section{Feature Extraction}
\label{sec:features}

For each cached item, we extract 12 temporal features:

\begin{enumerate}
    \item \textbf{Recency:} Time since last access (seconds)
    \item \textbf{Frequency:} Access count in last hour
    \item \textbf{Hour of day:} One-hot encoded (24 dims) → embedding
    \item \textbf{Day of week:} One-hot encoded (7 dims) → embedding
    \item \textbf{Inter-arrival times:} Mean, stddev, median of time between accesses
\end{enumerate}

\subsection{Temporal Convolutional Network (TCN)}

Figure~\ref{fig:tcn} shows our TCN architecture. The model has:
\begin{itemize}
    \item Input layer: 12 features
    \item 3 dilated convolutional layers (dilation = 1, 2, 4)
    \item Output layer: Single neuron (access probability)
    \item Parameters: 15,000 (100KB memory)
\end{itemize}

\textbf{Inference time:} 87 $\mu$s (measured on Intel Xeon E5-2680)

% ----------------------------------------------------------------------------
% IMPLEMENTATION (2 pages)
% ----------------------------------------------------------------------------

\section{Implementation}
\label{sec:implementation}

\tool{FastCache} is implemented in C++ (6,000 lines). Key components:

\subsection{Redis Protocol Compatibility}

We implement Redis Serialization Protocol (RESP) for compatibility:

\begin{lstlisting}[language=C++, caption=RESP parser (simplified)]
enum class RESPType { String, Integer, Array, Error };

struct RESPValue {
    RESPType type;
    std::string data;
    std::vector<RESPValue> array;
};

RESPValue parse_resp(const char* buffer, size_t len) {
    switch (buffer[0]) {
        case '+': return {RESPType::String, std::string(buffer+1, len-1)};
        case ':': return {RESPType::Integer, std::string(buffer+1, len-1)};
        case '*': return parse_array(buffer, len);
        case '-': return {RESPType::Error, std::string(buffer+1, len-1)};
    }
}
\end{lstlisting}

\subsection{Optimized Eviction (Heap-Based)}

We use a min-heap to track eviction candidates:

\begin{lstlisting}[language=C++, caption=Eviction heap]
#include <queue>

struct CacheItem {
    std::string key;
    std::string value;
    double score;  // Predicted access probability

    bool operator<(const CacheItem& other) const {
        return score > other.score;  // Min-heap
    }
};

std::priority_queue<CacheItem> eviction_heap;

void evict() {
    auto victim = eviction_heap.top();
    eviction_heap.pop();
    cache.erase(victim.key);
}
\end{lstlisting}

% ----------------------------------------------------------------------------
% EVALUATION (4 pages)
% ----------------------------------------------------------------------------

\section{Evaluation}
\label{sec:evaluation}

\subsection{Experimental Setup}

\textbf{Hardware:} AWS EC2 c5.4xlarge (16 vCPUs, 32GB RAM)

\textbf{Datasets:}
\begin{itemize}
    \item Twitter trace: 1.2B requests, 500K unique keys
    \item Wikipedia trace: 800M requests, 2M unique keys
    \item E-commerce trace: 500M requests, 100K unique keys
\end{itemize}

\textbf{Baselines:}
\begin{itemize}
    \item Redis 7.0 (LRU)
    \item Memcached 1.6 (LRU)
    \item ARC (Adaptive Replacement Cache)
    \item LeCaR (RL-based)
\end{itemize}

\subsection{Results: Hit Rate}

Figure~\ref{fig:hitrate} shows hit rates across workloads. \tool{FastCache} achieves:
\begin{itemize}
    \item \textbf{Twitter:} 89.7\% (vs. Redis 68.2\%, +31\%)
    \item \textbf{Wikipedia:} 85.3\% (vs. Redis 70.1\%, +22\%)
    \item \textbf{E-commerce:} 91.2\% (vs. Redis 72.8\%, +25\%)
\end{itemize}

\begin{figure}[t]
\centering
\includegraphics[width=0.9\columnwidth]{figures/hitrate.pdf}
\caption{Hit rate comparison across workloads. \tool{FastCache} consistently outperforms baselines.}
\label{fig:hitrate}
\end{figure}

\subsection{Results: Latency}

Table~\ref{tab:latency} shows p50, p95, p99 latencies. \tool{FastCache} adds <100 $\mu$s overhead compared to Redis.

\begin{table}[t]
\centering
\caption{Latency comparison (microseconds)}
\label{tab:latency}
\begin{tabular}{lccc}
\toprule
System & p50 & p95 & p99 \\
\midrule
Redis        & 120 & 350 & 800 \\
\tool{FastCache} & 210 & 450 & 920 \\
Overhead     & +90 & +100 & +120 \\
\bottomrule
\end{tabular}
\end{table}

% ----------------------------------------------------------------------------
% CONCLUSION (0.5 pages)
% ----------------------------------------------------------------------------

\section{Conclusion}
\label{sec:conclusion}

We presented \tool{FastCache}, an adaptive in-memory caching system that uses machine learning to improve hit rates by 25-40\% compared to Redis and Memcached. Our key insight is that temporal patterns in cache workloads are highly predictable, enabling lightweight ML models to significantly outperform static eviction policies. \tool{FastCache} is open-source and production-ready.

\subsection{Future Work}

\begin{itemize}
    \item \textbf{Multi-cache coordination:} Extend to distributed caching (CDN, multi-region)
    \item \textbf{Hardware acceleration:} FPGA-based TCN inference for <10 $\mu$s latency
    \item \textbf{Automated tuning:} Hyperparameter search for $\alpha$ (ML vs. LRU weight)
\end{itemize}

% ----------------------------------------------------------------------------
% REFERENCES
% ----------------------------------------------------------------------------

\bibliographystyle{ACM-Reference-Format}
\bibliography{references}

\end{document}
```

---

## BibTeX File: references.bib

```bibtex
@article{redis-paper,
  author = {Sanfilippo, Salvatore and Noordhuis, Pieter},
  title = {Redis: An In-Memory Data Structure Store},
  journal = {ACM Queue},
  year = {2015},
  volume = {13},
  number = {5},
  pages = {50--57},
  doi = {10.1145/2789149.2789169}
}

@inproceedings{lru,
  author = {Denning, Peter J.},
  title = {The Working Set Model for Program Behavior},
  booktitle = {SOSP '68},
  year = {1968},
  pages = {33--46},
  doi = {10.1145/800001.811669}
}

@article{arc,
  author = {Megiddo, Nimrod and Modha, Dharmendra S.},
  title = {ARC: A Self-Tuning, Low Overhead Replacement Cache},
  journal = {USENIX FAST},
  year = {2003},
  pages = {115--130}
}

@inproceedings{lecar,
  author = {Vietri, Giuseppe and others},
  title = {LeCaR: Learning Cache Replacement with Deep Reinforcement Learning},
  booktitle = {SoCC '18},
  year = {2018},
  pages = {54--66},
  doi = {10.1145/3267809.3267828}
}

@inproceedings{belady-ml,
  author = {Shi, Zhenyu and others},
  title = {Applying Deep Learning to the Cache Replacement Problem},
  booktitle = {MICRO '19},
  year = {2019},
  pages = {413--425},
  doi = {10.1145/3352460.3358319}
}
```

---

## Writing Process Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RESEARCH PAPER WRITING STAGES (12 weeks)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Week 1-2: IDEATION                                                         │
│  ├─► Read 50+ related papers (build bibliography)                           │
│  ├─► Identify research gap (what's missing?)                                │
│  └─► Formulate hypothesis (testable claim)                                  │
│                                                                              │
│  Week 3-4: EXPERIMENTATION                                                  │
│  ├─► Implement prototype                                                    │
│  ├─► Run experiments (collect data)                                         │
│  └─► Generate graphs/tables                                                 │
│                                                                              │
│  Week 5-6: WRITING DRAFT                                                    │
│  ├─► Start with Methods + Evaluation (easiest)                              │
│  ├─► Then Introduction + Related Work                                       │
│  └─► Abstract + Conclusion last                                             │
│                                                                              │
│  Week 7: INTERNAL REVIEW                                                    │
│  ├─► Share with co-authors                                                  │
│  ├─► Address feedback                                                       │
│  └─► Revise figures/tables                                                  │
│                                                                              │
│  Week 8: POLISHING                                                          │
│  ├─► Grammar check (Grammarly)                                              │
│  ├─► Citation consistency (BibTeX)                                          │
│  └─► LaTeX formatting                                                       │
│                                                                              │
│  Week 9-10: PRE-SUBMISSION REVIEW                                           │
│  ├─► Send to external reviewers (colleagues)                                │
│  ├─► Incorporate feedback                                                   │
│  └─► Prepare rebuttal for anticipated questions                             │
│                                                                              │
│  Week 11: SUBMISSION                                                        │
│  ├─► Final proofreading                                                     │
│  ├─► Package supplementary materials                                        │
│  └─► Submit to conference (HotCRP, EasyChair, etc.)                         │
│                                                                              │
│  Week 12: REBUTTAL PREPARATION                                              │
│  ├─► Anticipate reviewer concerns                                           │
│  ├─► Prepare answers (1-2 pages)                                            │
│  └─► Ready to respond in 48 hours                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Common Writing Anti-Patterns

| Anti-Pattern | Why Bad | Solution |
|--------------|---------|----------|
| **"It is well-known that..."** | Cites no source, assumes knowledge | Cite papers or remove claim |
| **Passive voice overuse** | "The system was designed..." | Active: "We designed the system..." |
| **Vague contributions** | "We improve performance" | Quantify: "We improve by 25%" |
| **Missing baselines** | Only show your system | Compare vs. Redis, Memcached, etc. |
| **Cherry-picked results** | Only show wins, hide losses | Show full picture (honest evaluation) |
| **No error bars** | Single data point | Show mean ± stddev over 10 runs |
| **Illegible figures** | Tiny fonts, no labels | Readable at print size (9pt min) |
| **Too many acronyms** | LRU, LFU, TCN, RESP, ML... | Define on first use |

---

## Peer Review Process Simulation

### Typical Review Form

```
Paper ID: 1234
Title: FastCache: A High-Performance In-Memory Caching System

OVERALL RECOMMENDATION: ⭐⭐⭐⭐ (Accept)

STRENGTHS:
1. Novel approach to cache eviction using TCNs (not explored before)
2. Comprehensive evaluation (3 real-world traces, 4 baselines)
3. Significant performance improvement (25-40% hit rate increase)
4. Open-source implementation (reproducibility)
5. Well-written (clear motivation, good figures)

WEAKNESSES:
1. Limited to single-node cache (no distributed caching)
2. TCN overhead not tested on ARM/lower-end hardware
3. Missing ablation study (which features matter most?)
4. No discussion of cold-start problem (model needs training data)

QUESTIONS FOR AUTHORS:
1. How does FastCache perform on adversarial workloads (random access)?
2. What is the model retraining frequency (daily? weekly?)?
3. Can the approach generalize to CDN caching (larger scales)?

DETAILED COMMENTS:

Section 1 (Intro):
+ Good motivation with real production traces
+ Clear problem statement
- Could cite more recent work (2023-2024 papers missing)

Section 4 (Algorithm):
+ Algorithm 1 is clear
- Line 7: How is α chosen? Needs explanation or ablation study

Section 6 (Evaluation):
+ Comprehensive benchmarks
- Missing comparison with LHD [ref 23] (recent LSTM-based cache)
- No error bars on Figure 5 (hit rate graph)

TYPOS/MINOR ISSUES:
- Page 3, line 15: "achives" → "achieves"
- Figure 2: Legend text too small (increase font to 10pt)
- Table 1: Missing unit for "Overhead" column

OVERALL:
Strong paper with significant contributions. The adaptive eviction approach is novel and well-executed. Evaluation is thorough but could benefit from ablation studies and adversarial workload testing. I recommend ACCEPT with minor revisions.

CONFIDENCE: ⭐⭐⭐⭐ (High)
```

---

## Rebuttal Strategy

### Example Rebuttal (1 page, responding to above review)

```
We thank the reviewers for their thoughtful feedback. Below we address key concerns:

══════════════════════════════════════════════════════════════
REVIEWER 2: Missing ablation study (feature importance)
══════════════════════════════════════════════════════════════

We ran an ablation study removing features one at a time:

| Feature Removed | Hit Rate (Twitter) | Impact |
|-----------------|-------------------|--------|
| None (full)     | 89.7%             | —      |
| - Recency       | 82.1%             | -7.6%  |
| - Frequency     | 85.3%             | -4.4%  |
| - Hour of day   | 87.2%             | -2.5%  |
| - Inter-arrival | 88.9%             | -0.8%  |

Result: Recency and frequency are most critical. We will add this table to Section 6.3 (Ablation Study).

══════════════════════════════════════════════════════════════
REVIEWER 3: Cold-start problem not discussed
══════════════════════════════════════════════════════════════

Good point. FastCache uses LRU-only mode during cold start (first 1000 requests) until sufficient training data is collected. We measured cold-start overhead:

- Hit rate during cold start: 68.2% (same as Redis LRU)
- Hit rate after warm-up (5 min): 89.7% (full FastCache)

We will add this analysis to Section 6.4 (Cold Start).

══════════════════════════════════════════════════════════════
REVIEWER 2: Adversarial workloads (random access)
══════════════════════════════════════════════════════════════

We tested on synthetic random access (worst case):

| Workload     | FastCache | Redis | Difference |
|--------------|-----------|-------|------------|
| Twitter      | 89.7%     | 68.2% | +31%       |
| Random       | 65.1%     | 64.8% | +0.3%      |

Result: FastCache degrades gracefully to LRU performance on unpredictable workloads (hybrid scoring with α=0.5 ensures robustness). We will add this to Section 6.5.

══════════════════════════════════════════════════════════════
REVIEWER 1: Missing citation (LHD cache, 2023)
══════════════════════════════════════════════════════════════

Thank you for pointing this out. We added LHD [ref 23] to Related Work:

"LHD uses LSTM but incurs 15% overhead. FastCache uses TCN (100KB vs 2MB) with <5% overhead, making it production-viable."

══════════════════════════════════════════════════════════════
MINOR FIXES
══════════════════════════════════════════════════════════════

- Fixed typo: "achives" → "achieves" (page 3, line 15)
- Increased Figure 2 legend font to 10pt
- Added units to Table 1 ("Overhead" column: CPU %)
- Added error bars to Figure 5 (mean ± stddev, n=10)
```

---

## Key Takeaways

1. **Structure matters** — Follow standard format (Intro → Related → Methods → Eval → Conclusion)
2. **Contributions upfront** — Numbered list in Introduction (readers skim)
3. **Quantify everything** — "Improves performance" → "25-40% higher hit rate"
4. **Compare vs. baselines** — Never show only your system
5. **Open-source wins** — Reproducibility increases acceptance rate (ICSE: 45% → 68%)
6. **Anticipate reviewers** — Prepare rebuttal before submission

**Writing Formula:**
```
Problem + Motivation → Contributions → Evaluation → Honest Comparison → Reproducibility
```

**Time Investment:**
- Research + Experiments: 6-8 weeks
- Writing draft: 2 weeks
- Revisions: 2 weeks
- Total: 10-12 weeks (3 months)

**Tools:** Overleaf (LaTeX), BibTeX, TikZ (figures), Grammarly, Zotero (references)

**Target Acceptance Rate:**
- Top-tier (SOSP, OSDI, PLDI): 15-20%
- Tier-1 (ICSE, FSE, USENIX ATC): 25-30%
- Tier-2 (Middleware, ICDCS): 30-40%
