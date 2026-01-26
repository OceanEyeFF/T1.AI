# Phase 4: LLM 增强层

**状态**：🔲 待开始
**预计周期**：1-2 周
**优先级**：P1

---

## 1. 目标

引入 LLM 进行量化信号的逻辑验证，过滤虚假信号，提升推荐质量。

---

## 2. 任务清单

| ID | 任务 | 优先级 | 状态 | 产出 |
|----|------|--------|------|------|
| 4.1 | LLM API 抽象层 | P0 | 🔲 | `llm/client.py` |
| 4.2 | 信号验证 Agent | P0 | 🔲 | `llm/signal_validator.py` |
| 4.3 | 提示词模板库 | P1 | 🔲 | `llm/prompts/` |
| 4.4 | 批量调用与缓存 | P1 | 🔲 | `llm/batch_processor.py` |
| 4.5 | 成本监控 | P2 | 🔲 | `llm/cost_tracker.py` |
| 4.6 | 单元测试 | P1 | 🔲 | `tests/test_llm.py` |

---

## 3. 详细设计

### 3.1 LLM API 抽象层 (Task 4.1)

**文件**：`src/ashare_lab/llm/client.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

class LLMProvider(Enum):
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    LOCAL = "local"  # 本地模型

@dataclass
class LLMConfig:
    provider: LLMProvider
    model: str
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.3
    max_tokens: int = 1024

class LLMClient:
    """
    统一 LLM 调用接口

    支持多种后端，自动重试和错误处理
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._init_client()

    def _init_client(self):
        if self.config.provider == LLMProvider.DEEPSEEK:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.config.api_key,
                base_url="https://api.deepseek.com/v1",
            )
        elif self.config.provider == LLMProvider.OPENAI:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.config.api_key)

    def chat(
        self,
        messages: list[dict],
        **kwargs
    ) -> str:
        """
        发送聊天请求

        Args:
            messages: [{"role": "system/user/assistant", "content": "..."}]

        Returns:
            助手回复内容
        """
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.config.temperature),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
        )
        return response.choices[0].message.content

    async def chat_async(self, messages: list[dict], **kwargs) -> str:
        """异步版本"""
        # 使用 asyncio 包装
        import asyncio
        return await asyncio.to_thread(self.chat, messages, **kwargs)
```

### 3.2 信号验证 Agent (Task 4.2)

**文件**：`src/ashare_lab/llm/signal_validator.py`

```python
from dataclasses import dataclass
from enum import Enum
import json

class LLMVerdict(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ADJUST_UP = "adjust_up"
    ADJUST_DOWN = "adjust_down"

@dataclass
class ValidationResult:
    verdict: LLMVerdict
    adjustment: float       # 置信度调整因子 0.5~1.5
    reasoning: str          # 分析理由
    risk_flags: list[str]   # 风险标记

class SignalValidator:
    """
    信号验证 Agent

    使用 LLM 验证量化信号的逻辑合理性
    """

    SYSTEM_PROMPT = """你是一位资深的量化投资分析师。
你的任务是验证量化模型的预测信号是否合理。

判断标准：
1. 预测是否与当前市场环境一致
2. 是否存在模型可能忽略的风险
3. 近期新闻/政策是否支持或反对该预测

输出格式（JSON）：
{
    "verdict": "approve/reject/adjust_up/adjust_down",
    "adjustment": 0.5-1.5,
    "reasoning": "简要分析（50字内）",
    "risk_flags": ["风险1", "风险2"]
}
"""

    USER_TEMPLATE = """
## 量化信号

股票: {symbol} ({name})
预测周期: {horizon}
预测收益: {pred_return:.2%}
模型置信度: {confidence:.1%}
当前排名: {rank}

## 市场环境

- 大盘趋势: {market_trend}
- 北向资金: {northbound_flow}
- 行业表现: {sector_performance}

## 近期新闻

{recent_news}

## 请分析

该预测信号是否合理？给出你的判断。
"""

    def __init__(self, llm_client: LLMClient):
        self.client = llm_client

    async def validate(
        self,
        signal: dict,
        context: dict,
    ) -> ValidationResult:
        """
        验证单个信号
        """
        # 构建用户消息
        user_msg = self.USER_TEMPLATE.format(
            symbol=signal["symbol"],
            name=signal.get("name", ""),
            horizon=signal["horizon"],
            pred_return=signal["pred_return"],
            confidence=signal["confidence"],
            rank=signal["rank"],
            market_trend=context.get("market_trend", "未知"),
            northbound_flow=context.get("northbound_flow", "未知"),
            sector_performance=context.get("sector_performance", "未知"),
            recent_news=context.get("recent_news", "无"),
        )

        # 调用 LLM
        response = await self.client.chat_async([
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ])

        # 解析结果
        return self._parse_response(response)

    def _parse_response(self, response: str) -> ValidationResult:
        """解析 LLM 响应"""
        try:
            # 提取 JSON
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            data = json.loads(json_str)

            return ValidationResult(
                verdict=LLMVerdict(data["verdict"]),
                adjustment=float(data.get("adjustment", 1.0)),
                reasoning=data.get("reasoning", ""),
                risk_flags=data.get("risk_flags", []),
            )
        except Exception as e:
            # 解析失败，默认通过
            return ValidationResult(
                verdict=LLMVerdict.APPROVE,
                adjustment=1.0,
                reasoning=f"解析失败: {e}",
                risk_flags=["llm_parse_error"],
            )
```

