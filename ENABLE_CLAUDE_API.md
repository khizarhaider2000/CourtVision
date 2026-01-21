# Enabling Claude API for Natural Language Queries

The AI query parser currently uses a rule-based fallback with OUT_OF_SCOPE validation. To enable the full Claude API integration for more robust natural language understanding:

## Setup Instructions

### 1. Install the Anthropic SDK

```bash
pip install anthropic
```

### 2. Get Your API Key

1. Sign up at https://console.anthropic.com/
2. Navigate to API Keys section
3. Create a new API key
4. Copy the key (starts with `sk-ant-`)

### 3. Set Environment Variable

Add your API key to your environment:

**macOS/Linux:**
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

**Or add to your `.env` file:**
```
ANTHROPIC_API_KEY=your-api-key-here
```

**Then load it in your Python code:**
```python
from dotenv import load_dotenv
load_dotenv()
```

### 4. Enable the API Code

In `ai_query_parser.py`, locate the `parse_natural_language_query` function (around line 130) and:

1. **Uncomment** the Claude API integration code block
2. **Comment out** or **remove** the fallback line:
   ```python
   # return _rule_based_parser_with_validation(user_query)
   ```

The code will automatically:
- Call Claude API with the comprehensive system prompt
- Handle CLARIFY responses (when user intent is ambiguous)
- Handle OUT_OF_SCOPE responses (when query is not supported)
- Parse valid JSON query objects

### 5. Test It

Run the Streamlit app:
```bash
streamlit run streamlit_ai.py
```

Try complex queries like:
- "Which teams have the best net rating in clutch situations?" → Should get OUT_OF_SCOPE
- "Show me offensive efficiency" → Should clarify if you want a scatter plot or leaderboard
- "Top 10 teams by net rating last 10 games" → Should work perfectly

## Benefits of Claude API vs Rule-Based

| Feature | Rule-Based | Claude API |
|---------|-----------|------------|
| Simple queries | ✅ Works | ✅ Works better |
| Complex phrasing | ❌ Limited | ✅ Robust |
| Typo tolerance | ❌ No | ✅ Yes |
| Intent understanding | ❌ Pattern matching | ✅ Semantic |
| Clarification questions | ❌ No | ✅ Yes |
| OUT_OF_SCOPE detection | ✅ Basic | ✅ Comprehensive |
| Team name variations | ✅ Limited | ✅ Extensive |

## Current Status

- ✅ Rule-based parser with OUT_OF_SCOPE validation (active)
- ✅ Comprehensive system prompt ready
- ⏸️ Claude API integration (commented out, ready to enable)

## Cost Considerations

Claude API pricing (as of 2025):
- Claude 3.5 Sonnet: ~$3 per million input tokens, ~$15 per million output tokens
- Average query cost: < $0.01 per query
- For personal/demo use: Very affordable (a few dollars per month)

For production with many users, consider:
- Caching frequently asked queries
- Using Claude 3.5 Haiku for cheaper option
- Rate limiting per user
