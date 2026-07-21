from agent import run_agent

if __name__ == "__main__":
    while True:
        user_text = input("you> ").strip()
        if user_text in ("q", "quit", "exit"):
            break
        if not user_text:
            continue
        if user_text in ("new", "newsession"):
            print("新对话已开启，请输入内容")
            session_id = None
            continue
        else:
            session_id = "last"
        run_agent(user_text, session_id=session_id)