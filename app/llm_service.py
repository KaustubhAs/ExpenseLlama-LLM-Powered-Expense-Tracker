from langchain_community.llms import Ollama
#from collections import defaultdict

class CategoryPredictor:
    def __init__(self):
        self.llm = Ollama(model="llama3.2")
        self.categories = [
            "Housing", "Transportation", "Food", 
            "Shopping", "Entertainment", "Services", 
            "Income", "Other"
        ]
        #self.misclassifications = defaultdict(int)
    # Updated predict_category method in llm_service.py
    def predict_category(self, description: str) -> str:
        prompt = f"""
        STRICTLY classify this transaction into ONE category from this exact list:
        {", ".join(self.categories)}

        RULES:
        1. Income = salary, freelance payments, investments
        2. Housing = rent, mortgage, utilities
        3. Transportation = fuel, public transit, vehicle maintenance
        4. Food = groceries, restaurants, delivery
        5. Shopping = retail purchases, online orders
        6. Services = subscriptions, repairs, professional services

        EXAMPLES:
        - "netflix subscription" → Services
        - "amazon purchase" → Shopping 
        - "salary deposit" → Income
        - "shell gas station" → Transportation
        - "Burger King" → Food

        Return ONLY the category name in Title Case. No explanations.
        Description: {description}
        """

        
        try:
            response = self.llm.invoke(prompt).strip()
            return self._validate_category(response)
        except Exception as e:
            print(f"LLM Error: {e}")
            return "Other"

        # Update _validate_category in llm_service.py
    def _validate_category(self, response: str) -> str:
        response_cleaned = response.strip().lower()
        for category in self.categories:
            if response_cleaned == category.lower():
                return category
        # Add fallback pattern matching
        if any(kw in response_cleaned for kw in ["housing", "rent"]):
            return "Housing"
        if "transport" in response_cleaned:
            return "Transportation"
        return "Other"

