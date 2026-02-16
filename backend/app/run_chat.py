from pharmacy_agent import pharmacy_chatbot

print("🤖 Pharmacy Bot Started! Type 'exit' to quit.\n")

while True:
    user_message = input("You: ")

    if user_message.lower() == "exit":
        print("Bot: Bye 👋")
        break

    reply = pharmacy_chatbot(user_message)
    print("Bot:", reply)
    print()
