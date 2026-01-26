# Phase 3: 情绪因子模块

**状态**：🔲 待开始
**预计周期**：1-2 周
**优先级**：P1

---

## 1. 目标

引入新闻舆情数据，构建情绪因子，为模型提供另类数据维度。

---

## 2. 任务清单

| ID | 任务 | 优先级 | 状态 | 产出 |
|----|------|--------|------|------|
| 3.1 | 新闻数据源适配器 | P0 | 🔲 | `data/news_source.py` |
| 3.2 | 情绪分析模型封装 | P0 | 🔲 | `nlp/sentiment.py` |
| 3.3 | 情绪因子计算 | P1 | 🔲 | `features/sentiment.py` |
| 3.4 | 时间对齐工具 | P1 | 🔲 | `fusion/temporal_aligner.py` |
| 3.5 | 宏观政策信号 (可选) | P2 | 🔲 | `nlp/policy_signal.py` |
| 3.6 | 单元测试 | P1 | 🔲 | `tests/test_sentiment.py` |

---

## 3. 详细设计

### 3.1 新闻数据源 (Task 3.1)

**文件**：`src/ashare_lab/data/news_source.py`

```python
from dataclasses import dataclass
from datetime import datetime
import pandas as pd

@dataclass
class NewsItem:
    """新闻条目"""
    publish_time: datetime
    title: str
    content: str
    source: str
    symbols: list[str]  # 关联股票

@dataclass
class NewsRequest:
    start_date: str  # YYYYMMDD
    end_date: str
    symbols: list[str] | None = None  # 可选：过滤特定股票

class NewsSource:
    """
    新闻数据源抽象基类

    支持多种数据源：
    - AkShare 财经新闻
    - 公告数据
    - 自定义爬虫
    """

    def fetch(self, request: NewsRequest) -> list[NewsItem]:
        raise NotImplementedError

class AkShareNewsSource(NewsSource):
    """AkShare 新闻数据源"""

    def fetch(self, request: NewsRequest) -> list[NewsItem]:
        import akshare as ak

        # 获取财经新闻
        df = ak.stock_news_em(symbol="财经")

        # 转换格式
        items = []
        for _, row in df.iterrows():
            items.append(NewsItem(
                publish_time=row["发布时间"],
                title=row["新闻标题"],
                content=row["新闻内容"],
                source=row["来源"],
                symbols=self._extract_symbols(row["新闻内容"]),
            ))

        return items

    def _extract_symbols(self, text: str) -> list[str]:
        """从文本中提取股票代码"""
        import re
        pattern = r'[036]\d{5}'
        return re.findall(pattern, text)
```

### 3.2 情绪分析模型 (Task 3.2)

**文件**：`src/ashare_lab/nlp/sentiment.py`

```python
from enum import Enum
from dataclasses import dataclass

class SentimentBackend(Enum):
    FINBERT = "finbert"      # 金融领域预训练
    DEEPSEEK = "deepseek"    # DeepSeek API
    SIMPLE = "simple"        # 简单规则（词典）

@dataclass
class SentimentResult:
    score: float        # [-1, 1]
    label: str          # positive/negative/neutral
    confidence: float   # [0, 1]

class SentimentAnalyzer:
    """
    情绪分析器

    支持多种后端，可根据需求切换
    """

    def __init__(self, backend: SentimentBackend = SentimentBackend.FINBERT):
        self.backend = backend
        self._init_model()

    def _init_model(self):
        if self.backend == SentimentBackend.FINBERT:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                "yiyanghkust/finbert-tone"
            )
            self.model = AutoModelForSequenceClassification.from_pretrained(
                "yiyanghkust/finbert-tone"
            )
        elif self.backend == SentimentBackend.SIMPLE:
            self._load_sentiment_dict()

    def analyze(self, text: str) -> SentimentResult:
        """分析单条文本"""
        if self.backend == SentimentBackend.FINBERT:
            return self._analyze_finbert(text)
        elif self.backend == SentimentBackend.DEEPSEEK:
            return self._analyze_deepseek(text)
        else:
            return self._analyze_simple(text)

    def analyze_batch(self, texts: list[str]) -> list[SentimentResult]:
        """批量分析"""
        return [self.analyze(t) for t in texts]

    def _analyze_finbert(self, text: str) -> SentimentResult:
        import torch

        inputs = self.tokenizer(
            text, return_tensors="pt",
            truncation=True, max_length=512
        )

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)

        # FinBERT: [negative, neutral, positive]
        scores = probs[0].tolist()
        label_idx = scores.index(max(scores))
        labels = ["negative", "neutral", "positive"]

        # 转换为 [-1, 1] 分数
        score = scores[2] - scores[0]  # positive - negative

        return SentimentResult(
            score=score,
            label=labels[label_idx],
            confidence=max(scores),
        )

    def _analyze_simple(self, text: str) -> SentimentResult:
        """基于词典的简单分析"""
        pos_count = sum(1 for w in self.pos_words if w in text)
        neg_count = sum(1 for w in self.neg_words if w in text)

        total = pos_count + neg_count + 1
        score = (pos_count - neg_count) / total

        return SentimentResult(
            score=score,
            label="positive" if score > 0.1 else ("negative" if score < -0.1 else "neutral"),
            confidence=abs(score),
        )
```

