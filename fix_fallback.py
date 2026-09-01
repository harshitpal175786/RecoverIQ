import re

with open("agent/fallback_rules.py", "r") as f:
    content = f.read()

content = content.replace("amount = transaction.amount", "amount = transaction.amount_inr")
content = content.replace("customer_name = getattr(transaction, 'customer_id', 'Customer') # fallback", "customer_name = getattr(transaction, 'customer_name', 'Customer')")

# Add transaction_id=transaction.transaction_id, is_fallback=True to AgentDecision calls
content = re.sub(r'AgentDecision\(', 'AgentDecision(\n            transaction_id=transaction.transaction_id,\n            is_fallback=True,', content)

with open("agent/fallback_rules.py", "w") as f:
    f.write(content)

