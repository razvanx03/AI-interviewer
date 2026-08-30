# ==============================================================================
# Model Sampling & Inference Parameters
# ==============================================================================

# Temperature: Controls randomness / creativity of token generation (0.0 to 2.0).
# - Higher values (e.g. 0.7 - 1.0): More creative, varied, and conversational phrasing.
# - Lower values (e.g. 0.0 - 0.2): More deterministic, precise, and analytical.
DEFAULT_CHAT_TEMPERATURE: float = 0.7
DEFAULT_EVALUATION_TEMPERATURE: float = 0.2

# Repeat Penalty (llama.cpp / Ollama native parameter, default 1.1 - 1.2):
# - Mathematically penalizes logits of tokens that have already been generated recently.
# - Values > 1.0 (e.g. 1.18) prevent the model from getting stuck in loops or repeating
#   the exact same questions / phrases word-for-word across conversational turns.
DEFAULT_REPEAT_PENALTY: float = 1.18

# Presence Penalty (OpenAI / llama.cpp standard, -2.0 to 2.0):
# - One-off flat penalty applied if a token appears AT LEAST ONCE in the text.
# - Values > 0.0 (e.g. 0.6) encourage the model to introduce completely new topics
#   and competencies rather than lingering on the same subject.
DEFAULT_PRESENCE_PENALTY: float = 0.6

# Frequency Penalty (OpenAI / llama.cpp standard, -2.0 to 2.0):
# - Proportional penalty based on HOW OFTEN a token has appeared in the text.
# - Values > 0.0 (e.g. 0.5) discourage verbatim word re-use and cliché phrases.
DEFAULT_FREQUENCY_PENALTY: float = 0.5

# Top-P (Nucleus Sampling, 0.0 to 1.0):
# - Cuts off the long tail of low-probability tokens, considering only the cumulative
#   top 90% (0.9) probability mass. Ensures high coherence while allowing natural variety.
DEFAULT_TOP_P: float = 0.9

# ==============================================================================
# HTTP Client Timeouts (seconds)
# ==============================================================================
HTTP_CONNECT_TIMEOUT_SECONDS: float = 10.0
HTTP_READ_TIMEOUT_SECONDS: float = 180.0
HTTP_WRITE_TIMEOUT_SECONDS: float = 30.0
HTTP_POOL_TIMEOUT_SECONDS: float = 30.0

# ==============================================================================
# Context Window Management & Progressive Summarization Constants
# ==============================================================================
DEFAULT_NUM_CTX: int = 8192
CONTEXT_TOKEN_THRESHOLD_RATIO: float = 0.60
RECENT_MESSAGES_WINDOW_COUNT: int = 6
EVALUATION_CHUNK_SIZE_ROUNDS: int = 4
EVALUATION_CHUNK_TRIGGER_ROUNDS: int = 5

