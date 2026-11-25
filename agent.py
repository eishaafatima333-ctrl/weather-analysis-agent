from dotenv import load_dotenv
from deepagents import create_deep_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from tools import get_weather, get_forecast, get_hourly_outlook, save_pdf_report

load_dotenv()

# The model retries automatically when Google's servers are busy
model = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    max_retries=6,
    timeout=60,
)

SYSTEM_PROMPT = """You are a Weather Analysis and Storm Prediction agent.

Rules:
- Always use your tools to get live data. Never guess the weather.
- For current conditions in a city, use get_weather.
- For multi-day outlooks, use get_forecast.
- For questions about rain or storms in the coming hours, use get_hourly_outlook,
  then explain which hours carry risk and what to expect.
- Always say clearly whether a storm or rain is likely, and give the time window.
- After your analysis, ALWAYS call save_pdf_report with the city and your full
  analysis written as plain text (no markdown symbols like ** or #).
- In your final answer, give the analysis and mention the PDF path.
"""

agent = create_deep_agent(
    model=model,
    tools=[get_weather, get_forecast, get_hourly_outlook, save_pdf_report],
    system_prompt=SYSTEM_PROMPT,
)


def ask(question: str) -> str:
    try:
        result = agent.invoke({"messages": [{"role": "user", "content": question}]})
        return result["messages"][-1].text
    except Exception as e:
        return f"The AI model is busy right now. Please try again in a minute. (Details: {e})"


if __name__ == "__main__":
    print(ask(input("Ask something: "))) 
    
