from agent import Agent

agent = Agent()

while True:
    prompt = input('You: ')
    response, token = agent.ask(prompt)
    print(response)
    print("Total token usage: ", token)