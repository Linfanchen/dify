# Dify 源码解析

## 架构


## 租户设计


## RAG部分
代码：`api/core/rag`

## Agent
代码：`api/core/agent`

## Workflow
`api/core/workflow`

## 优雅设计 

### 配置类

```python

class SentryConfig(BaseSettings):
    """
        1. 继承自 pydantic_settings 的 BaseSettings
        2. Field 都设置 默认值和描述
    """

    SENTRY_DSN: Optional[str] = Field(
        description="Sentry Data Source Name (DSN)."
        " This is the unique identifier of your Sentry project, used to send events to the correct project.",
        default=None,
    )

```

