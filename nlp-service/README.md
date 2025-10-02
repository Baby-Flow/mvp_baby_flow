# NLP Service Configuration

## LLM Provider Support

The NLP service now supports multiple LLM providers:

### 1. Anthropic Claude (Default)
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_api_key
ANTHROPIC_MODEL=claude-3-haiku-20240307  # Fast and economical
```

Available Claude models:
- `claude-3-haiku-20240307` - Fastest, most economical
- `claude-3-sonnet-20240229` - Balanced performance
- `claude-3-opus-20240229` - Most capable

### 2. Mistral AI
```env
LLM_PROVIDER=mistral
MISTRAL_API_KEY=your_api_key
MISTRAL_MODEL=mistral-large-latest  # Best available model
```

Available Mistral models:
- `mistral-large-latest` - Most capable (recommended)
- `mistral-medium-latest` - Balanced performance
- `mistral-small-latest` - Fast and economical
- `open-mistral-7b` - Open source model

## Switching Providers

1. Update your `.env` file with the desired provider:
```env
# For Mistral
LLM_PROVIDER=mistral
MISTRAL_API_KEY=your_mistral_api_key
MISTRAL_MODEL=mistral-large-latest

# For Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-haiku-20240307
```

2. Restart the service:
```bash
docker-compose restart nlp-service
```

## Performance Comparison

| Provider | Model | Speed | Cost | Quality |
|----------|-------|-------|------|---------|
| Anthropic | claude-3-haiku | ⚡⚡⚡ | 💰 | ⭐⭐⭐ |
| Anthropic | claude-3-sonnet | ⚡⚡ | 💰💰 | ⭐⭐⭐⭐ |
| Mistral | mistral-small | ⚡⚡⚡ | 💰 | ⭐⭐⭐ |
| Mistral | mistral-large | ⚡⚡ | 💰💰 | ⭐⭐⭐⭐⭐ |

## Getting API Keys

- **Anthropic**: https://console.anthropic.com/
- **Mistral**: https://console.mistral.ai/