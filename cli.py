from agent import run_agent

if __name__ == "__main__":
    while True:
        user_text = input("you> ").strip()
        if user_text in ("q", "quit", "exit"):
            break
        if user_text:
            run_agent(user_text)