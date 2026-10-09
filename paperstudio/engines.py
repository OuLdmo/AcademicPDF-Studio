"""Unified, user-visible engine defaults. No credentials are stored here."""
ENGINES = {
    'none': {'name':'仅格式转换', 'model':'', 'url':'', 'env':''},
    'ollama': {'name':'Ollama（本地免费）', 'model':'qwen2.5:3b', 'url':'http://127.0.0.1:11434', 'env':''},
    'argos': {'name':'Argos Translate（离线免费）', 'model':'', 'url':'', 'env':''},
    'libretranslate': {'name':'LibreTranslate（自建免费）', 'model':'', 'url':'http://127.0.0.1:5000', 'env':'LIBRETRANSLATE_API_KEY'},
    'deepseek': {'name':'DeepSeek API（按量计费）', 'model':'deepseek-flash', 'url':'https://api.deepseek.com', 'env':'DEEPSEEK_API_KEY'},
    'openai': {'name':'OpenAI API（按量计费）', 'model':'gpt-4.1-mini', 'url':'https://api.openai.com/v1', 'env':'OPENAI_API_KEY'},
    'deepl': {'name':'DeepL API（有条件免费额度）', 'model':'', 'url':'', 'env':'DEEPL_AUTH_KEY'},
}

def defaults(engine):
    return ENGINES[engine]
