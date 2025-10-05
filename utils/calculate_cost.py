# Helper function for cost calculation
def calculate_openai_cost(token_usage: dict, model: str) -> float:

    # Current pricing (as of August 2024)
    pricing = {
        "gpt-4o-2024-08-06": {"input": 5.00, "output": 15.00},  # per 1M tokens
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-5": {"input": 1.25 , "output":10},
        "gpt-5-nano": {"input": 0.05 , "output":0.40}
    }

    if model not in pricing:
        return 0.0

    input_tokens = token_usage.get('input_tokens', 0)
    output_tokens = token_usage.get('output_tokens', 0)

    input_cost = (input_tokens / 1_000_000) * pricing[model]["input"]
    output_cost = (output_tokens / 1_000_000) * pricing[model]["output"]

    return input_cost + output_cost