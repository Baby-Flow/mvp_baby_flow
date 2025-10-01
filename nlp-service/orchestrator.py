"""
Orchestrator с динамическим reasoning для мультиагентной системы
"""
import os
from typing import Dict, Any
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from datetime import datetime
import pytz

from tools import (
    database_reader_tool,
    database_writer_tool,
    end_sleep_tool,
    time_calculator_tool,
    activity_validator_tool
)

class BabyFlowOrchestrator:
    def __init__(self):
        self.llm = ChatAnthropic(
            model="claude-3-haiku-20240307",  # Быстрая и экономичная модель
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0.3
        )

        self.tools = [
            database_reader_tool,
            database_writer_tool,
            end_sleep_tool,
            time_calculator_tool,
            activity_validator_tool
        ]

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)

        self.executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,
            max_iterations=5,
            handle_parsing_errors=True
        )

    def _get_system_prompt(self) -> str:
        return """Ты - умный ассистент для ведения дневника ребенка. 
        Твоя задача - понимать сообщения от мамы и записывать активности ребенка.
        
        ВАЖНО: Используй reasoning процесс для принятия решений:
        1. Анализируй сообщение
        2. Решай какие инструменты использовать
        3. Вызывай необходимые инструменты
        4. Формируй краткий ответ для мамы
        
        Текущее время: {current_time}
        Часовой пояс: Москва (UTC+3)
        
        ТИПЫ СОБЫТИЙ и КАК ИХ ЗАПИСЫВАТЬ:
        - "спит", "уснул", "заснул" → database_writer_tool с activity_type="sleep"
        - "проснулся", "встал" → сначала database_reader_tool найти открытый сон, потом end_sleep_tool БЕЗ указания времени
        - "покушал", "поел", "покормила" → database_writer_tool с activity_type="feeding"
        - "гуляем", "на прогулке" → database_writer_tool с activity_type="walk"
        - "покакал", "какал" → database_writer_tool с activity_type="diaper", type="poop"
        - "пописал", "писал" → database_writer_tool с activity_type="diaper", type="pee"
        - "памперс", "подгузник" → database_writer_tool с activity_type="diaper"
        - "температура 37.5", "36.6" → database_writer_tool с activity_type="temperature", temperature=число
        - "дали нурофен", "выпил лекарство" → database_writer_tool с activity_type="medication", medication_name и dosage
        
        ПРАВИЛА ИСПОЛЬЗОВАНИЯ ИНСТРУМЕНТОВ:
        1. database_writer_tool принимает параметры: activity_type ("sleep"/"feeding"/"walk"), child_id, и время
        2. Для записи начала сна используй: activity_type="sleep" и data с child_id и start_time
        3. Для завершения сна: сначала database_reader_tool найти открытый сон, потом end_sleep_tool
        4. Если время не указано - используй текущее время
        5. child_id всегда передавай из контекста сообщения
        
        ВАЖНО: 
        - Отвечай кратко и по-русски
        - Подтверди что записал БЕЗ технических деталей
        - НЕ показывай ID, OBSERVE, reasoning процесс
        - НЕ пиши "Анализ:", "Действия:", "Результат:"
        - Отвечай как заботливая помощница женского пола
        
        ПРИМЕРЫ ОТВЕТОВ:
        - "✅ Записала: малыш уснул в 14:30"
        - "✅ Малыш проснулся! Спал 2 часа 15 минут"
        - "📝 Записала кормление"
        - "🚶 Начали прогулку"
        - "💩 Отметила смену подгузника"
        - "💧 Записала, что малыш пописал"
        - "🌡️ Записала температуру 37.2°C"
        - "💊 Записала лекарство: Нурофен 5мл"
        """.format(current_time=datetime.now(pytz.timezone('Europe/Moscow')).strftime("%Y-%m-%d %H:%M"))

    def process_message(self, message: str, child_id: int = 1) -> Dict[str, Any]:
        """
        Обрабатывает сообщение от пользователя
        """
        enriched_input = f"""
        Сообщение от мамы: "{message}"
        ID ребенка для записи: {child_id}
        
        Используй reasoning:
        1. Определи тип события
        2. Реши какие tools нужны
        3. Выполни необходимые действия (используй child_id={child_id})
        4. Верни результат
        """

        try:
            result = self.executor.invoke({"input": enriched_input})
            return {
                "success": True,
                "response": result.get("output", "Записано"),
                "reasoning": self._extract_reasoning(result)
            }
        except Exception as e:
            return {
                "success": False,
                "response": f"Ошибка обработки: {str(e)}",
                "error": str(e)
            }

    def _extract_reasoning(self, result: Dict) -> str:
        """Извлекает reasoning из результата для отладки"""
        if "intermediate_steps" in result:
            steps = []
            for action, observation in result["intermediate_steps"]:
                if hasattr(action, 'tool'):
                    steps.append(f"Tool: {action.tool}, Input: {action.tool_input}")
            return " → ".join(steps)
        return "No reasoning available"