### 3.3 情绪因子 (Task 3.3)

**文件**：`src/ashare_lab/features/sentiment.py`

```python
from .base import BaseFeature, FeatureMeta, NormalizationMethod

class SentimentFactor(BaseFeature):
    """
    新闻情绪因子

    聚合股票相关新闻的情绪分数
    """

    def __init__(
        self,
        lookback: int = 5,
        decay: float = 0.8,  # 时间衰减
    ):
        self.lookback = lookback
        self.decay = decay
        self.analyzer = SentimentAnalyzer()

    @property
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            name=f"sentiment_{self.lookback}d",
            normalization=NormalizationMethod.ZSCORE,
            fillna_value=0.0,  # 无新闻时用中性值
        )

    def compute_raw(self, data: dict[str, pd.DataFrame]) -> pd.Series:
        news_df = data.get("news")
        if news_df is None:
            # 无新闻数据，返回全零
            return pd.Series(0.0, index=data["ohlcv"].index)

        # 按股票+日期聚合情绪
        sentiment_scores = []

        for (symbol, date), group in news_df.groupby(["symbol", "date"]):
            # 分析当日新闻
            scores = [
                self.analyzer.analyze(text).score
                for text in group["content"]
            ]
            # 取平均
            avg_score = np.mean(scores) if scores else 0.0
            sentiment_scores.append({
                "symbol": symbol,
                "date": date,
                "sentiment": avg_score,
            })

        sentiment_df = pd.DataFrame(sentiment_scores)

        # 带衰减的滚动平均
        def weighted_mean(x):
            weights = [self.decay ** i for i in range(len(x))][::-1]
            return np.average(x, weights=weights[:len(x)])

        return sentiment_df.groupby("symbol")["sentiment"].rolling(
            self.lookback
        ).apply(weighted_mean)
```

### 3.4 时间对齐 (Task 3.4)

**文件**：`src/ashare_lab/fusion/temporal_aligner.py`

```python
class TemporalAligner:
    """
    时间对齐器

    确保不同频率/来源的数据正确对齐到日频
    关键：防止未来信息泄露
    """

    def align_news_to_daily(
        self,
        news_df: pd.DataFrame,  # 包含 publish_time
        trading_dates: pd.DatetimeIndex,
        cutoff_hour: int = 15,  # 15点后的新闻算次日
    ) -> pd.DataFrame:
        """
        将新闻对齐到交易日

        规则：
        - 收盘前(15:00)的新闻 → 当日
        - 收盘后的新闻 → 次日
        - 非交易日的新闻 → 下一交易日
        """
        aligned = []

        for _, row in news_df.iterrows():
            pub_time = row["publish_time"]

            # 判断归属日期
            if pub_time.hour < cutoff_hour:
                target_date = pub_time.date()
            else:
                target_date = pub_time.date() + timedelta(days=1)

            # 找到下一个交易日
            target_date = self._next_trading_day(target_date, trading_dates)

            row["aligned_date"] = target_date
            aligned.append(row)

        return pd.DataFrame(aligned)
```

---

## 4. 验收标准

### 4.1 功能验收

- [ ] 新闻数据正常获取和解析
- [ ] 情绪分析模型正确运行（FinBERT/简单规则）
- [ ] 时间对齐无未来信息泄露
- [ ] 情绪因子正确计算

### 4.2 性能验收

| 指标 | 目标 |
|------|------|
| 情绪因子 IC | > 0.02 |
| 新闻覆盖率 | > 50% 交易日有新闻 |
| 情绪分析延迟 | < 100ms/条 |

---

## 5. 依赖与风险

### 依赖

- FinBERT 模型（HuggingFace）
- AkShare 新闻接口

### 风险

| 风险 | 概率 | 缓解措施 |
|------|------|---------|
| 新闻数据获取受限 | 高 | 多源备份，本地存档 |
| FinBERT 模型较大 | 中 | 可选简单规则模式 |
| 时间戳不准确 | 中 | 保守对齐策略 |

---

## 6. 后续步骤

完成 Phase 3 后：
1. 情绪因子集成到特征矩阵
2. 评估情绪因子对模型的边际贡献
3. 进入 Phase 4（LLM 增强）
