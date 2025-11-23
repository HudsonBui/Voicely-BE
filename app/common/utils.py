from app.common.constants import AIPrompts


def build_summary_system_prompt(language="Tiếng Việt") -> str:
    return AIPrompts.SUMMARY_SYSTEM_PROMPT.format(language=language)

def build_summary_user_prompt(content: str) -> str:
    return AIPrompts.SUMMARY_USER_PROMPT.format(content=content)