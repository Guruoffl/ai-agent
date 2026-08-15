import os
import json

from dotenv import load_dotenv
from openai import OpenAI
from json_repair import repair_json

from tool_registry import (
    tool_registry,
    tools
)


load_dotenv()


client = OpenAI(

    base_url=
        "https://openrouter.ai/api/v1",

    api_key=
        os.getenv(
            "OPENROUTER_API_KEY"
        )

)


MAX_USER_TURNS = 10


SYSTEM_MESSAGE = {

    "role":
        "system",

    "content":
        """
You are a helpful AI agent.

You have access to several tools.

Use calculator for arithmetic.

Use get_time for the current time.

Use web_search when the user needs
current or web-based information.

Use read_webpage when you need to inspect
the actual contents of a webpage.

Use search_memory when previous long-term
information may be relevant.

Use save_memory when the user tells you
something durable that will be useful later.

Good things to remember include:

- preferences
- learning goals
- projects
- skills
- long-term plans

Do not save:

- passwords
- API keys
- secrets
- sensitive personal information
- temporary conversation details

When researching something, use web_search
first and then read_webpage when needed.

Always use tool results to construct
your answer.

Do not claim that you lack real-time
information when an appropriate tool
can provide it.

When calling a tool, provide valid JSON
arguments that exactly match the tool schema.
"""
}


messages = [
    SYSTEM_MESSAGE
]


def get_role(message):

    if isinstance(message, dict):

        return message.get("role")

    return message.role


def trim_memory():

    global messages

    user_positions = []

    for index, message in enumerate(
        messages
    ):

        if get_role(message) == "user":

            user_positions.append(index)


    if len(user_positions) <= MAX_USER_TURNS:

        return


    first_kept_position = (
        user_positions[-MAX_USER_TURNS]
    )


    messages = [

        SYSTEM_MESSAGE

    ] + messages[first_kept_position:]


def parse_arguments(arguments):

    try:

        return json.loads(
            arguments
        )

    except json.JSONDecodeError:

        print(
            "[Warning: repairing malformed JSON...]"
        )

        repaired = repair_json(
            arguments
        )

        return json.loads(
            repaired
        )


def execute_tool(tool_call):

    tool_name = (
        tool_call.function.name
    )

    raw_arguments = (
        tool_call.function.arguments
    )


    print(
        f"\n[Using tool: {tool_name}]"
    )


    try:

        arguments = parse_arguments(
            raw_arguments
        )

    except Exception as e:

        return (
            "Could not parse tool arguments: "
            f"{str(e)}"
        )


    tool = tool_registry.get(
        tool_name
    )


    if tool is None:

        return (
            f"Tool '{tool_name}' "
            f"does not exist."
        )


    try:

        return tool(
            **arguments
        )

    except Exception as e:

        return (
            "Tool execution error: "
            f"{str(e)}"
        )


while True:

    user_input = input(
        "\nYou: "
    )


    if user_input.lower() == "exit":

        print(
            "Agent stopped."
        )

        break


    messages.append({

        "role":
            "user",

        "content":
            user_input

    })


    while True:

        response = client.chat.completions.create(

            model=
                "openrouter/free",

            messages=
                messages,

            tools=
                tools

        )


        message = (
            response.choices[0].message
        )


        if not message.tool_calls:

            messages.append(
                message
            )

            print(
                "\nAgent:",
                message.content
            )

            break


        messages.append(
            message
        )


        for tool_call in (
            message.tool_calls
        ):

            result = execute_tool(
                tool_call
            )


            messages.append({

                "role":
                    "tool",

                "tool_call_id":
                    tool_call.id,

                "content":
                    json.dumps(
                        result
                    )

            })


    trim_memory()