### 3.3 批量处理与缓存 (Task 4.4)

**文件**：`src/ashare_lab/llm/batch_processor.py`

```python
import hashlib
import json
from pathlib import Path
import asyncio

class BatchProcessor:
    """
    批量处理 LLM 请求

    功能：
    - 并发控制
    - 结果缓存
    - 失败重试
    """

    def __init__(
        self,
        validator: SignalValidator,
        cache_dir: Path = Path("data/llm_cache"),
        max_concurrent: int = 5,
        cache_ttl_days: int = 7,
    ):
        self.validator = validator
        self.cache_dir = cache_dir
        self.max_concurrent = max_concurrent
        self.cache_ttl_days = cache_ttl_days

        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def validate_batch(
        self,
        signals: list[dict],
        context: dict,
    ) -> list[ValidationResult]:
        """
        批量验证信号
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def validate_with_cache(signal):
            # 检查缓存
            cache_key = self._cache_key(signal, context)
            cached = self._load_cache(cache_key)
            if cached:
                return cached

            # 调用 LLM
            async with semaphore:
                result = await self.validator.validate(signal, context)

            # 保存缓存
            self._save_cache(cache_key, result)
            return result

        tasks = [validate_with_cache(s) for s in signals]
        return await asyncio.gather(*tasks)

    def _cache_key(self, signal: dict, context: dict) -> str:
        """生成缓存键"""
        key_data = {
            "symbol": signal["symbol"],
            "horizon": signal["horizon"],
            "pred_return": round(signal["pred_return"], 4),
            "market_trend": context.get("market_trend"),
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _load_cache(self, key: str) -> ValidationResult | None:
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None

        # 检查 TTL
        import time
        age_days = (time.time() - cache_file.stat().st_mtime) / 86400
        if age_days > self.cache_ttl_days:
            return None

        with open(cache_file) as f:
            data = json.load(f)

        return ValidationResult(
            verdict=LLMVerdict(data["verdict"]),
            adjustment=data["adjustment"],
            reasoning=data["reasoning"],
            risk_flags=data["risk_flags"],
        )

    def _save_cache(self, key: str, result: ValidationResult):
        cache_file = self.cache_dir / f"{key}.json"
        with open(cache_file, "w") as f:
            json.dump({
                "verdict": result.verdict.value,
                "adjustment": result.adjustment,
                "reasoning": result.reasoning,
                "risk_flags": result.risk_flags,
            }, f)
```

### 3.4 成本监控 (Task 4.5)

**文件**：`src/ashare_lab/llm/cost_tracker.py`

```python
@dataclass
class CostRecord:
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float

class CostTracker:
    """
    LLM 调用成本追踪
    """

    # 价格表 (USD per 1K tokens)
    PRICES = {
        "deepseek-chat": {"input": 0.0001, "output": 0.0002},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }

    def __init__(self, budget_daily_usd: float = 1.0):
        self.budget = budget_daily_usd
        self.records: list[CostRecord] = []

    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ):
        prices = self.PRICES.get(model, {"input": 0.001, "output": 0.002})
        cost = (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1000

        self.records.append(CostRecord(
            timestamp=datetime.now(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        ))

    def daily_cost(self) -> float:
        today = datetime.now().date()
        return sum(
            r.cost_usd for r in self.records
            if r.timestamp.date() == today
        )

    def is_over_budget(self) -> bool:
        return self.daily_cost() >= self.budget
```

---

## 4. 验收标准

### 4.1 功能验收

- [ ] LLM 客户端正常连接 DeepSeek/OpenAI
- [ ] 信号验证 Agent 输出格式正确
- [ ] 缓存机制正常工作
- [ ] 成本追踪准确

### 4.2 性能验收

| 指标 | 目标 |
|------|------|
| 调用成功率 | > 95% |
| 单次响应时间 | < 5s |
| 单日成本 | < $1 |
| 缓存命中率 | > 30% |

---

## 5. 配置示例

**文件**：`configs/llm.yaml`

```yaml
llm:
  provider: "deepseek"
  model: "deepseek-chat"
  temperature: 0.3
  max_tokens: 512

validation:
  llm_weight: 0.3       # LLM 调整权重
  enable_veto: true     # 是否允许否决
  min_confidence: 0.3   # 最低置信度阈值

cost_control:
  daily_budget_usd: 1.0
  max_concurrent: 5
  cache_ttl_days: 7
```

---

## 6. 依赖与风险

### 依赖

- DeepSeek API 或 OpenAI API
- 网络稳定性

### 风险

| 风险 | 概率 | 缓解措施 |
|------|------|---------|
| API 调用失败 | 中 | 重试机制，降级到无验证 |
| 成本超支 | 低 | 预算控制，缓存复用 |
| 响应格式不稳定 | 中 | 容错解析，默认通过 |

---

## 7. 后续步骤

完成 Phase 4 后：
1. LLM 验证集成到推荐流程
2. 评估 LLM 过滤效果（命中率变化）
3. 进入 Phase 5（模型融合）
