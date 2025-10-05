from langchain_openai import ChatOpenAI
from data_moduels.validation_mode import ValidationMode


class LLMManager:
    def __init__(self):
        self.auto_transform_llm = None
        self.auto_validation_llm = None
        self.human_transform_llm = None

    def get_transform_llm(self, validation_mode: ValidationMode):
        if validation_mode == ValidationMode.AUTOMATIC:
            if not self.auto_transform_llm:
                self.auto_transform_llm = ChatOpenAI(
                    model="gpt-5",
                    #temperature=0.0,
                    api_key="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"
                )
            return self.auto_transform_llm
        else:  # HUMAN
            if not self.human_transform_llm:
                self.human_transform_llm = ChatOpenAI(
                    model="gpt-5-nano",
                    temperature=0.0,
                    api_key="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"
                )
            return self.human_transform_llm

    def get_validation_llm(self):
        """Gibt Validation LLM zurück (nur für AUTO Mode)"""
        if not self.auto_validation_llm:
            self.auto_validation_llm = ChatOpenAI(
                model="gpt-5-nano",
                temperature=0.0,
                api_key="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"
            )
        return self.auto_validation_llm


# Global instance
llm_manager = LLMManager()