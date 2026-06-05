import anthropic

def main():
    print("Hello from ant!\n")
    client = anthropic.Anthropic()
    history = []

    while True:
        usermsg = input("You: ").strip()
        if usermsg.lower() in ("exit", "quit"):
            break
        usermsg = usermsg if usermsg else "Hello, Claude"

        history.append({"role": "user", "content": usermsg})

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=history
        )

        reply = message.content[0].text
        print(f"\nClaude: {reply}\n")

        history.append({"role": "assistant", "content": reply})

if __name__ == "__main__":
    main()
