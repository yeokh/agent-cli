import anthropic

def main():
    print("Hello from ant!\n")

    usermsg = input("You: ").strip()
    usermsg = usermsg if usermsg else "Hello, Claude"
    
    message = anthropic.Anthropic().messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": usermsg}],
    )
    print(message)
    print("\n")
    print(message.content[0].text + "\n")


if __name__ == "__main__":
    main()
